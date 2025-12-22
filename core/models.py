"""Modele danych dla Content Context Vector Analyzer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import numpy as np


class HeadingLevel(Enum):
    """Poziomy nagłówków."""
    H1 = 1
    H2 = 2
    H3 = 3


class CheckStatus(Enum):
    """Status sprawdzenia checklisty."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class Priority(Enum):
    """Priorytet elementu checklisty."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


@dataclass
class Heading:
    """Model nagłówka z pozycją i relacją do rodzica."""
    level: HeadingLevel
    text: str
    position: int
    parent_index: Optional[int] = None  # indeks rodzica H2 dla H3
    embedding: Optional[np.ndarray] = None

    @property
    def is_question(self) -> bool:
        """Sprawdza czy nagłówek jest pytaniem."""
        return self.text.strip().endswith("?")

    @property
    def word_count(self) -> int:
        """Liczba słów w nagłówku."""
        return len(self.text.split())


@dataclass
class ExtractedContent:
    """Wyekstrahowana zawartość dokumentu."""
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1_list: list[str] = field(default_factory=list)
    h2_list: list[Heading] = field(default_factory=list)
    h3_list: list[Heading] = field(default_factory=list)
    raw_text: str = ""
    source_type: str = "html"  # "html" lub "markdown"

    @property
    def h1(self) -> Optional[str]:
        """Zwraca pierwszy H1 lub None."""
        return self.h1_list[0] if self.h1_list else None

    @property
    def h1_count(self) -> int:
        """Liczba nagłówków H1."""
        return len(self.h1_list)

    @property
    def h2_count(self) -> int:
        """Liczba nagłówków H2."""
        return len(self.h2_list)

    @property
    def h3_count(self) -> int:
        """Liczba nagłówków H3."""
        return len(self.h3_list)

    def get_all_text_elements(self) -> dict[str, str]:
        """Zwraca wszystkie elementy tekstowe do embeddingu."""
        elements = {}

        if self.title:
            elements["title"] = self.title
        if self.meta_description:
            elements["meta"] = self.meta_description
        if self.h1:
            elements["h1"] = self.h1

        for i, h2 in enumerate(self.h2_list):
            elements[f"h2_{i}"] = h2.text

        for i, h3 in enumerate(self.h3_list):
            elements[f"h3_{i}"] = h3.text

        return elements

    def get_display_name(self, key: str) -> str:
        """
        Konwertuje klucz techniczny na czytelną etykietę dla UI.

        Args:
            key: Klucz techniczny (np. 'title', 'h2_0', 'h3_1')

        Returns:
            Czytelna etykieta (np. 'Title', 'H2: Jak to działa...', 'H3: Przykłady...')
        """
        if key == "title":
            preview = self.title[:40] + "..." if self.title and len(self.title) > 40 else self.title
            return f"Title: {preview}" if self.title else "Title"
        elif key == "meta":
            preview = self.meta_description[:40] + "..." if self.meta_description and len(self.meta_description) > 40 else self.meta_description
            return f"Meta: {preview}" if self.meta_description else "Meta Description"
        elif key == "h1":
            preview = self.h1[:40] + "..." if self.h1 and len(self.h1) > 40 else self.h1
            return f"H1: {preview}" if self.h1 else "H1"
        elif key.startswith("h2_"):
            idx = int(key.split("_")[1])
            if idx < len(self.h2_list):
                text = self.h2_list[idx].text
                preview = text[:35] + "..." if len(text) > 35 else text
                return f"H2: {preview}"
            return key
        elif key.startswith("h3_"):
            idx = int(key.split("_")[1])
            if idx < len(self.h3_list):
                text = self.h3_list[idx].text
                preview = text[:35] + "..." if len(text) > 35 else text
                return f"H3: {preview}"
            return key
        return key

    def get_all_display_names(self) -> dict[str, str]:
        """
        Zwraca mapowanie klucz techniczny -> etykieta wyświetlana.

        Returns:
            Słownik {klucz: etykieta} dla wszystkich elementów
        """
        elements = self.get_all_text_elements()
        return {key: self.get_display_name(key) for key in elements.keys()}


@dataclass
class ChecklistItem:
    """Element checklisty CV-*."""
    code: str  # np. "CV-001"
    name: str
    description: str
    priority: Priority
    status: CheckStatus = CheckStatus.PASS
    value: Optional[str] = None  # aktualna wartość (np. "52 zn.")
    target: Optional[str] = None  # oczekiwana wartość
    message: Optional[str] = None  # dodatkowa informacja


@dataclass
class SimilarityScore:
    """Wynik podobieństwa między dwoma elementami."""
    element_a: str
    element_b: str
    score: float
    status: CheckStatus
    target_min: float
    target_max: float


@dataclass
class AnalysisResult:
    """Pełny wynik analizy dokumentu."""
    content: ExtractedContent
    embeddings: dict[str, np.ndarray]
    similarity_scores: list[SimilarityScore]
    checklist_results: list[ChecklistItem]
    topic_drifts: list[tuple[str, str, float]]
    overall_score: float

    @property
    def critical_issues(self) -> list[ChecklistItem]:
        """Zwraca krytyczne problemy (FAIL na CRITICAL)."""
        return [
            item for item in self.checklist_results
            if item.status == CheckStatus.FAIL and item.priority == Priority.CRITICAL
        ]

    @property
    def warnings(self) -> list[ChecklistItem]:
        """Zwraca ostrzeżenia."""
        return [
            item for item in self.checklist_results
            if item.status == CheckStatus.WARNING
        ]

    @property
    def failures(self) -> list[ChecklistItem]:
        """Zwraca wszystkie błędy."""
        return [
            item for item in self.checklist_results
            if item.status == CheckStatus.FAIL
        ]
