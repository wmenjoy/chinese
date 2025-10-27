"""Tests for SQLite storage helpers."""

from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

from hanzi_mcp.storage import load_cached_results, load_results, store_results


def test_store_and_load_results(tmp_path: Path):
    database = tmp_path / "results.db"
    payload = {
        "cuhk": {"character": "金", "identifiers": {"Unicode": "U+91D1"}},
        "hanziyuan": {"summary": {"text": "dummy"}},
    }

    store_results(str(database), "金", payload)

    loaded = load_results(str(database), "金")
    assert loaded == payload

    # Ensure filtering by source works and data is JSON parsed.
    hanziyuan_only = load_results(str(database), "金", source="hanziyuan")
    assert hanziyuan_only == {"hanziyuan": {"summary": {"text": "dummy"}}}


def test_load_cached_results_respects_ttl(tmp_path: Path):
    database = tmp_path / "results.db"
    payload = {"cuhk": {"dummy": True}}
    store_results(str(database), "金", payload)

    # Artificially age the record beyond the TTL threshold.
    with sqlite3.connect(str(database)) as conn:
        past = (datetime.utcnow() - timedelta(seconds=3600)).isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE results
            SET fetched_at = ?
            WHERE character_id = (SELECT id FROM characters WHERE char = ?)
              AND source_id = (SELECT id FROM sources WHERE name = ?)
            """,
            (past, "金", "cuhk"),
        )
        conn.commit()

    cached, missing = load_cached_results(str(database), "金", ["cuhk"], max_age_seconds=10)
    assert cached == {}
    assert missing == ["cuhk"]
