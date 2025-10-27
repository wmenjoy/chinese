"""SQLite persistence helpers for scraper results."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import os
import sqlite3
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    char TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS results (
    character_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (character_id, source_id),
    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_results_character_source ON results(character_id, source_id);
"""


@contextmanager
def _connect(database_path: str, *, write: bool) -> Iterator[sqlite3.Connection]:
    if database_path == ":memory:":
        if not write:
            raise FileNotFoundError("In-memory databases cannot be used for caching without write access.")
        conn = sqlite3.connect(database_path)
    else:
        abs_path = os.path.abspath(database_path)
        directory = os.path.dirname(abs_path)
        if write and directory:
            os.makedirs(directory, exist_ok=True)
        if not write and not os.path.exists(abs_path):
            raise FileNotFoundError(abs_path)
        if write:
            conn = sqlite3.connect(abs_path)
        else:
            conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        if write:
            conn.executescript(SCHEMA)
            conn.execute("PRAGMA journal_mode=WAL;")
        yield conn
        if write:
            conn.commit()
    finally:
        conn.close()


def _get_character_id(conn: sqlite3.Connection, character: str, *, create: bool) -> Optional[int]:
    row = conn.execute("SELECT id FROM characters WHERE char = ?", (character,)).fetchone()
    if row:
        return row[0]
    if not create:
        return None
    conn.execute("INSERT INTO characters(char) VALUES (?)", (character,))
    return conn.execute("SELECT id FROM characters WHERE char = ?", (character,)).fetchone()[0]


def _get_source_id(conn: sqlite3.Connection, source: str, *, create: bool) -> Optional[int]:
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (source,)).fetchone()
    if row:
        return row[0]
    if not create:
        return None
    conn.execute("INSERT INTO sources(name) VALUES (?)", (source,))
    return conn.execute("SELECT id FROM sources WHERE name = ?", (source,)).fetchone()[0]


def store_results(database_path: str, character: str, results: Dict[str, Dict[str, object]]) -> None:
    """Persist scraper *results* for *character* into *database_path*."""

    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    with _connect(database_path, write=True) as conn:
        character_id = _get_character_id(conn, character, create=True)
        for source, payload in results.items():
            source_id = _get_source_id(conn, source, create=True)
            conn.execute(
                """
                INSERT INTO results(character_id, source_id, fetched_at, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(character_id, source_id) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    payload = excluded.payload
                """,
                (character_id, source_id, timestamp, json.dumps(payload, ensure_ascii=False)),
            )


def load_results(database_path: str, character: str, source: Optional[str] = None) -> Dict[str, Dict[str, object]]:
    """Load previously stored results for *character* (optionally filtered by *source*)."""

    cached, _missing = load_cached_results(database_path, character, [source] if source else None)
    if source:
        return {source: cached[source]} if source in cached else {}
    return cached


def load_cached_results(
    database_path: str,
    character: str,
    sources: Optional[Iterable[str]] = None,
    max_age_seconds: Optional[int] = None,
) -> Tuple[Dict[str, Dict[str, object]], List[str]]:
    """Return cached payloads and the list of *sources* that still need fetching."""

    requested = list(sources) if sources is not None else None
    if database_path == ":memory:":
        return {}, requested or []
    try:
        with _connect(database_path, write=False) as conn:
            character_id = _get_character_id(conn, character, create=False)
            if character_id is None:
                return {}, requested or []
            params: List[object] = [character_id]
            query = (
                "SELECT s.name, r.payload, r.fetched_at "
                "FROM results r JOIN sources s ON s.id = r.source_id "
                "WHERE r.character_id = ?"
            )
            if requested:
                placeholders = ",".join("?" for _ in requested)
                query += f" AND s.name IN ({placeholders})"
                params.extend(requested)
            rows = conn.execute(query, params).fetchall()
    except FileNotFoundError:
        return {}, requested or []

    cached: Dict[str, Dict[str, object]] = {}
    missing: List[str] = list(requested) if requested else []
    now = datetime.utcnow()
    for name, payload_text, fetched_at in rows:
        payload = json.loads(payload_text)
        is_stale = False
        if max_age_seconds is not None and fetched_at:
            fetched_dt = datetime.fromisoformat(fetched_at)
            if (now - fetched_dt) > timedelta(seconds=max_age_seconds):
                is_stale = True
        if requested is not None and name not in requested:
            continue
        if is_stale:
            continue
        cached[name] = payload
        if requested and name in missing:
            missing.remove(name)

    if requested is None:
        missing = []
    else:
        # Ensure missing contains any requested sources we did not encounter at all.
        for name in requested:
            if name not in cached and name not in missing:
                missing.append(name)

    return cached, missing
