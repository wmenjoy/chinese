"""Scraper for the CUHK Chinese Multi-functional Character Database."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from .utils import (
    assign_value,
    collapse_table_dict,
    create_session,
    node_text,
    options_to_links,
    table_to_dict,
)

BASE_URL = "https://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php"


def _parse_basic_sections(soup: BeautifulSoup) -> Tuple[Dict[str, object], Dict[str, object]]:
    identifiers: Dict[str, object] = {}
    statistics: Dict[str, object] = {}
    tables = soup.select(".char_info2_col .char_info_table")
    if tables:
        identifiers = collapse_table_dict(table_to_dict(tables[0]))
        if len(tables) > 1:
            statistics = collapse_table_dict(table_to_dict(tables[1]))
    return identifiers, statistics


def _parse_forms(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    forms_cell = soup.select_one("#char_form_type")
    if not forms_cell:
        return {}
    items = [span for span in forms_cell.find_all("span") if span.get("class")]
    result: Dict[str, Optional[str]] = {}
    mapping = {
        "form_tc": "traditional",
        "form_sc": "simplified",
        "form_hk": "hong_kong",
        "not_form_tc": "traditional",
        "not_form_sc": "simplified",
        "not_form_hk": "hong_kong",
    }
    for span in items:
        classes = span.get("class", [])
        label = mapping.get(classes[0]) if classes else None
        if not label:
            continue
        text = node_text(span)
        if label in result and result[label]:
            continue
        result[label] = text
    return result


def _parse_shuowen(soup: BeautifulSoup) -> Dict[str, str]:
    table = soup.find("table", id="shuoWenTable")
    if not table:
        return {}
    data = {}
    for label, values in table_to_dict(table).items():
        if values:
            data[label] = " ".join(values)
    return data


def _parse_cantonese_table(soup: BeautifulSoup) -> List[Dict[str, object]]:
    table = soup.find("table", id="char_can_table")
    if not table:
        return []
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []
    headers = [node_text(th) or "" for th in rows[0].find_all("th")]
    entries: List[Dict[str, object]] = []
    for row in rows[1:]:
        cells = [node_text(td) or "" for td in row.find_all("td")]
        if not any(cells):
            continue
        entry: Dict[str, object] = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            value = cells[idx] if idx < len(cells) else ""
            if not value:
                continue
            assign_value(entry, header, value)
        if entry:
            entries.append(entry)
    return entries


def _parse_english_gloss(soup: BeautifulSoup) -> Dict[str, object]:
    table = soup.find("table", id="char_eng_table")
    if not table:
        return {}
    return collapse_table_dict(table_to_dict(table))


def _parse_dictionary_links(soup: BeautifulSoup) -> List[Dict[str, str]]:
    select = soup.find("select", id="usefullinks")
    if not select:
        return []
    return options_to_links(select)


def _parse_misc_sections(soup: BeautifulSoup) -> Dict[str, object]:
    data: Dict[str, object] = {}

    dialect_table = soup.find("table", id="dialectTable")
    if dialect_table:
        dialect_values = collapse_table_dict(table_to_dict(dialect_table))
        if dialect_values:
            data["dialect_notes"] = dialect_values

    related_table = soup.find("table", id="char_rel_table")
    if related_table:
        related_entries = []
        for label, values in table_to_dict(related_table).items():
            if not values:
                continue
            related_entries.append({"label": label, "values": values})
        if related_entries:
            data["related_characters"] = related_entries

    admin = soup.find("table", id="char_admin_table")
    if admin:
        admin_text = " ".join(
            filter(None, (node_text(cell) for cell in admin.find_all("td")))
        )
        if admin_text:
            data["administrative_notes"] = admin_text

    return data


def fetch_cuhk_data(character: str, *, session=None) -> Dict[str, object]:
    """Fetch and parse data from the CUHK multi-functional character database."""

    if session is None:
        session = create_session()

    response = session.get(BASE_URL, params={"word": character}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    head_char = node_text(soup.select_one("#char_headchar"))

    identifiers, statistics = _parse_basic_sections(soup)

    result: Dict[str, object] = {
        "character": head_char or character,
        "title": node_text(soup.title),
    }

    links = _parse_dictionary_links(soup)
    if links:
        result["external_links"] = links

    forms = _parse_forms(soup)
    if forms:
        result["forms"] = forms

    if identifiers:
        result["identifiers"] = identifiers
    if statistics:
        result["statistics"] = statistics

    shuowen = _parse_shuowen(soup)
    if shuowen:
        result["shuowen"] = shuowen

    cantonese = _parse_cantonese_table(soup)
    if cantonese:
        result["cantonese_readings"] = cantonese

    english = _parse_english_gloss(soup)
    if english:
        result["english_definitions"] = english

    misc = _parse_misc_sections(soup)
    if misc:
        result.update(misc)

    return result
