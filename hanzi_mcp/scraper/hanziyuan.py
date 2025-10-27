"""Scraper for ChineseEtymology / hanziyuan.net."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

from .utils import assign_value, create_session, node_text

INDEX_URL = "https://hanziyuan.net/"
QUERY_URL = "https://hanziyuan.net/Etymology"

SUMMARY_RE = re.compile(
    r"Found\s+(?P<etymologies>\d+)\s+etymologies\s+and\s+(?P<characters>\d+)\s+characters\s+in\s+(?P<seconds>[0-9.]+)"
)
ITEM_ID_RE = re.compile(r"^[A-Z][0-9A-Z]+$")


def _ensure_tokens(session) -> Tuple[str, str]:
    response = session.get(INDEX_URL, timeout=30)
    response.raise_for_status()
    bronze = session.cookies.get("Bronze")
    oracle = session.cookies.get("Oracle")
    if not bronze or not oracle:
        raise RuntimeError("Unable to obtain anti-forgery tokens from hanziyuan.net")
    return bronze, oracle


def _structure_item_value(value: str) -> Dict[str, str]:
    parts = value.split()
    if parts and ITEM_ID_RE.match(parts[0]):
        remainder = " ".join(parts[1:]).strip()
        data = {"id": parts[0]}
        if remainder and remainder != parts[0]:
            data["text"] = remainder
        return data
    return {"text": value}


def _parse_summary(soup: BeautifulSoup) -> Dict[str, object]:
    summary_block = soup.select_one(".etymology-alert")
    if not summary_block:
        return {}

    content_text = node_text(summary_block) or ""

    result: Dict[str, object] = {"text": content_text}

    summary_label = summary_block.find("strong")
    label_text = node_text(summary_label)
    if label_text:
        result["character"] = label_text.strip(" :")

    match = SUMMARY_RE.search(content_text)
    if match:
        result["counts"] = {
            "etymologies": int(match.group("etymologies")),
            "characters": int(match.group("characters")),
        }
        result["elapsed_seconds"] = float(match.group("seconds"))

    badges = []
    for span in summary_block.select("span.label"):
        label = node_text(span)
        if label:
            badges.append(_structure_item_value(label))
    if badges:
        result["identifiers"] = badges

    return result


def _parse_left_column(column) -> Dict[str, object]:
    metadata: Dict[str, object] = {}
    if not column:
        return metadata

    notes: List[str] = []
    for paragraph in column.find_all("p"):
        label_tag = paragraph.find("b")
        label = node_text(label_tag).rstrip(":") if label_tag else None
        if label_tag:
            label_tag.extract()
        value = node_text(paragraph)
        if not value:
            continue
        if label:
            assign_value(metadata, label, value)
        else:
            notes.append(value)
    if notes:
        metadata["notes"] = notes
    return metadata


def _collect_section_content(heading) -> Dict[str, object]:
    title = node_text(heading) or ""
    items: List[Dict[str, str]] = []
    pointer = heading.find_next_sibling()
    while pointer and pointer.name in {"p", "ul", "pre", "div", "ol"}:
        if pointer.name in {"ul", "ol"}:
            for item in pointer.find_all("li"):
                text = node_text(item)
                if text:
                    items.append(_structure_item_value(text))
        elif pointer.name == "div" and "row" in pointer.get("class", []):
            text = node_text(pointer)
            if text:
                items.append(_structure_item_value(text))
        else:
            text = node_text(pointer)
            if text:
                items.append(_structure_item_value(text))
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

    result: Dict[str, object] = {"character": character}

    summary = _parse_summary(soup)
    if summary:
        result["summary"] = summary

    etymologies: List[Dict[str, object]] = []
    for row in soup.select("div.row.mx-0.bg-info.row-eq-height.border-top.border-purple"):
        left = row.select_one(".col-md-3")
        right = row.select_one(".col-md-9")

        entry: Dict[str, object] = {}
        row_id = row.get("id")
        if row_id:
            entry["id"] = row_id

        metadata = _parse_left_column(left)
        if metadata:
            entry["metadata"] = metadata

        sections = _parse_right_column(right)
        if sections:
            entry["sections"] = sections

        if entry:
            etymologies.append(entry)

    if etymologies:
        result["etymologies"] = etymologies

    return result
