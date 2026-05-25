from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite

from bot.config import DB_PATH

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    user_id INTEGER PRIMARY KEY,
    state_json TEXT NOT NULL,
    prev_state_json TEXT,
    comparisons_done INTEGER NOT NULL DEFAULT 0,
    estimated_total INTEGER NOT NULL DEFAULT 119,
    is_finished INTEGER NOT NULL DEFAULT 0,
    result_json TEXT,
    updated_at TEXT NOT NULL
);
"""


@dataclass(slots=True)
class Session:
    user_id: int
    state_json: str
    prev_state_json: str | None
    comparisons_done: int
    estimated_total: int
    is_finished: bool
    result_json: str | None


def _row_to_session(row: aiosqlite.Row) -> Session:
    return Session(
        user_id=row["user_id"],
        state_json=row["state_json"],
        prev_state_json=row["prev_state_json"],
        comparisons_done=row["comparisons_done"],
        estimated_total=row["estimated_total"],
        is_finished=bool(row["is_finished"]),
        result_json=row["result_json"],
    )


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def load_session(user_id: int) -> Session | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_session(row)


async def save_session(
    user_id: int,
    *,
    state_json: str,
    prev_state_json: str | None,
    comparisons_done: int,
    estimated_total: int,
    is_finished: bool = False,
    result_json: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO sessions (
                user_id,
                state_json,
                prev_state_json,
                comparisons_done,
                estimated_total,
                is_finished,
                result_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state_json = excluded.state_json,
                prev_state_json = excluded.prev_state_json,
                comparisons_done = excluded.comparisons_done,
                estimated_total = excluded.estimated_total,
                is_finished = excluded.is_finished,
                result_json = excluded.result_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                state_json,
                prev_state_json,
                comparisons_done,
                estimated_total,
                int(is_finished),
                result_json,
                now,
            ),
        )
        await db.commit()


async def finish_session(
    user_id: int,
    ranking: list[int],
    state_json: str,
    *,
    comparisons_done: int,
    estimated_total: int,
) -> None:
    await save_session(
        user_id,
        state_json=state_json,
        prev_state_json=None,
        comparisons_done=comparisons_done,
        estimated_total=estimated_total,
        is_finished=True,
        result_json=json.dumps(ranking, ensure_ascii=False),
    )


async def delete_session(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        await db.commit()


async def undo_session(user_id: int) -> Session | None:
    session = await load_session(user_id)
    if session is None or session.is_finished or not session.prev_state_json:
        return session

    now = datetime.now(timezone.utc).isoformat()
    comparisons_done = max(session.comparisons_done - 1, 0)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE sessions
            SET state_json = ?,
                prev_state_json = NULL,
                comparisons_done = ?,
                is_finished = 0,
                result_json = NULL,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                session.prev_state_json,
                comparisons_done,
                now,
                user_id,
            ),
        )
        await db.commit()

    return await load_session(user_id)
