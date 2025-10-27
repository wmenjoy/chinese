"""Aggregate character data from multiple online sources."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from .scraper import cjkv, cuhk, hanziyuan
from .scraper.utils import create_session


AVAILABLE_SOURCES = {
    "cuhk": cuhk.fetch_cuhk_data,
    "hanziyuan": hanziyuan.fetch_hanziyuan_data,
    "cjkv": cjkv.fetch_cjkv_data,
}


def collect_character_data(
    character: str,
    *,
    sources: Optional[Iterable[str]] = None,
    session=None,
) -> Dict[str, Dict[str, object]]:
    """Collect data for *character* from the requested *sources*.

    Parameters
    ----------
    character:
        Single Chinese character to query.
    sources:
        Optional iterable containing a subset of ``{"cuhk", "hanziyuan", "cjkv"}``.
        If omitted all sources are queried.
    session:
        Optional :class:`requests.Session` (or session-like object) which will be
        re-used by all scrapers.  When omitted a new session with sensible
        defaults is created.
    """

    if not character or len(character) != 1:
        raise ValueError("Character must be a single Unicode code point.")

    if session is None:
        session = create_session()

    requested_sources = list(sources) if sources is not None else list(AVAILABLE_SOURCES)
    invalid = [source for source in requested_sources if source not in AVAILABLE_SOURCES]
    if invalid:
        raise ValueError(f"Unknown sources requested: {', '.join(sorted(invalid))}")

    results: Dict[str, Dict[str, object]] = {}
    for source in requested_sources:
        fetcher = AVAILABLE_SOURCES[source]
        try:
            results[source] = fetcher(character, session=session)
        except Exception as exc:  # pragma: no cover - defensive
            results[source] = {"error": str(exc)}
    return results
