"""Unit tests for utility helpers."""

from hanzi_mcp.scraper.utils import assign_value, collapse_table_dict


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
