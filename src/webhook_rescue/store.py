from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from webhook_rescue.utils import ensure_parent


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    failure_reason TEXT,
    replay_result TEXT,
    created_at TEXT NOT NULL,
    replayed_at TEXT,
    duplicate_of_event_id TEXT,
    credit_delta INTEGER NOT NULL DEFAULT 0,
    suggested_fix TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL UNIQUE,
    credits INTEGER NOT NULL DEFAULT 0,
    subscription_status_local TEXT,
    subscription_status_provider TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_event_id ON events(event_id);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
"""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    ensure_parent(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def reset_db(db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    init_db(db_path)


def insert_event(
    conn: sqlite3.Connection,
    *,
    provider: str,
    event_id: str,
    event_type: str,
    status: str,
    payload: dict[str, Any],
    failure_reason: str | None = None,
    replay_result: str | None = None,
    duplicate_of_event_id: str | None = None,
    credit_delta: int = 0,
    suggested_fix: str | None = None,
) -> sqlite3.Row:
    conn.execute(
        """
        INSERT INTO events (
            provider, event_id, event_type, status, payload_json, failure_reason,
            replay_result, created_at, duplicate_of_event_id, credit_delta, suggested_fix
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            provider,
            event_id,
            event_type,
            status,
            json.dumps(payload, sort_keys=True),
            failure_reason,
            replay_result,
            utc_now(),
            duplicate_of_event_id,
            credit_delta,
            suggested_fix,
        ),
    )
    return get_latest_event(conn, event_id)


def get_latest_event(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM events WHERE event_id = ? ORDER BY id DESC LIMIT 1",
        (event_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"event not found: {event_id}")
    return row


def decode_payload(row: sqlite3.Row) -> dict[str, Any]:
    return json.loads(row["payload_json"])


def find_first_non_duplicate(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT * FROM events
        WHERE event_id = ? AND status NOT IN ('duplicate', 'duplicate_object')
        ORDER BY id ASC
        LIMIT 1
        """,
        (event_id,),
    ).fetchone()


def upsert_account(
    conn: sqlite3.Connection,
    *,
    customer_id: str,
    credit_delta: int = 0,
    subscription_status_local: str | None = None,
    subscription_status_provider: str | None = None,
) -> sqlite3.Row:
    conn.execute(
        """
        INSERT INTO accounts (
            customer_id, credits, subscription_status_local, subscription_status_provider
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(customer_id) DO UPDATE SET
            credits = accounts.credits + excluded.credits,
            subscription_status_local = COALESCE(excluded.subscription_status_local, accounts.subscription_status_local),
            subscription_status_provider = COALESCE(excluded.subscription_status_provider, accounts.subscription_status_provider)
        """,
        (
            customer_id,
            credit_delta,
            subscription_status_local,
            subscription_status_provider,
        ),
    )
    row = conn.execute(
        "SELECT * FROM accounts WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"account upsert failed: {customer_id}")
    return row


def get_account(conn: sqlite3.Connection, customer_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM accounts WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()


def list_events(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM events ORDER BY id ASC").fetchall()


def list_accounts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM accounts ORDER BY id ASC").fetchall()
