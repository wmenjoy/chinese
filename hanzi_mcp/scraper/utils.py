"""Shared helper functions for the scraper modules."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    "Connection": "keep-alive",
}

WHITESPACE_RE = re.compile(r"\s+")


def create_session() -> requests.Session:
    """Return a :class:`requests.Session` with default headers."""

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.max_redirects = 5
    return session


def normalize_text(value: str) -> str:
    """Normalise whitespace and strip control characters."""

    return WHITESPACE_RE.sub(" ", value.replace("\xa0", " ").strip())


def node_text(node: Optional[Tag | NavigableString]) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, NavigableString):
        return normalize_text(str(node)) or None
    return normalize_text(node.get_text(" ")) or None


def iter_table_rows(table: Tag) -> Iterator[Tuple[str, List[str]]]:
    """Yield ``(header, cells)`` pairs for the rows inside *table*."""

    for row in table.find_all("tr"):
        headers = [node_text(th) for th in row.find_all("th")]
        data = [node_text(td) for td in row.find_all("td")]
        label = next((value for value in headers if value), None)
        if label is None:
            continue
        yield label, [value for value in data if value]


def table_to_dict(table: Tag) -> Dict[str, List[str]]:
    return {label: values for label, values in iter_table_rows(table)}


def options_to_links(select: Tag) -> List[Dict[str, str]]:
    links = []
    for option in select.find_all("option"):
        value = option.get("value")
        text = node_text(option)
        if not value or not text or text.startswith("\""):
            continue
        links.append({"title": text, "url": value})
    return links


def safe_find(soup: BeautifulSoup, selector: str) -> Optional[Tag]:
    return soup.select_one(selector)


def assign_value(mapping: Dict[str, object], key: str, value: object) -> None:
    """Assign a value to *mapping* keeping duplicate keys as lists."""

    if key in mapping:
        current = mapping[key]
        if isinstance(current, list):
            current.append(value)
        else:
            mapping[key] = [current, value]
    else:
        mapping[key] = value


def collapse_table_dict(table_map: Dict[str, List[str]]) -> Dict[str, object]:
    """Collapse list based table data into friendlier scalars."""

    collapsed: Dict[str, object] = {}
    for label, values in table_map.items():
        if not values:
            continue
        cleaned = [value for value in values if value]
        if not cleaned:
            continue
        if label.endswith("A/B") and len(cleaned) == 2:
            assign_value(
                collapsed,
                label[:-3].strip(),
                {"A": cleaned[0], "B": cleaned[1]},
            )
        elif len(cleaned) == 1:
            assign_value(collapsed, label, cleaned[0])
        else:
            assign_value(collapsed, label, cleaned)
    return collapsed
