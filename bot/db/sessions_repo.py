from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    user_id INTEGER PRIMARY KEY,
    state_json TEXT NOT NULL,
    prev_state_json TEXT,
    comparisons_done INTEGER NOT NULL DEFAULT 0,
    estimated_total INTEGER NOT NULL DEFAULT 119,
    is_finished INTEGER NOT NULL DEFAULT 0,
    result_json TEXT,
    last_question_chat_id INTEGER,
    last_question_message_id INTEGER,
    updated_at TEXT NOT NULL
);
"""

MIGRATIONS = (
    "ALTER TABLE sessions ADD COLUMN last_question_chat_id INTEGER",
    "ALTER TABLE sessions ADD COLUMN last_question_message_id INTEGER",
)


@dataclass(slots=True)
class Session:
    user_id: int
    state_json: str
    prev_state_json: str | None
    comparisons_done: int
    estimated_total: int
    is_finished: bool
    result_json: str | None
    last_question_chat_id: int | None
    last_question_message_id: int | None


def _row_to_session(row: aiosqlite.Row) -> Session:
    return Session(
        user_id=row["user_id"],
        state_json=row["state_json"],
        prev_state_json=row["prev_state_json"],
        comparisons_done=row["comparisons_done"],
        estimated_total=row["estimated_total"],
        is_finished=bool(row["is_finished"]),
        result_json=row["result_json"],
        last_question_chat_id=row["last_question_chat_id"],
        last_question_message_id=row["last_question_message_id"],
    )


class SessionsRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(CREATE_TABLE_SQL)
            for migration in MIGRATIONS:
                with suppress(aiosqlite.OperationalError):
                    await db.execute(migration)
            await db.commit()

    async def close(self) -> None:
        return None

    async def load(self, user_id: int) -> Session | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_session(row)

    async def save(
        self,
        user_id: int,
        *,
        state_json: str,
        prev_state_json: str | None,
        comparisons_done: int,
        estimated_total: int,
        is_finished: bool = False,
        result_json: str | None = None,
        last_question_chat_id: int | None = None,
        last_question_message_id: int | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
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
                    last_question_chat_id,
                    last_question_message_id,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    prev_state_json = excluded.prev_state_json,
                    comparisons_done = excluded.comparisons_done,
                    estimated_total = excluded.estimated_total,
                    is_finished = excluded.is_finished,
                    result_json = excluded.result_json,
                    last_question_chat_id = excluded.last_question_chat_id,
                    last_question_message_id = excluded.last_question_message_id,
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
                    last_question_chat_id,
                    last_question_message_id,
                    now,
                ),
            )
            await db.commit()

    async def update_last_question_message(
        self,
        user_id: int,
        *,
        chat_id: int,
        message_id: int,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                UPDATE sessions
                SET last_question_chat_id = ?,
                    last_question_message_id = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (chat_id, message_id, now, user_id),
            )
            await db.commit()

    async def finish(
        self,
        user_id: int,
        *,
        state_json: str,
        comparisons_done: int,
        estimated_total: int,
        result_json: str,
    ) -> None:
        await self.save(
            user_id,
            state_json=state_json,
            prev_state_json=None,
            comparisons_done=comparisons_done,
            estimated_total=estimated_total,
            is_finished=True,
            result_json=result_json,
        )

    async def delete(self, user_id: int) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            await db.commit()

    async def undo(self, user_id: int) -> Session | None:
        session = await self.load(user_id)
        if session is None or session.is_finished or not session.prev_state_json:
            return session

        now = datetime.now(UTC).isoformat()
        comparisons_done = max(session.comparisons_done - 1, 0)
        async with aiosqlite.connect(self._db_path) as db:
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

        return await self.load(user_id)
