from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from bot.db._sql_loader import load_migrations, load_sql

_SQL_CREATE_TABLE = load_sql("create_table")
_SQL_LOAD_SESSION = load_sql("load_session")
_SQL_UPSERT_SESSION = load_sql("upsert_session")
_SQL_UPDATE_LAST_QUESTION_MESSAGE = load_sql("update_last_question_message")
_SQL_DELETE_SESSION = load_sql("delete_session")
_SQL_UNDO_SESSION = load_sql("undo_session")
_SQL_MIGRATIONS = load_migrations()


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
            await db.executescript(_SQL_CREATE_TABLE)
            for migration in _SQL_MIGRATIONS:
                with suppress(aiosqlite.OperationalError):
                    await db.executescript(migration)
            await db.commit()

    async def close(self) -> None:
        return None

    async def load(self, user_id: int) -> Session | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(_SQL_LOAD_SESSION, (user_id,))
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
                _SQL_UPSERT_SESSION,
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
                _SQL_UPDATE_LAST_QUESTION_MESSAGE,
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
            await db.execute(_SQL_DELETE_SESSION, (user_id,))
            await db.commit()

    async def undo(self, user_id: int) -> Session | None:
        session = await self.load(user_id)
        if session is None or session.is_finished or not session.prev_state_json:
            return session

        now = datetime.now(UTC).isoformat()
        comparisons_done = max(session.comparisons_done - 1, 0)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                _SQL_UNDO_SESSION,
                (
                    session.prev_state_json,
                    comparisons_done,
                    now,
                    user_id,
                ),
            )
            await db.commit()

        return await self.load(user_id)
