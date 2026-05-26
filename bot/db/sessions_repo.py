from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from bot.db._sql_loader import load_migrations, load_sql

_SQL_LOAD_ACTIVE = load_sql("load_session_by_user")
_SQL_LOAD_SESSION_BY_ID = load_sql("load_session_by_id")
_SQL_INSERT_SESSION = load_sql("insert_session")
_SQL_UPDATE_SESSION = load_sql("update_session")
_SQL_INSERT_RESULT = load_sql("insert_result")
_SQL_LOAD_LATEST_RESULT = load_sql("load_latest_result")
_SQL_UPDATE_LAST_QUESTION_MESSAGE = load_sql("update_last_question_message")
_SQL_DELETE_SESSION_BY_ID = load_sql("delete_session_by_id")
_SQL_UNDO_SESSION_BY_ID = load_sql("undo_session_by_id")
_SQL_MIGRATIONS = load_migrations()


@dataclass(slots=True)
class Session:
    id: int
    user_id: int
    state_json: str
    prev_state_json: str | None
    comparisons_done: int
    estimated_total: int
    question_id: int
    last_question_chat_id: int | None
    last_question_message_id: int | None


def _row_to_session(row: aiosqlite.Row) -> Session:
    return Session(
        id=row["id"],
        user_id=row["user_id"],
        state_json=row["state_json"],
        prev_state_json=row["prev_state_json"],
        comparisons_done=row["comparisons_done"],
        estimated_total=row["estimated_total"],
        question_id=row["question_id"],
        last_question_chat_id=row["last_question_chat_id"],
        last_question_message_id=row["last_question_message_id"],
    )


class SessionsRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            for migration in _SQL_MIGRATIONS:
                await db.executescript(migration)
            await db.commit()

    async def close(self) -> None:
        return None

    async def load_active(self, user_id: int) -> Session | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(_SQL_LOAD_ACTIVE, (user_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_session(row)

    async def load_by_id(self, session_id: int) -> Session | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(_SQL_LOAD_SESSION_BY_ID, (session_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_session(row)

    async def create(
        self,
        user_id: int,
        *,
        state_json: str,
        prev_state_json: str | None,
        comparisons_done: int,
        estimated_total: int,
        question_id: int = 1,
    ) -> Session:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                _SQL_INSERT_SESSION,
                (
                    user_id,
                    state_json,
                    prev_state_json,
                    comparisons_done,
                    estimated_total,
                    question_id,
                    None,
                    None,
                    now,
                    now,
                ),
            )
            session_id = cursor.lastrowid
            if session_id is None:
                raise RuntimeError("Failed to create session")
            await db.commit()

        session = await self.load_by_id(session_id)
        if session is None:
            raise RuntimeError("Created session not found")
        return session

    async def save(
        self,
        session_id: int,
        *,
        state_json: str,
        prev_state_json: str | None,
        comparisons_done: int,
        estimated_total: int,
        question_id: int,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                _SQL_UPDATE_SESSION,
                (
                    state_json,
                    prev_state_json,
                    comparisons_done,
                    estimated_total,
                    question_id,
                    now,
                    session_id,
                ),
            )
            await db.commit()

    async def update_last_question_message(
        self,
        session_id: int,
        *,
        chat_id: int,
        message_id: int,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                _SQL_UPDATE_LAST_QUESTION_MESSAGE,
                (chat_id, message_id, now, session_id),
            )
            await db.commit()

    async def finish(
        self,
        session: Session,
        *,
        result_json: str,
        comparisons_done: int,
        estimated_total: int,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                _SQL_INSERT_RESULT,
                (
                    session.id,
                    session.user_id,
                    result_json,
                    comparisons_done,
                    estimated_total,
                    now,
                ),
            )
            await db.execute(_SQL_DELETE_SESSION_BY_ID, (session.id,))
            await db.commit()

    async def latest_result(self, user_id: int) -> str | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(_SQL_LOAD_LATEST_RESULT, (user_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            return str(row[0])

    async def delete(self, session_id: int) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(_SQL_DELETE_SESSION_BY_ID, (session_id,))
            await db.commit()

    async def undo(self, session_id: int) -> Session | None:
        session = await self.load_by_id(session_id)
        if session is None or not session.prev_state_json:
            return session

        now = datetime.now(UTC).isoformat()
        comparisons_done = max(session.comparisons_done - 1, 0)
        question_id = max(session.question_id - 1, 1)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                _SQL_UNDO_SESSION_BY_ID,
                (
                    session.prev_state_json,
                    comparisons_done,
                    question_id,
                    now,
                    session_id,
                ),
            )
            await db.commit()

        return await self.load_by_id(session_id)
