from __future__ import annotations

import datetime as dt
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import aiosqlite

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    is_blocked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    button_text TEXT,
    button_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    total INTEGER NOT NULL DEFAULT 0,
    sent INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    media_kind TEXT NOT NULL DEFAULT 'none',
    excluded_count INTEGER NOT NULL DEFAULT 0
);
"""

# (таблица, колонка, объявление типа) — добавляются в уже существующие БД,
# т.к. CREATE TABLE IF NOT EXISTS их не тронет.
_MIGRATIONS = (
    ("broadcasts", "media_kind", "TEXT NOT NULL DEFAULT 'none'"),
    ("broadcasts", "excluded_count", "INTEGER NOT NULL DEFAULT 0"),
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


@asynccontextmanager
async def _connect() -> AsyncIterator[aiosqlite.Connection]:
    db_conn = await aiosqlite.connect(config.DB_PATH)
    try:
        await db_conn.execute("PRAGMA busy_timeout=5000")
        yield db_conn
    finally:
        await db_conn.close()


async def _run_migrations(conn: aiosqlite.Connection) -> None:
    for table, column, decl in _MIGRATIONS:
        async with conn.execute(f"PRAGMA table_info({table})") as cursor:
            existing = {row[1] async for row in cursor}
        if column not in existing:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


async def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with _connect() as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.executescript(_SCHEMA)
        await _run_migrations(conn)
        await conn.commit()


async def upsert_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> None:
    now = _now()
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, first_seen, last_seen, is_blocked)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                last_seen=excluded.last_seen,
                is_blocked=0
            """,
            (telegram_id, username, first_name, last_name, now, now),
        )
        await conn.commit()


async def mark_blocked(telegram_id: int) -> None:
    async with _connect() as conn:
        await conn.execute(
            "UPDATE users SET is_blocked = 1 WHERE telegram_id = ?", (telegram_id,)
        )
        await conn.commit()


async def count_users(include_blocked: bool = False) -> int:
    query = "SELECT COUNT(*) FROM users"
    if not include_blocked:
        query += " WHERE is_blocked = 0"
    async with _connect() as conn:
        async with conn.execute(query) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_active_user_ids(exclude_ids: set[int] | None = None) -> list[int]:
    async with _connect() as conn:
        async with conn.execute(
            "SELECT telegram_id FROM users WHERE is_blocked = 0"
        ) as cursor:
            rows = await cursor.fetchall()
    ids = [r[0] for r in rows]
    if exclude_ids:
        ids = [tid for tid in ids if tid not in exclude_ids]
    return ids


async def list_users(limit: int = 1000) -> list[dict[str, Any]]:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            """
            SELECT telegram_id, username, first_name, last_name, last_seen
            FROM users
            WHERE is_blocked = 0
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def create_broadcast(
    admin_id: int,
    text: str,
    button_text: str | None,
    button_url: str | None,
    total: int,
    media_kind: str = "none",
    excluded_count: int = 0,
) -> int:
    async with _connect() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO broadcasts
                (admin_id, text, button_text, button_url, status, total, created_at, media_kind, excluded_count)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """,
            (admin_id, text, button_text, button_url, total, _now(), media_kind, excluded_count),
        )
        await conn.commit()
        return cursor.lastrowid


async def update_broadcast_progress(
    broadcast_id: int,
    sent: int,
    failed: int,
    status: str | None = None,
) -> None:
    async with _connect() as conn:
        if status:
            finished_at = _now() if status in ("done", "failed") else None
            await conn.execute(
                "UPDATE broadcasts SET sent = ?, failed = ?, status = ?, finished_at = ? WHERE id = ?",
                (sent, failed, status, finished_at, broadcast_id),
            )
        else:
            await conn.execute(
                "UPDATE broadcasts SET sent = ?, failed = ? WHERE id = ?",
                (sent, failed, broadcast_id),
            )
        await conn.commit()


async def get_broadcast(broadcast_id: int) -> dict[str, Any] | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_broadcasts(limit: int = 20) -> list[dict[str, Any]]:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM broadcasts ORDER BY id DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
