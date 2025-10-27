"""Scraper for the CUHK Chinese Multi-functional Character Database."""

from __future__ import annotations

from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from .utils import (
    create_session,
    node_text,
    options_to_links,
    table_to_dict,
)

BASE_URL = "https://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php"


def _parse_basic_tables(soup: BeautifulSoup) -> Dict[str, Dict[str, List[str]]]:
    sections: Dict[str, Dict[str, List[str]]] = {}
    columns = soup.select(".char_info2_col .char_info_table")
    labels = ("codes", "usage")
    for label, table in zip(labels, columns):
        sections[label] = table_to_dict(table)
    return sections


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


def _parse_cantonese_table(soup: BeautifulSoup) -> List[Dict[str, str]]:
    table = soup.find("table", id="char_can_table")
    if not table:
        return []
    rows = table.find_all("tr")
    if not rows:
        return []
    headers = [node_text(th) or "" for th in rows[0].find_all("th")]
    entries: List[Dict[str, str]] = []
    for row in rows[1:]:
        cells = [node_text(td) or "" for td in row.find_all("td")]
        if not any(cells):
            continue
        entry = {headers[idx]: value for idx, value in enumerate(cells) if headers[idx]}
        entries.append(entry)
    return entries


def _parse_english_gloss(soup: BeautifulSoup) -> Dict[str, str]:
    table = soup.find("table", id="char_eng_table")
    if not table:
        return {}
    return {label: " ".join(values) for label, values in table_to_dict(table).items()}


def _parse_dictionary_links(soup: BeautifulSoup) -> List[Dict[str, str]]:
    select = soup.find("select", id="usefullinks")
    if not select:
        return []
    return options_to_links(select)


def _parse_misc_sections(soup: BeautifulSoup) -> Dict[str, object]:
    data: Dict[str, object] = {}
    sections = {
        "dialects": soup.find("table", id="dialectTable"),
        "related": soup.find("table", id="char_rel_table"),
    }
    for key, table in sections.items():
        if not table:
            continue
        values = {
            label: " ".join(entries)
            for label, entries in table_to_dict(table).items()
            if entries
        }
        if values:
            data[key] = values
    admin = soup.find("table", id="char_admin_table")
    if admin:
        admin_text = " ".join(
            filter(None, (node_text(cell) for cell in admin.find_all("td")))
        )
        if admin_text:
            data["admin"] = admin_text
    return data


def fetch_cuhk_data(character: str, *, session=None) -> Dict[str, object]:
    """Fetch and parse data from the CUHK multi-functional character database."""

    if session is None:
        session = create_session()

    response = session.get(BASE_URL, params={"word": character}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    head_char = node_text(soup.select_one("#char_headchar"))

    result: Dict[str, object] = {
        "character": head_char or character,
        "title": node_text(soup.title),
        "links": _parse_dictionary_links(soup),
        "forms": _parse_forms(soup),
    }

    result["sections"] = {
        "basic": _parse_basic_tables(soup),
        "shuowen": _parse_shuowen(soup),
        "cantonese": _parse_cantonese_table(soup),
        "english": _parse_english_gloss(soup),
    }
    misc = _parse_misc_sections(soup)
    if misc:
        result["sections"].update(misc)

    return result
