"""Tests for scraper parsing helpers using lightweight HTML fixtures."""

from bs4 import BeautifulSoup

from hanzi_mcp.scraper import cuhk, hanziyuan


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def test_cuhk_parse_basic_sections_and_statistics():
    html = """
    <div>
      <div class="char_info2_col">
        <table class="char_info_table">
          <tr><th>Unicode</th><td>U+91D1</td></tr>
          <tr><th>UTF-8</th><td>E9 87 91</td></tr>
        </table>
      </div>
      <div class="char_info2_col">
        <table class="char_info_table">
          <tr><th>頻序 A/B</th><td>280</td><td>371</td></tr>
          <tr><th>四角號碼</th><td>8010.9</td></tr>
        </table>
      </div>
    </div>
    """
    soup = make_soup(html)
    identifiers, statistics = cuhk._parse_basic_sections(soup)
    assert identifiers == {"Unicode": "U+91D1", "UTF-8": "E9 87 91"}
    assert statistics == {
        "頻序": {"A": "280", "B": "371"},
        "四角號碼": "8010.9",
    }


def test_cuhk_parse_cantonese_table_merges_duplicate_headers():
    html = """
    <table id="char_can_table">
      <tr><th>讀音</th><th>詞例(解釋)</th></tr>
      <tr><td>gam1</td><td>金錢</td></tr>
      <tr><td>gaam3</td><td>黄金</td></tr>
    </table>
    """
    soup = make_soup(html)
    entries = cuhk._parse_cantonese_table(soup)
    assert entries == [
        {"讀音": "gam1", "詞例(解釋)": "金錢"},
        {"讀音": "gaam3", "詞例(解釋)": "黄金"},
    ]


def test_hanziyuan_structure_item_value_extracts_identifiers():
    assert hanziyuan._structure_item_value("B19065 Ancient coin") == {
        "id": "B19065",
        "text": "Ancient coin",
    }
    # When the remainder is identical to the identifier we do not duplicate the text.
    assert hanziyuan._structure_item_value("B19065 B19065") == {"id": "B19065"}


def test_hanziyuan_parse_summary_extracts_counts_and_badges():
    html = """
    <div class="etymology-alert">
        <strong>金</strong>
        Found 2 etymologies and 5 characters in 0.123 seconds.
        <span class="label">B19065 Ancient</span>
        <span class="label">S10415 Seal</span>
    </div>
    """
    soup = make_soup(html)
    summary = hanziyuan._parse_summary(soup)
    assert summary["character"] == "金"
    assert summary["counts"] == {"etymologies": 2, "characters": 5}
    assert summary["elapsed_seconds"] == 0.123
    assert summary["identifiers"] == [
        {"id": "B19065", "text": "Ancient"},
        {"id": "S10415", "text": "Seal"},
    ]


def test_hanziyuan_parse_left_column_splits_labels_and_notes():
    html = """
    <div>
      <p><b>Traditional:</b> 金</p>
      <p><b>Simplified:</b> 金</p>
      <p>Common surname</p>
    </div>
    """
    soup = make_soup(html)
    metadata = hanziyuan._parse_left_column(soup.div)
    assert metadata["Traditional"] == "金"
    assert metadata["Simplified"] == "金"
    assert metadata["notes"] == ["Common surname"]


def test_hanziyuan_collect_section_content_normalises_items():
    html = """
    <div>
      <h3>Bronze characters</h3>
      <ul>
        <li>B19065 Ancient</li>
        <li>B19066 Another</li>
      </ul>
    </div>
    """
    soup = make_soup(html)
    heading = soup.find("h3")
    section = hanziyuan._collect_section_content(heading)
    assert section == {
        "title": "Bronze characters",
        "items": [
            {"id": "B19065", "text": "Ancient"},
            {"id": "B19066", "text": "Another"},
        ],
    }
