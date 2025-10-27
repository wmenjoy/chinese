# Hanzi MCP Scraper

This repository contains a lightweight scraper and aggregation toolkit for
collecting information about Chinese characters from three publicly available
sources:

1. **香港中文大学汉语多功能字库** (`humanum.arts.cuhk.edu.hk`)
2. **汉字源 / Chinese Etymology** (`hanziyuan.net`)
3. **CJKV 多语言字形数据库** (`ccamc.org`)

The toolkit normalises the data structures returned by each site and exposes a
single Python API (and CLI helper) that can be reused when building a Model
Context Protocol (MCP) tool.

> **Note**  
> The code only depends on `requests` and `beautifulsoup4` which means it can be
> executed in restricted environments (no headless browsers are required).  The
> Chinese Etymology site does require an anti-forgery token which is fetched and
> forwarded automatically.

## Project layout

```
hanzi_mcp/
  __init__.py
  aggregator.py          # High level helper that merges data from all sources
  cli.py                 # Simple CLI wrapper (prints JSON to stdout)
  scraper/
    __init__.py
    utils.py             # Shared helpers (HTTP session, text utilities)
    cuhk.py              # CUHK Multifunctional Character Database scraper
    hanziyuan.py         # Chinese Etymology scraper
    cjkv.py              # CJKV Multilingual Glyph Database scraper
requirements.txt
README.md
```

## Getting started

Create a virtual environment (optional) and install the requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Fetch data for a single character via the CLI helper:

```bash
python -m hanzi_mcp.cli 金
```

The command prints a JSON document containing the normalised output from all
three sources.  The CLI accepts a `--source` flag if you only want one of the
scrapers to run, e.g. `python -m hanzi_mcp.cli 金 --source cuhk`.
You can additionally persist the results by supplying `--database path/to/db.sqlite`.
To control cache freshness, pass `--cache-ttl <seconds>`; cached entries older
than the specified age will be re-fetched automatically.

Within Python the high level API looks like this:

```python
from hanzi_mcp.aggregator import collect_character_data

result = collect_character_data("金")
print(result["hanziyuan"]["summary"])
```

## Integration into an MCP tool

The module deliberately keeps the network and parsing logic isolated from any
transport layer.  You can import `collect_character_data` inside a dedicated MCP
server (for example, one built with `modelcontextprotocol`) and expose the
result to the client without duplicating the scraping logic.

The `result` dictionary returned by `collect_character_data` uses the source
identifier as the top-level key (`cuhk`, `hanziyuan`, `cjkv`).  Each scraper
returns structured data (maps, lists, and simple strings) that can be serialised
as JSON straight away.

### Persisting to SQLite

If you provide the optional `database_path` argument, the aggregated payload is
stored inside an SQLite database.  The helper keeps the schema extremely simple:
`results(character, source, fetched_at, payload)`.  Consecutive scrapes update
the stored JSON blob, allowing downstream tooling to reuse the cached data even
when the remote sites are temporarily unavailable.

## Caching / rate limits

All HTTP requests share the same `requests.Session` instance which automatically
re-uses cookies and connection pools for efficiency.  The Chinese Etymology
scraper fetches the anti-forgery tokens on demand and honours the same session
for subsequent calls, so repeated queries for different characters will only
perform the handshake once per session.

## Testing notes

The repository does not ship unit tests yet because the target sites are dynamic
and the focus of this task was on building the scraper.  The modules have been
manually validated against the character `金` and can be used as reference data
when authoring regression tests in the future.
