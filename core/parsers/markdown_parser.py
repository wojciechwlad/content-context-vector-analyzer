"""Parser Markdown do ekstrakcji elementów Content Context Vector."""

import re
from markdown_it import MarkdownIt
from core.models import ExtractedContent, Heading, HeadingLevel


class MarkdownParser:
    """Parser Markdown ekstrahujący nagłówki i metadane."""

    def __init__(self):
        """Inicjalizuje parser Markdown."""
        self.md = MarkdownIt()

    def parse(self, markdown_content: str) -> ExtractedContent:
        """
        Parsuje Markdown i ekstrahuje elementy Content Context Vector.

        Args:
            markdown_content: Surowy tekst Markdown

        Returns:
            ExtractedContent z wyekstrahowanymi elementami
        """
        content = ExtractedContent(source_type="markdown")

        # Usuń frontmatter YAML jeśli istnieje
        clean_content = self._remove_frontmatter(markdown_content)

        # Ekstrakcja nagłówków
        content.h1_list = self._extract_headings_by_level(clean_content, 1)
        content.h2_list, content.h3_list = self._extract_h2_h3_with_hierarchy(clean_content)

        # W Markdown nie ma bezpośrednich odpowiedników title i meta
        # Używamy H1 jako title jeśli jest dokładnie jeden
        if len(content.h1_list) == 1:
            content.title = content.h1_list[0]

        # Próba wyekstrahowania description z frontmatter
        content.meta_description = self._extract_frontmatter_field(markdown_content, "description")

        # Raw text (bez nagłówków)
        content.raw_text = self._get_plain_text(clean_content)

        return content

    def _remove_frontmatter(self, content: str) -> str:
        """Usuwa YAML frontmatter z początku dokumentu."""
        frontmatter_pattern = r"^---\s*\n.*?\n---\s*\n"
        return re.sub(frontmatter_pattern, "", content, flags=re.DOTALL)

    def _extract_frontmatter_field(self, content: str, field: str) -> str | None:
        """Ekstrahuje pole z YAML frontmatter."""
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            return None

        frontmatter = frontmatter_match.group(1)
        field_pattern = rf"^{field}:\s*['\"]?(.+?)['\"]?\s*$"
        field_match = re.search(field_pattern, frontmatter, re.MULTILINE)

        return field_match.group(1) if field_match else None

    def _extract_headings_by_level(self, content: str, level: int) -> list[str]:
        """Ekstrahuje nagłówki danego poziomu."""
        pattern = rf"^{'#' * level}\s+(.+?)$"
        matches = re.findall(pattern, content, re.MULTILINE)
        return [m.strip() for m in matches]

    def _extract_h2_h3_with_hierarchy(
        self, content: str
    ) -> tuple[list[Heading], list[Heading]]:
        """
        Ekstrahuje H2 i H3 z informacją o hierarchii.

        Returns:
            Tuple (lista H2, lista H3 z parent_index)
        """
        h2_list: list[Heading] = []
        h3_list: list[Heading] = []

        # Znajdź wszystkie nagłówki ## i ### w kolejności
        pattern = r"^(#{2,3})\s+(.+?)$"
        matches = re.finditer(pattern, content, re.MULTILINE)

        position = 0
        current_h2_index = -1

        for match in matches:
            level_str = match.group(1)
            text = match.group(2).strip()

            if not text:
                continue

            if level_str == "##":
                h2 = Heading(
                    level=HeadingLevel.H2,
                    text=text,
                    position=position,
                )
                h2_list.append(h2)
                current_h2_index = len(h2_list) - 1

            elif level_str == "###":
                h3 = Heading(
                    level=HeadingLevel.H3,
                    text=text,
                    position=position,
                    parent_index=current_h2_index if current_h2_index >= 0 else None,
                )
                h3_list.append(h3)

            position += 1

        return h2_list, h3_list

    def _get_plain_text(self, content: str) -> str:
        """Konwertuje Markdown na plain text."""
        # Usuń nagłówki
        text = re.sub(r"^#+\s+.+$", "", content, flags=re.MULTILINE)
        # Usuń linki [text](url) → text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Usuń obrazy
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
        # Usuń pogrubienie i kursywę
        text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text)
        # Usuń kod inline
        text = re.sub(r"`([^`]+)`", r"\1", text)
        # Usuń bloki kodu
        text = re.sub(r"```[\s\S]*?```", "", text)
        # Normalizuj białe znaki
        text = re.sub(r"\s+", " ", text)

        return text.strip()
