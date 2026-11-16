"""Durable review decisions: local SQLite or configured PostgreSQL."""

import os
import sqlite3
from contextlib import contextmanager

from src.backend.data import PROCESSED


@contextmanager
def connection():
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        import psycopg
        with psycopg.connect(url, connect_timeout=10) as conn:
            yield conn, "%s"
    else:
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise RuntimeError("DATABASE_URL is required in production")
        PROCESSED.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(PROCESSED / "reviews.sqlite3")
        try:
            with conn:
                yield conn, "?"
        finally:
            conn.close()


def prepare(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS anomaly_reviews (account_id TEXT PRIMARY KEY, decision TEXT NOT NULL, note TEXT NOT NULL, updated_at TEXT NOT NULL)")


def list_reviews():
    with connection() as (conn, _):
        prepare(conn)
        return {row[0]: {"decision": row[1], "note": row[2], "updated_at": row[3]}
                for row in conn.execute("SELECT account_id, decision, note, updated_at FROM anomaly_reviews").fetchall()}


def save_review(account_id, decision, note, updated_at):
    with connection() as (conn, marker):
        prepare(conn)
        params = ", ".join([marker] * 4)
        conn.execute(f"INSERT INTO anomaly_reviews (account_id, decision, note, updated_at) VALUES ({params}) "
                     "ON CONFLICT (account_id) DO UPDATE SET decision=excluded.decision, note=excluded.note, updated_at=excluded.updated_at",
                     (account_id, decision, note, updated_at))
