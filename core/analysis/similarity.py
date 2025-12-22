"""Analiza podobieństwa semantycznego między elementami Content Context Vector."""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from config.settings import SIMILARITY_THRESHOLDS
from core.models import CheckStatus, SimilarityScore


class SimilarityAnalyzer:
    """Analizator podobieństwa semantycznego."""

    def __init__(self, thresholds: dict | None = None):
        """
        Inicjalizuje analizator.

        Args:
            thresholds: Słownik z progami similarity (opcjonalnie)
        """
        self.thresholds = thresholds or SIMILARITY_THRESHOLDS

    def compute_similarity(
        self, embedding_a: np.ndarray, embedding_b: np.ndarray
    ) -> float:
        """
        Oblicza cosine similarity między dwoma embeddingami.

        Args:
            embedding_a: Pierwszy embedding
            embedding_b: Drugi embedding

        Returns:
            Similarity score (0-1)
        """
        # Reshape dla sklearn
        a = embedding_a.reshape(1, -1)
        b = embedding_b.reshape(1, -1)
        return float(cosine_similarity(a, b)[0][0])

    def compute_similarity_matrix(
        self, embeddings: dict[str, np.ndarray]
    ) -> pd.DataFrame:
        """
        Oblicza macierz podobieństwa dla wszystkich elementów.

        Args:
            embeddings: Słownik {nazwa: embedding}

        Returns:
            DataFrame z macierzą similarity
        """
        labels = list(embeddings.keys())
        vectors = np.array([embeddings[k] for k in labels])

        sim_matrix = cosine_similarity(vectors)

        return pd.DataFrame(sim_matrix, index=labels, columns=labels)

    def analyze_core_alignment(
        self, embeddings: dict[str, np.ndarray]
    ) -> list[SimilarityScore]:
        """
        Analizuje semantic alignment dla Title-Meta-H1.

        Args:
            embeddings: Słownik z embeddingami (musi zawierać title, meta, h1)

        Returns:
            Lista SimilarityScore dla par Title-Meta, Title-H1, Meta-H1
        """
        scores = []

        # Title ↔ Meta
        if "title" in embeddings and "meta" in embeddings:
            score = self.compute_similarity(embeddings["title"], embeddings["meta"])
            thresholds = self.thresholds["title_meta"]
            scores.append(
                SimilarityScore(
                    element_a="title",
                    element_b="meta",
                    score=score,
                    status=self._evaluate_score(score, thresholds),
                    target_min=thresholds["target_min"],
                    target_max=thresholds["target_max"],
                )
            )

        # Title ↔ H1
        if "title" in embeddings and "h1" in embeddings:
            score = self.compute_similarity(embeddings["title"], embeddings["h1"])
            thresholds = self.thresholds["title_h1"]
            scores.append(
                SimilarityScore(
                    element_a="title",
                    element_b="h1",
                    score=score,
                    status=self._evaluate_score(score, thresholds),
                    target_min=thresholds["target_min"],
                    target_max=thresholds["target_max"],
                )
            )

        # Meta ↔ H1
        if "meta" in embeddings and "h1" in embeddings:
            score = self.compute_similarity(embeddings["meta"], embeddings["h1"])
            thresholds = self.thresholds["meta_h1"]
            scores.append(
                SimilarityScore(
                    element_a="meta",
                    element_b="h1",
                    score=score,
                    status=self._evaluate_score(score, thresholds),
                    target_min=thresholds["target_min"],
                    target_max=thresholds["target_max"],
                )
            )

        return scores

    def analyze_h2_alignment(
        self, embeddings: dict[str, np.ndarray]
    ) -> list[SimilarityScore]:
        """
        Analizuje similarity H2 do kontekstu sekcji (H1 lub Title).

        H2 powinno być porównywane z H1 (najbliższy kontekst),
        a nie bezpośrednio z Title.

        Args:
            embeddings: Słownik z embeddingami

        Returns:
            Lista SimilarityScore dla każdego H2
        """
        scores = []

        # Użyj H1 jako kontekstu, fallback do Title
        context_key = "h1" if "h1" in embeddings else "title" if "title" in embeddings else None
        if not context_key:
            return scores

        context_emb = embeddings[context_key]
        thresholds = self.thresholds["h2_title"]  # Te same progi

        for key, emb in embeddings.items():
            if key.startswith("h2_"):
                score = self.compute_similarity(context_emb, emb)
                scores.append(
                    SimilarityScore(
                        element_a=key,
                        element_b=context_key,
                        score=score,
                        status=self._evaluate_score(score, thresholds),
                        target_min=thresholds["target_min"],
                        target_max=thresholds["target_max"],
                    )
                )

        return scores

    def detect_topic_drift(
        self, embeddings: dict[str, np.ndarray]
    ) -> list[tuple[str, str, float]]:
        """
        Wykrywa elementy z niskim similarity do ich kontekstu rodzica.

        Hierarchia porównań:
        - H1 → Title (główny temat)
        - H2 → H1 (kontekst sekcji)
        - H3 → H1 (uproszczone, ideanie H3→parent H2)
        - Meta → Title

        Args:
            embeddings: Słownik z embeddingami

        Returns:
            Lista (element, parent, score) dla elementów z drift
        """
        drifts = []
        threshold = self.thresholds["topic_drift"]

        # Wybierz główny kontekst: H1 jeśli dostępny, inaczej Title
        context_key = "h1" if "h1" in embeddings else "title" if "title" in embeddings else None
        if not context_key:
            return drifts

        context_emb = embeddings[context_key]

        for name, emb in embeddings.items():
            # Pomiń sam kontekst i podstawowe elementy
            if name in ("title", "meta", "h1", context_key):
                continue

            score = self.compute_similarity(context_emb, emb)
            if score < threshold:
                drifts.append((name, context_key, score))

        return drifts

    def _evaluate_score(self, score: float, thresholds: dict) -> CheckStatus:
        """
        Ocenia score względem progów.

        Logika: Wyższe similarity = lepsze (chyba że to duplikacja).
        - >= target_min = PASS (spełnia lub przekracza wymagania)
        - >= min = WARNING (poniżej optymalnego, ale akceptowalne)
        - < min = FAIL (za niskie similarity)

        Args:
            score: Wartość similarity (0-1)
            thresholds: Słownik z min, target_min, target_max, max

        Returns:
            CheckStatus (PASS, WARNING, FAIL)
        """
        if score >= thresholds["target_min"]:
            return CheckStatus.PASS  # Spełnione lub lepiej
        elif score >= thresholds["min"]:
            return CheckStatus.WARNING  # Akceptowalne, ale poniżej optimum
        else:
            return CheckStatus.FAIL  # Za niskie similarity


def get_similarity_color(score: float) -> str:
    """
    Zwraca kolor na podstawie score similarity.

    Args:
        score: Wartość similarity (0-1)

    Returns:
        Kolor w formacie hex
    """
    if score >= 0.8:
        return "#28a745"  # zielony
    elif score >= 0.6:
        return "#ffc107"  # żółty
    elif score >= 0.4:
        return "#fd7e14"  # pomarańczowy
    else:
        return "#dc3545"  # czerwony
