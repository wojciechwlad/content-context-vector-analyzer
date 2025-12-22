"""Parser HTML do ekstrakcji elementów Content Context Vector."""

from bs4 import BeautifulSoup
from core.models import ExtractedContent, Heading, HeadingLevel


class HTMLParser:
    """Parser HTML ekstrahujący title, meta, h1-h3."""

    def parse(self, html_content: str) -> ExtractedContent:
        """
        Parsuje HTML i ekstrahuje elementy Content Context Vector.

        Args:
            html_content: Surowy kod HTML

        Returns:
            ExtractedContent z wyekstrahowanymi elementami
        """
        soup = BeautifulSoup(html_content, "lxml")

        content = ExtractedContent(source_type="html")

        # Title
        title_tag = soup.find("title")
        if title_tag:
            content.title = title_tag.get_text(strip=True)

        # Meta Description
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            content.meta_description = meta_tag["content"].strip()

        # H1
        h1_tags = soup.find_all("h1")
        content.h1_list = [h1.get_text(strip=True) for h1 in h1_tags if h1.get_text(strip=True)]

        # H2 i H3 z zachowaniem hierarchii
        content.h2_list, content.h3_list = self._extract_headings_with_hierarchy(soup)

        # Raw text (do analizy keyword density)
        content.raw_text = soup.get_text(separator=" ", strip=True)

        return content

    def _extract_headings_with_hierarchy(
        self, soup: BeautifulSoup
    ) -> tuple[list[Heading], list[Heading]]:
        """
        Ekstrahuje H2 i H3 z informacją o hierarchii.

        Returns:
            Tuple (lista H2, lista H3 z parent_index)
        """
        h2_list: list[Heading] = []
        h3_list: list[Heading] = []

        # Znajdź wszystkie nagłówki w kolejności dokumentu
        all_headings = soup.find_all(["h2", "h3"])

        position = 0
        current_h2_index = -1

        for heading in all_headings:
            text = heading.get_text(strip=True)
            if not text:
                continue

            if heading.name == "h2":
                h2 = Heading(
                    level=HeadingLevel.H2,
                    text=text,
                    position=position,
                )
                h2_list.append(h2)
                current_h2_index = len(h2_list) - 1

            elif heading.name == "h3":
                h3 = Heading(
                    level=HeadingLevel.H3,
                    text=text,
                    position=position,
                    parent_index=current_h2_index if current_h2_index >= 0 else None,
                )
                h3_list.append(h3)

            position += 1

        return h2_list, h3_list

    def detect_heading_issues(self, content: ExtractedContent) -> list[str]:
        """
        Wykrywa problemy z hierarchią nagłówków.

        Returns:
            Lista wykrytych problemów
        """
        issues = []

        # Sprawdź liczbę H1
        if content.h1_count == 0:
            issues.append("Brak nagłówka H1")
        elif content.h1_count > 1:
            issues.append(f"Wiele nagłówków H1 ({content.h1_count})")

        # Sprawdź H3 bez rodzica H2
        orphan_h3 = [h3 for h3 in content.h3_list if h3.parent_index is None]
        if orphan_h3:
            issues.append(f"H3 bez poprzedzającego H2 ({len(orphan_h3)} wystąpień)")

        # Sprawdź liczbę H2
        if content.h2_count < 4:
            issues.append(f"Za mało nagłówków H2 ({content.h2_count}, zalecane 4-8)")
        elif content.h2_count > 8:
            issues.append(f"Za dużo nagłówków H2 ({content.h2_count}, zalecane 4-8)")

        return issues
