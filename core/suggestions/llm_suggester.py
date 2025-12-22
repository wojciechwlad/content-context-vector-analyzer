"""Generator sugestii naprawy Content Context Vector przez LLM."""

from pathlib import Path
from functools import lru_cache

from core.embeddings.ollama_client import OllamaClient
from core.models import ChecklistItem, CheckStatus, ExtractedContent


# Ścieżka do katalogu z promptami
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=10)
def load_prompt(name: str) -> str:
    """
    Ładuje prompt z pliku tekstowego.

    Args:
        name: Nazwa promptu (bez rozszerzenia .txt)

    Returns:
        Zawartość promptu
    """
    path = PROMPTS_DIR / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    # Fallback dla braku pliku
    return f"[Brak pliku promptu: {name}.txt]"


def get_system_prompt() -> str:
    """Zwraca system prompt z pliku."""
    return load_prompt("system_prompt")


def get_prompt_template(name: str) -> str:
    """Zwraca szablon promptu z pliku."""
    return load_prompt(name)


def load_prompt_for_code(code: str) -> str | None:
    """
    Szuka dedykowanego promptu dla kodu CV w katalogu /prompts.

    Szuka plików pasujących do wzorca: CV-XXX-*.txt
    np. CV-002-title-length.txt, CV-012-topic-drift.txt

    Args:
        code: Kod problemu (np. "CV-002", "CV-012")

    Returns:
        Zawartość promptu lub None jeśli nie znaleziono
    """
    import glob
    pattern = str(PROMPTS_DIR / f"{code}-*.txt")
    matches = glob.glob(pattern)

    if matches:
        # Użyj pierwszego pasującego pliku
        return Path(matches[0]).read_text(encoding="utf-8")
    return None


class LLMSuggester:
    """Generator sugestii naprawy przez LLM."""

    def __init__(self, ollama_client: OllamaClient | None = None):
        """
        Inicjalizuje generator sugestii.

        Args:
            ollama_client: Klient Ollama (opcjonalnie)
        """
        self.client = ollama_client or OllamaClient()

    def _parse_variants(self, response: str) -> list[str]:
        """Parsuje warianty z odpowiedzi LLM."""
        import re
        variants = []
        # Szukaj linii zaczynających się od numeru
        for line in response.split("\n"):
            # Usuń numerację i białe znaki
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line.strip())
            # Usuń cudzysłowy jeśli są
            cleaned = cleaned.strip('"\'')
            if cleaned and len(cleaned) > 10:  # Ignoruj za krótkie
                variants.append(cleaned)
        return variants[:5]  # Max 5 wariantów

    def _generate_length_suggestion_with_llm(
        self,
        text: str,
        current_len: int,
        target_min: int,
        target_max: int,
        element_name: str,
        max_iterations: int = 3,
    ) -> str:
        """
        Generuje przykłady z LLM i waliduje długość.

        Args:
            text: Aktualny tekst
            current_len: Aktualna długość
            target_min: Minimalna długość docelowa
            target_max: Maksymalna długość docelowa
            element_name: Nazwa elementu
            max_iterations: Maksymalna liczba prób

        Returns:
            Tekst z przykładami i walidacją
        """
        all_examples = []
        too_long = current_len > target_max

        for iteration in range(max_iterations):
            # Buduj prompt z feedbackiem
            if iteration == 0:
                direction = "skróć" if too_long else "wydłuż"
                hint = f"Wygeneruj 5 wariantów. Cel: {target_min}-{target_max} znaków. {direction.capitalize()} oryginalny tekst."
            else:
                # Analiza poprzednich prób
                valid = [e for e in all_examples if e["status"] == "✅"]
                invalid = [e for e in all_examples if "❌" in e["status"]]

                if invalid:
                    avg_len = sum(e["len"] for e in invalid) / len(invalid)
                    if avg_len > target_max:
                        hint = f"Poprzednie próby za DŁUGIE (śr. {avg_len:.0f} zn.). Cel: {target_min}-{target_max} zn. SKRÓĆ tekst bardziej."
                    else:
                        hint = f"Poprzednie próby za KRÓTKIE (śr. {avg_len:.0f} zn.). Cel: {target_min}-{target_max} zn. WYDŁUŻ tekst."
                else:
                    hint = f"Wygeneruj kolejne warianty. Cel: {target_min}-{target_max} znaków."

            prompt = f"""Oryginalny {element_name}: "{text}" ({current_len} zn.)

{hint}

Wymagania:
- Zachowaj główne słowa kluczowe
- Zachowaj sens i value proposition
- Każdy wariant w nowej linii

Format odpowiedzi (TYLKO warianty, bez komentarzy):
1. [wariant tekstu]
2. [wariant tekstu]
3. [wariant tekstu]
4. [wariant tekstu]
5. [wariant tekstu]"""

            try:
                response = self.client.generate(
                    prompt=prompt,
                    system=get_system_prompt(),
                    temperature=0.8,
                )
                variants = self._parse_variants(response)

                # Walidacja długości
                for variant in variants:
                    variant_len = len(variant)
                    if target_min <= variant_len <= target_max:
                        all_examples.append({
                            "text": variant,
                            "len": variant_len,
                            "status": "✅"
                        })
                    else:
                        diff = variant_len - target_max if variant_len > target_max else target_min - variant_len
                        all_examples.append({
                            "text": variant,
                            "len": variant_len,
                            "status": f"❌ ({diff:+d} zn.)"
                        })

                # Jeśli mamy >= 2 poprawne, zakończ
                valid_count = sum(1 for e in all_examples if e["status"] == "✅")
                if valid_count >= 2:
                    break

            except Exception as e:
                return f"Błąd generowania: {str(e)}"

        # Formatuj wynik
        return self._format_length_examples(all_examples, text, current_len, target_min, target_max, element_name)

    def _format_length_examples(
        self,
        examples: list[dict],
        original_text: str,
        current_len: int,
        target_min: int,
        target_max: int,
        element_name: str,
    ) -> str:
        """Formatuje przykłady z oznaczeniem poprawności."""
        valid = [e for e in examples if e["status"] == "✅"]
        invalid = [e for e in examples if "❌" in e["status"]]

        lines = [
            f"📏 **{element_name}** - analiza długości",
            "",
            f"**Oryginalny:** \"{original_text}\" ({current_len} zn.)",
            f"**Cel:** {target_min}-{target_max} znaków",
            "",
        ]

        if valid:
            lines.append(f"### ✅ Poprawne warianty ({len(valid)}):")
            for i, ex in enumerate(valid, 1):
                lines.append(f"{i}. \"{ex['text']}\" ({ex['len']} zn.)")
            lines.append("")

        if invalid:
            lines.append(f"### ❌ Niepoprawne warianty ({len(invalid)}):")
            for i, ex in enumerate(invalid, 1):
                lines.append(f"{i}. \"{ex['text']}\" ({ex['len']} zn.) {ex['status']}")
            lines.append("")

        if not valid:
            lines.append("⚠️ Nie udało się wygenerować wariantów o poprawnej długości.")
            lines.append("Spróbuj ręcznie dostosować tekst.")

        return "\n".join(lines)

    def generate_suggestion(
        self,
        checklist_item: ChecklistItem,
        content: ExtractedContent,
        similarity_score: float | None = None,
    ) -> str:
        """
        Generuje sugestię naprawy dla problemu.

        Args:
            checklist_item: Element checklisty z problemem
            content: Zawartość dokumentu
            similarity_score: Opcjonalny score similarity

        Returns:
            Tekst z sugestiami
        """
        code = checklist_item.code

        # Dla problemów z długością - użyj LLM z pętlą walidacji
        if code == "CV-002":  # Title length
            title = content.title or ""
            return self._generate_length_suggestion_with_llm(
                text=title,
                current_len=len(title),
                target_min=50,
                target_max=60,
                element_name="Title Tag",
            )

        if code == "CV-006":  # Meta description length
            meta = content.meta_description or ""
            return self._generate_length_suggestion_with_llm(
                text=meta,
                current_len=len(meta),
                target_min=150,
                target_max=160,
                element_name="Meta Description",
            )

        # Dla innych problemów - użyj LLM
        prompt = self._build_prompt(checklist_item, content, similarity_score)

        try:
            response = self.client.generate(
                prompt=prompt,
                system=get_system_prompt(),
                temperature=0.7,
            )
            return response.strip()
        except Exception as e:
            return f"Błąd generowania sugestii: {str(e)}"

    def generate_suggestions_for_failures(
        self,
        checklist_results: list[ChecklistItem],
        content: ExtractedContent,
        similarity_scores: list | None = None,
    ) -> dict[str, str]:
        """
        Generuje sugestie dla wszystkich problemów.

        Args:
            checklist_results: Lista wyników checklisty
            content: Zawartość dokumentu
            similarity_scores: Lista scores similarity

        Returns:
            Słownik {kod_problemu: sugestia}
        """
        suggestions = {}

        # Filtruj tylko FAIL i WARNING
        problems = [
            item for item in checklist_results
            if item.status in (CheckStatus.FAIL, CheckStatus.WARNING)
        ]

        for item in problems:
            # Znajdź similarity score jeśli dotyczy
            sim_score = None
            if similarity_scores and item.code in ("CV-009", "CV-011"):
                for score in similarity_scores:
                    if (
                        (item.code == "CV-009" and score.element_a == "title" and score.element_b == "h1")
                        or (item.code == "CV-011")
                    ):
                        sim_score = score.score
                        break

            suggestion = self.generate_suggestion(item, content, sim_score)
            suggestions[item.code] = suggestion

        return suggestions

    def _build_prompt(
        self,
        item: ChecklistItem,
        content: ExtractedContent,
        similarity_score: float | None,
    ) -> str:
        """Buduje prompt dla konkretnego problemu (ładuje z plików)."""
        code = item.code

        # 1. Sprawdź czy jest dedykowany plik promptu (CV-XXX-*.txt)
        dedicated_prompt = load_prompt_for_code(code)
        if dedicated_prompt:
            # Przygotuj zmienne do podstawienia
            h2_texts = "\n".join([f"- {h.text}" for h in content.h2_list])
            h3_texts = "\n".join([f"- {h.text}" for h in content.h3_list])
            question_count = sum(1 for h in content.h2_list if h.is_question)
            total = len(content.h2_list) or 1

            try:
                return dedicated_prompt.format(
                    title=content.title or "",
                    meta=content.meta_description or "",
                    h1=content.h1 or "",
                    current_value=item.value or "N/A",
                    target=item.target or "N/A",
                    similarity=f"{similarity_score*100:.0f}" if similarity_score else "N/A",
                    similarity_issue="za niskie" if similarity_score and similarity_score < 0.80 else "za wysokie",
                    h2_list=h2_texts,
                    h3_list=h3_texts,
                    question_ratio=f"{question_count/total*100:.0f}",
                    problem=item.message or item.description,
                    element_type=item.name,
                )
            except KeyError as e:
                # Jeśli brakuje zmiennej w prompcie, użyj fallbacku
                pass

        # 2. Legacy - hardcoded prompts (do migracji)
        # H1-Title similarity
        if code == "CV-009" and similarity_score is not None:
            issue = "za niskie" if similarity_score < 0.80 else "za wysokie"
            return get_prompt_template("h1_similarity").format(
                title=content.title or "",
                current_h1=content.h1 or "",
                similarity=f"{similarity_score*100:.0f}",
                similarity_issue=issue,
            )

        # H2 questions
        if code == "CV-015":
            h2_texts = "\n".join([f"- {h.text}" for h in content.h2_list])
            question_count = sum(1 for h in content.h2_list if h.is_question)
            total = len(content.h2_list) or 1
            return get_prompt_template("h2_questions").format(
                current_h2_list=h2_texts,
                question_ratio=f"{question_count/total*100:.0f}",
            )

        # 3. Generic fallback
        return get_prompt_template("generic").format(
            element_type=item.name,
            current_value=item.value or "N/A",
            problem=item.message or item.description,
            title=content.title or "",
        )

    def check_ollama_available(self) -> tuple[bool, str]:
        """
        Sprawdza czy Ollama jest dostępna i ma wymagane modele.

        Returns:
            Tuple (is_available, message)
        """
        if not self.client.check_connection():
            return False, "Ollama nie jest uruchomiona. Uruchom: ollama serve"

        llm_model = self.client.llm_model
        if not self.client.has_model(llm_model):
            return False, f"Brak modelu {llm_model}. Pobierz: ollama pull {llm_model}"

        return True, f"Ollama gotowa (model: {llm_model})"
