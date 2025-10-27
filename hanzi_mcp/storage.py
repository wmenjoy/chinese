"""SQLite persistence helpers for scraper results."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import os
import sqlite3
from typing import Dict, Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    character TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (character, source)
);
"""


@contextmanager
def _connect(database_path: str) -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)
    conn = sqlite3.connect(database_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def store_results(database_path: str, character: str, results: Dict[str, Dict[str, object]]) -> None:
    """Persist scraper *results* for *character* into *database_path*."""

    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    with _connect(database_path) as conn:
        for source, payload in results.items():
            conn.execute(
                """
                INSERT INTO results(character, source, fetched_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(character, source) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    payload = excluded.payload
                """,
                (character, source, timestamp, json.dumps(payload, ensure_ascii=False)),
            )


def load_results(database_path: str, character: str, source: Optional[str] = None) -> Dict[str, Dict[str, object]]:
    """Load previously stored results for *character* (optionally filtered by *source*)."""

    query = "SELECT source, payload FROM results WHERE character = ?"
    params = [character]
    if source is not None:
        query += " AND source = ?"
        params.append(source)

    with _connect(database_path) as conn:
        rows = conn.execute(query, params).fetchall()

    return {row[0]: json.loads(row[1]) for row in rows}
