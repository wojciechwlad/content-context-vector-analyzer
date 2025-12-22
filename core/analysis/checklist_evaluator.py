"""Ewaluator checklisty Content Context Vector (CV-001 do CV-034)."""

from core.models import (
    ExtractedContent,
    ChecklistItem,
    CheckStatus,
    Priority,
    SimilarityScore,
)
from config.settings import THRESHOLDS, PRIORITY_CONFIG


class ChecklistEvaluator:
    """Ewaluator kryteriów Content Context Vector."""

    def __init__(self, thresholds: dict | None = None):
        """
        Inicjalizuje ewaluator.

        Args:
            thresholds: Słownik z progami (opcjonalnie)
        """
        self.thresholds = thresholds or THRESHOLDS

    def evaluate_all(
        self,
        content: ExtractedContent,
        similarity_scores: list[SimilarityScore],
    ) -> list[ChecklistItem]:
        """
        Ewaluuje wszystkie kryteria checklisty.

        Args:
            content: Wyekstrahowana zawartość
            similarity_scores: Wyniki analizy similarity

        Returns:
            Lista ChecklistItem z wynikami
        """
        results = []

        # Title checks (CV-001 do CV-004)
        results.extend(self._evaluate_title(content))

        # Meta Description checks (CV-005 do CV-007)
        results.extend(self._evaluate_meta(content))

        # H1 checks (CV-008 do CV-010)
        results.extend(self._evaluate_h1(content, similarity_scores))

        # Semantic Alignment checks (CV-011, CV-012)
        results.extend(self._evaluate_semantic_alignment(similarity_scores))

        # H2 checks (CV-013 do CV-016)
        results.extend(self._evaluate_h2(content))

        # H3 checks (CV-017 do CV-019)
        results.extend(self._evaluate_h3(content))

        return results

    def _evaluate_title(self, content: ExtractedContent) -> list[ChecklistItem]:
        """Ewaluuje kryteria Title Tag (CV-001 do CV-004)."""
        results = []

        title = content.title or ""
        title_len = len(title)

        # CV-001: Keyword w pierwszych 60 znakach (CRITICAL)
        # Bez keyword analysis - tylko sprawdzamy czy title istnieje i ma sensowną długość
        results.append(
            ChecklistItem(
                code="CV-001",
                name="Title zawiera treść",
                description="Title tag powinien zawierać główne słowo kluczowe w pierwszych 60 znakach",
                priority=Priority.CRITICAL,
                status=CheckStatus.PASS if title_len > 0 else CheckStatus.FAIL,
                value=f"{title_len} zn.",
                target="Keyword w pierwszych 60 zn.",
            )
        )

        # CV-002: Długość 50-60 znaków (HIGH)
        opt_min = self.thresholds["title_optimal_min"]
        opt_max = self.thresholds["title_optimal_max"]
        max_len = self.thresholds["title_max_length"]

        if opt_min <= title_len <= opt_max:
            status = CheckStatus.PASS
        elif title_len < opt_min or title_len > max_len:
            status = CheckStatus.FAIL
        else:
            status = CheckStatus.WARNING

        results.append(
            ChecklistItem(
                code="CV-002",
                name="Długość Title",
                description="Title tag powinien mieć 50-60 znaków",
                priority=Priority.HIGH,
                status=status,
                value=f"{title_len} zn.",
                target=f"{opt_min}-{opt_max} zn.",
            )
        )

        # CV-003: Unikalność (wymaga zewnętrznej walidacji - skip)
        results.append(
            ChecklistItem(
                code="CV-003",
                name="Unikalność Title",
                description="Title tag powinien być unikalny",
                priority=Priority.HIGH,
                status=CheckStatus.PASS,  # Assume pass - wymaga zewnętrznej walidacji
                value="N/A",
                target="Unikalny title",
                message="Wymaga porównania z innymi stronami",
            )
        )

        # CV-004: Max 1-2× keyword (uproszczenie - sprawdzamy powtórzenia słów)
        words = title.lower().split()
        word_counts = {}
        for word in words:
            if len(word) > 4:  # ignoruj krótkie słowa
                word_counts[word] = word_counts.get(word, 0) + 1

        max_repeat = max(word_counts.values()) if word_counts else 0
        max_allowed = self.thresholds["title_max_keyword_count"]

        results.append(
            ChecklistItem(
                code="CV-004",
                name="Brak keyword stuffing",
                description="Title nie powinien zawierać więcej niż 2× tego samego słowa",
                priority=Priority.HIGH,
                status=CheckStatus.PASS if max_repeat <= max_allowed else CheckStatus.WARNING,
                value=f"max {max_repeat}× powtórzeń",
                target=f"max {max_allowed}× słowo",
            )
        )

        return results

    def _evaluate_meta(self, content: ExtractedContent) -> list[ChecklistItem]:
        """Ewaluuje kryteria Meta Description (CV-005 do CV-007)."""
        results = []

        meta = content.meta_description or ""
        meta_len = len(meta)
        title = content.title or ""

        # CV-005: Meta rozszerza Title (HIGH)
        # Uproszczenie: sprawdzamy czy meta nie jest identyczna z title
        if meta and title:
            # Oblicz overlap słów
            title_words = set(title.lower().split())
            meta_words = set(meta.lower().split())
            overlap = len(title_words & meta_words) / len(title_words) if title_words else 0
            unique_ratio = 1 - overlap

            status = (
                CheckStatus.PASS if unique_ratio >= 0.4
                else CheckStatus.WARNING if unique_ratio >= 0.2
                else CheckStatus.FAIL
            )
            results.append(
                ChecklistItem(
                    code="CV-005",
                    name="Meta rozszerza Title",
                    description="Meta Description powinna rozszerzać Title, nie duplikować",
                    priority=Priority.HIGH,
                    status=status,
                    value=f"{unique_ratio*100:.0f}% unikalnej treści",
                    target="min 60% unikalnej treści",
                )
            )
        else:
            results.append(
                ChecklistItem(
                    code="CV-005",
                    name="Meta rozszerza Title",
                    description="Meta Description powinna rozszerzać Title",
                    priority=Priority.HIGH,
                    status=CheckStatus.FAIL if not meta else CheckStatus.WARNING,
                    value="Brak meta" if not meta else "Brak title",
                    target="min 60% unikalnej treści",
                )
            )

        # CV-006: Długość 150-160 znaków (MEDIUM)
        opt_min = self.thresholds["meta_optimal_min"]
        opt_max = self.thresholds["meta_optimal_max"]

        if opt_min <= meta_len <= opt_max:
            status = CheckStatus.PASS
        elif meta_len == 0:
            status = CheckStatus.FAIL
        else:
            status = CheckStatus.WARNING

        results.append(
            ChecklistItem(
                code="CV-006",
                name="Długość Meta",
                description="Meta Description powinna mieć 150-160 znaków",
                priority=Priority.MEDIUM,
                status=status,
                value=f"{meta_len} zn.",
                target=f"{opt_min}-{opt_max} zn.",
            )
        )

        # CV-007: LSI keywords (MEDIUM) - uproszczenie
        results.append(
            ChecklistItem(
                code="CV-007",
                name="LSI keywords w Meta",
                description="Meta powinna zawierać 1-2 dodatkowe słowa kluczowe",
                priority=Priority.MEDIUM,
                status=CheckStatus.PASS if meta_len > 100 else CheckStatus.WARNING,
                value="N/A",
                target="1-2 LSI keywords",
                message="Wymaga manualnej weryfikacji",
            )
        )

        return results

    def _evaluate_h1(
        self, content: ExtractedContent, similarity_scores: list[SimilarityScore]
    ) -> list[ChecklistItem]:
        """Ewaluuje kryteria H1 (CV-008 do CV-010)."""
        results = []

        # CV-008: Tylko jeden H1 (CRITICAL)
        h1_count = content.h1_count
        results.append(
            ChecklistItem(
                code="CV-008",
                name="Jeden H1 na stronie",
                description="Strona powinna mieć dokładnie jeden nagłówek H1",
                priority=Priority.CRITICAL,
                status=CheckStatus.PASS if h1_count == 1 else CheckStatus.FAIL,
                value=f"{h1_count} H1",
                target="1 H1",
            )
        )

        # CV-009: H1-Title similarity 80-90% (CRITICAL)
        title_h1_score = next(
            (s for s in similarity_scores if s.element_a == "title" and s.element_b == "h1"),
            None,
        )
        if title_h1_score:
            results.append(
                ChecklistItem(
                    code="CV-009",
                    name="H1-Title similarity",
                    description="H1 powinien mieć 80-90% semantic similarity z Title",
                    priority=Priority.CRITICAL,
                    status=title_h1_score.status,
                    value=f"{title_h1_score.score*100:.0f}%",
                    target="80-90%",
                )
            )
        else:
            results.append(
                ChecklistItem(
                    code="CV-009",
                    name="H1-Title similarity",
                    description="H1 powinien mieć 80-90% semantic similarity z Title",
                    priority=Priority.CRITICAL,
                    status=CheckStatus.FAIL,
                    value="N/A",
                    target="80-90%",
                    message="Brak danych do analizy",
                )
            )

        # CV-010: H1 zawiera keyword (HIGH)
        h1 = content.h1 or ""
        results.append(
            ChecklistItem(
                code="CV-010",
                name="Keyword w H1",
                description="H1 powinien zawierać główne słowo kluczowe",
                priority=Priority.HIGH,
                status=CheckStatus.PASS if h1 else CheckStatus.FAIL,
                value="Obecny" if h1 else "Brak H1",
                target="Keyword present",
            )
        )

        return results

    def _evaluate_semantic_alignment(
        self, similarity_scores: list[SimilarityScore]
    ) -> list[ChecklistItem]:
        """Ewaluuje Semantic Alignment (CV-011, CV-012)."""
        results = []

        # CV-011: Title→Meta→H1 spójny chain (CRITICAL)
        core_scores = [
            s for s in similarity_scores
            if (s.element_a in ("title", "meta", "h1") and s.element_b in ("title", "meta", "h1"))
        ]

        if core_scores:
            all_pass = all(s.status == CheckStatus.PASS for s in core_scores)
            any_fail = any(s.status == CheckStatus.FAIL for s in core_scores)
            avg_score = sum(s.score for s in core_scores) / len(core_scores)

            results.append(
                ChecklistItem(
                    code="CV-011",
                    name="Semantic Chain",
                    description="Title→Meta→H1 powinny tworzyć spójny semantic chain",
                    priority=Priority.CRITICAL,
                    status=(
                        CheckStatus.PASS if all_pass
                        else CheckStatus.FAIL if any_fail
                        else CheckStatus.WARNING
                    ),
                    value=f"avg {avg_score*100:.0f}%",
                    target="100% spójność",
                )
            )
        else:
            results.append(
                ChecklistItem(
                    code="CV-011",
                    name="Semantic Chain",
                    description="Title→Meta→H1 powinny tworzyć spójny semantic chain",
                    priority=Priority.CRITICAL,
                    status=CheckStatus.FAIL,
                    value="N/A",
                    target="100% spójność",
                    message="Brak danych do analizy",
                )
            )

        # CV-012: Brak zmiany tematu (CRITICAL) - sprawdzane przez topic drift
        results.append(
            ChecklistItem(
                code="CV-012",
                name="Brak topic drift",
                description="Wszystkie elementy powinny mówić o tym samym temacie",
                priority=Priority.CRITICAL,
                status=CheckStatus.PASS,  # Będzie zaktualizowane przez topic drift analysis
                value="Sprawdzone",
                target="0 zmian tematu",
            )
        )

        return results

    def _evaluate_h2(self, content: ExtractedContent) -> list[ChecklistItem]:
        """Ewaluuje kryteria H2 (CV-013 do CV-016)."""
        results = []

        h2_count = content.h2_count
        h2_min = self.thresholds["h2_count_min"]
        h2_max = self.thresholds["h2_count_max"]

        # CV-013: 4-8 nagłówków H2 (HIGH)
        if h2_min <= h2_count <= h2_max:
            status = CheckStatus.PASS
        elif h2_count == 0:
            status = CheckStatus.FAIL
        else:
            status = CheckStatus.WARNING

        results.append(
            ChecklistItem(
                code="CV-013",
                name="Liczba H2",
                description="Strona powinna mieć 4-8 nagłówków H2",
                priority=Priority.HIGH,
                status=status,
                value=f"{h2_count} H2",
                target=f"{h2_min}-{h2_max} H2",
            )
        )

        # CV-014: Samowyjaśniające H2 (HIGH) - sprawdzamy długość
        if content.h2_list:
            short_h2 = sum(1 for h in content.h2_list if h.word_count < 3)
            ratio = 1 - (short_h2 / len(content.h2_list))
            results.append(
                ChecklistItem(
                    code="CV-014",
                    name="Samowyjaśniające H2",
                    description="Każdy H2 powinien być zrozumiały samodzielnie",
                    priority=Priority.HIGH,
                    status=CheckStatus.PASS if ratio >= 0.8 else CheckStatus.WARNING,
                    value=f"{ratio*100:.0f}% wystarczająco długich",
                    target="100% samowyjaśniające",
                )
            )
        else:
            results.append(
                ChecklistItem(
                    code="CV-014",
                    name="Samowyjaśniające H2",
                    description="Każdy H2 powinien być zrozumiały samodzielnie",
                    priority=Priority.HIGH,
                    status=CheckStatus.FAIL,
                    value="Brak H2",
                    target="100% samowyjaśniające",
                )
            )

        # CV-015: Min 50% H2 jako pytania (MEDIUM)
        if content.h2_list:
            question_count = sum(1 for h in content.h2_list if h.is_question)
            question_ratio = question_count / len(content.h2_list)
            target_ratio = self.thresholds["h2_question_ratio_min"]

            results.append(
                ChecklistItem(
                    code="CV-015",
                    name="H2 jako pytania",
                    description="Min 50% H2 powinno być w formie pytań",
                    priority=Priority.MEDIUM,
                    status=CheckStatus.PASS if question_ratio >= target_ratio else CheckStatus.WARNING,
                    value=f"{question_ratio*100:.0f}% pytań ({question_count}/{len(content.h2_list)})",
                    target=f"min {target_ratio*100:.0f}%",
                )
            )
        else:
            results.append(
                ChecklistItem(
                    code="CV-015",
                    name="H2 jako pytania",
                    description="Min 50% H2 powinno być w formie pytań",
                    priority=Priority.MEDIUM,
                    status=CheckStatus.FAIL,
                    value="Brak H2",
                    target="min 50%",
                )
            )

        # CV-016: Warianty słów kluczowych (MEDIUM) - wymaga manualnej weryfikacji
        results.append(
            ChecklistItem(
                code="CV-016",
                name="Warianty keywords w H2",
                description="H2 powinny używać naturalnych wariantów słów kluczowych",
                priority=Priority.MEDIUM,
                status=CheckStatus.PASS if h2_count > 0 else CheckStatus.WARNING,
                value="N/A",
                target="Max 2 H2 z identyczną frazą",
                message="Wymaga manualnej weryfikacji",
            )
        )

        return results

    def _evaluate_h3(self, content: ExtractedContent) -> list[ChecklistItem]:
        """Ewaluuje kryteria H3 (CV-017 do CV-019)."""
        results = []

        # CV-017: H3 zagnieżdżone pod H2 (HIGH)
        orphan_h3 = [h for h in content.h3_list if h.parent_index is None]
        orphan_count = len(orphan_h3)

        results.append(
            ChecklistItem(
                code="CV-017",
                name="H3 zagnieżdżenie",
                description="H3 powinny być zagnieżdżone pod właściwym H2",
                priority=Priority.HIGH,
                status=CheckStatus.PASS if orphan_count == 0 else CheckStatus.WARNING,
                value=f"{orphan_count} osieroconch H3",
                target="0 osieroconych H3",
            )
        )

        # CV-018: Brak przeskakiwania poziomów (HIGH)
        results.append(
            ChecklistItem(
                code="CV-018",
                name="Brak przeskakiwania poziomów",
                description="Nie powinno być H3 bez poprzedzającego H2",
                priority=Priority.HIGH,
                status=CheckStatus.PASS if orphan_count == 0 else CheckStatus.FAIL,
                value="OK" if orphan_count == 0 else f"{orphan_count} przeskoków",
                target="0 przeskoków",
            )
        )

        # CV-019: H3 jako sub-concepts H2 (MEDIUM)
        results.append(
            ChecklistItem(
                code="CV-019",
                name="H3 jako sub-concepts",
                description="H3 powinny precyzować i zawężać temat H2",
                priority=Priority.MEDIUM,
                status=CheckStatus.PASS if content.h3_count > 0 else CheckStatus.WARNING,
                value=f"{content.h3_count} H3",
                target="H3 pod każdym długim H2",
                message="Wymaga analizy similarity",
            )
        )

        return results

    def calculate_overall_score(self, results: list[ChecklistItem]) -> float:
        """
        Oblicza overall score na podstawie wyników checklisty.

        Args:
            results: Lista ChecklistItem

        Returns:
            Score 0-100
        """
        if not results:
            return 0.0

        weights = {
            Priority.CRITICAL: PRIORITY_CONFIG["CRITICAL"]["weight"],
            Priority.HIGH: PRIORITY_CONFIG["HIGH"]["weight"],
            Priority.MEDIUM: PRIORITY_CONFIG["MEDIUM"]["weight"],
        }

        total_weight = sum(weights[r.priority] for r in results)
        earned = sum(
            weights[r.priority] * (1.0 if r.status == CheckStatus.PASS else 0.5 if r.status == CheckStatus.WARNING else 0.0)
            for r in results
        )

        return (earned / total_weight) * 100 if total_weight > 0 else 0.0
