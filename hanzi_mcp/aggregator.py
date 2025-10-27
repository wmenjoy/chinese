"""Aggregate character data from multiple online sources."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from .scraper import cjkv, cuhk, hanziyuan
from .scraper.utils import create_session
from .storage import load_cached_results, store_results


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
    database_path: Optional[str] = None,
    cache_ttl_seconds: Optional[int] = None,
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
    database_path:
        Optional path to an SQLite database. When supplied, the collected
        results are persisted via :func:`hanzi_mcp.storage.store_results`.
    cache_ttl_seconds:
        Optional time-to-live (in seconds) for cached entries. When specified, a
        cached result older than this value is considered stale and will be
        refreshed from the remote source.
    """

    if not character or len(character) != 1:
        raise ValueError("Character must be a single Unicode code point.")

    if session is None:
        session = create_session()

    requested_sources = list(sources) if sources is not None else list(AVAILABLE_SOURCES)
    requested_sources = list(dict.fromkeys(requested_sources))
    invalid = [source for source in requested_sources if source not in AVAILABLE_SOURCES]
    if invalid:
        raise ValueError(f"Unknown sources requested: {', '.join(sorted(invalid))}")

    results: Dict[str, Dict[str, object]] = {}
    missing_sources = requested_sources

    if database_path:
        cached, missing = load_cached_results(
            database_path,
            character,
            requested_sources,
            max_age_seconds=cache_ttl_seconds,
        )
        results.update(cached)
        missing_sources = missing

    for source in missing_sources:
        fetcher = AVAILABLE_SOURCES[source]
        try:
            results[source] = fetcher(character, session=session)
        except Exception as exc:  # pragma: no cover - defensive
            results[source] = {"error": str(exc)}

    if database_path and missing_sources:
        store_results(
            database_path,
            character,
            {source: results[source] for source in missing_sources},
        )

    return results
