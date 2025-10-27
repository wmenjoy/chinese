"""Command line helper for the Hanzi MCP scraper."""

from __future__ import annotations

import argparse
import json
import sys

from .aggregator import collect_character_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Chinese character info from multiple sources.")
    parser.add_argument("character", help="Single Chinese character to query.")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        choices=["cuhk", "hanziyuan", "cjkv"],
        help="Restrict the lookup to one or more sources (can be supplied multiple times).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation (defaults to 2). Use 0 for compact output.",
    )
    parser.add_argument(
        "--database",
        dest="database_path",
        help="Optional path to an SQLite database used to store the collected results.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = collect_character_data(
            args.character,
            sources=args.sources,
            database_path=args.database_path,
        )
    except Exception as exc:  # pragma: no cover - CLI convenience
        parser.error(str(exc))
        return 1

    indent = None if args.indent <= 0 else args.indent
    json.dump(data, sys.stdout, ensure_ascii=False, indent=indent)
    if indent is not None:
        sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
