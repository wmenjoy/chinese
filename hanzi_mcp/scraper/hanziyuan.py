"""Scraper for ChineseEtymology / hanziyuan.net."""

from __future__ import annotations

from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

from .utils import create_session, node_text

INDEX_URL = "https://hanziyuan.net/"
QUERY_URL = "https://hanziyuan.net/Etymology"


def _ensure_tokens(session) -> Tuple[str, str]:
    response = session.get(INDEX_URL, timeout=30)
    response.raise_for_status()
    bronze = session.cookies.get("Bronze")
    oracle = session.cookies.get("Oracle")
    if not bronze or not oracle:
        raise RuntimeError("Unable to obtain anti-forgery tokens from hanziyuan.net")
    return bronze, oracle


def _parse_summary(soup: BeautifulSoup) -> Dict[str, object]:
    summary_block = soup.select_one(".etymology-alert")
    if not summary_block:
        return {}
    summary_label = summary_block.find("strong")
    label_text = node_text(summary_label)
    label = None
    if label_text:
        label = label_text.strip(" :")
    counts = [node_text(span) for span in summary_block.select("span.label")]
    return {
        "character": label,
        "text": node_text(summary_block),
        "labels": [count for count in counts if count],
    }


def _parse_left_column(column) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    if not column:
        return entries
    for paragraph in column.find_all("p"):
        label_tag = paragraph.find("b")
        label = node_text(label_tag).rstrip(":") if label_tag else None
        if label_tag:
            label_tag.extract()
        value = node_text(paragraph)
        if not value and not label:
            continue
        entries.append({"label": label, "value": value or ""})
    return entries


def _collect_section_content(heading) -> Dict[str, object]:
    title = node_text(heading) or ""
    items: List[str] = []
    pointer = heading.find_next_sibling()
    while pointer and pointer.name in {"p", "ul", "pre", "div", "ol"}:
        if pointer.name == "ul" or pointer.name == "ol":
            for item in pointer.find_all("li"):
                text = node_text(item)
                if text:
                    items.append(text)
        elif pointer.name == "div" and "row" in pointer.get("class", []):
            text = node_text(pointer)
            if text:
                items.append(text)
        else:
            text = node_text(pointer)
            if text:
                items.append(text)
        pointer = pointer.find_next_sibling()
        if pointer and pointer.name == "h3":
            break
    return {"title": title, "items": items}


def _parse_right_column(column) -> List[Dict[str, object]]:
    sections: List[Dict[str, object]] = []
    if not column:
        return sections
    for heading in column.find_all("h3"):
        sections.append(_collect_section_content(heading))
    return sections


def fetch_hanziyuan_data(character: str, *, session=None) -> Dict[str, object]:
    if session is None:
        session = create_session()

    bronze, _oracle = _ensure_tokens(session)
    headers = {
        "Chinese": str(ord(character)),
        "Seal": bronze,
        "Referer": INDEX_URL,
        "Origin": "https://hanziyuan.net",
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {"chinese": character, "Bronze": bronze}
    response = session.post(QUERY_URL, headers=headers, data=payload, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    result: Dict[str, object] = {
        "character": character,
        "summary": _parse_summary(soup),
        "entries": [],
    }

    for row in soup.select("div.row.mx-0.bg-info.row-eq-height.border-top.border-purple"):
        left = row.select_one(".col-md-3")
        right = row.select_one(".col-md-9")
        result["entries"].append(
            {
                "id": row.get("id"),
                "metadata": _parse_left_column(left),
                "sections": _parse_right_column(right),
            }
        )
    return result
