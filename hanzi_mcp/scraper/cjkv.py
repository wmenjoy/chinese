"""Scraper for the CJKV Multilingual Glyph Database (ccamc.org)."""

from __future__ import annotations

from typing import Dict, List

from bs4 import BeautifulSoup, Tag

from .utils import create_session, node_text

BASE_URL = "http://ccamc.org/cjkv.php"


def _extract_sections(node: Tag) -> List[Dict[str, object]]:
    sections: List[Dict[str, object]] = []
    row_children = [child for child in node.find_all(recursive=False) if isinstance(child, Tag)]
    if not row_children:
        return sections
    for child in row_children:
        classes = child.get("class", [])
        if any(value.startswith("col-") for value in classes):
            # Nested rows often appear inside the main columns.
            nested_rows = child.find_all("div", class_="row", recursive=False)
            if nested_rows:
                for nested in nested_rows:
                    sections.extend(_extract_sections(nested))
            title_tag = child.find("p", class_="title")
            if not title_tag:
                continue
            title = node_text(title_tag) or ""
            title_tag.extract()
            values: List[str] = []
            # Capture all direct paragraph children after removing the title.
            for paragraph in child.find_all("p", recursive=False):
                text = node_text(paragraph)
                if text:
                    values.append(text)
            # Fallback to the full block text if no direct paragraphs remain.
            if not values:
                text = node_text(child)
                if text:
                    values.append(text)
            sections.append({"title": title, "values": values})
    return sections


def fetch_cjkv_data(character: str, *, session=None) -> Dict[str, object]:
    if session is None:
        session = create_session()

    response = session.get(BASE_URL, params={"cjkv": character}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    pane = soup.select_one("div.row.info.main div.tab-pane.active")
    if pane is None:
        # Some pages mark the active pane with both `active` and `in` classes.
        pane = soup.select_one("div.row.info.main div.tab-pane.in")

    sections: List[Dict[str, object]] = []
    if pane:
        sections = _extract_sections(pane)

    labels = [node_text(span) for span in soup.select("div.row.info.main span.label")]
    labels = [label for label in labels if label]

    return {
        "character": character,
        "title": node_text(soup.title),
        "sections": sections,
        "labels": labels,
    }
