"""Tests for SQLite storage helpers."""

import json
from pathlib import Path

from hanzi_mcp.storage import load_results, store_results


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
