"""Unit tests for utility helpers and aggregator persistence."""

from pathlib import Path

from hanzi_mcp import aggregator
from hanzi_mcp.scraper.utils import assign_value, collapse_table_dict
from hanzi_mcp.storage import load_results


def test_assign_value_promotes_to_list():
    data = {"Unicode": "U+91D1"}
    assign_value(data, "Unicode", "U+91D2")
    assert data["Unicode"] == ["U+91D1", "U+91D2"]


def test_assign_value_appends_to_existing_list():
    data = {"notes": ["first"]}
    assign_value(data, "notes", "second")
    assert data["notes"] == ["first", "second"]


def test_collapse_table_dict_handles_single_and_ab_pairs():
    table = {
        "Unicode": ["U+91D1"],
        "頻序 A/B": ["280", "371"],
        "四角號碼": ["8010.9"],
        "Empty": [],
    }
    collapsed = collapse_table_dict(table)
    assert collapsed == {
        "Unicode": "U+91D1",
        "頻序": {"A": "280", "B": "371"},
        "四角號碼": "8010.9",
    }


def test_collect_character_data_can_persist_results(tmp_path: Path):
    database = tmp_path / "results.db"
    original_sources = aggregator.AVAILABLE_SOURCES.copy()
    try:
        aggregator.AVAILABLE_SOURCES = {"mock": lambda char, session=None: {"echo": char}}
        results = aggregator.collect_character_data(
            "金",
            sources=["mock"],
            database_path=str(database),
        )
    finally:
        aggregator.AVAILABLE_SOURCES = original_sources

    assert results == {"mock": {"echo": "金"}}
    stored = load_results(str(database), "金")
    assert stored == results
