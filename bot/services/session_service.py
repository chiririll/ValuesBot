from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from bot.core.testflow import TestResult, TestState
from bot.core.values import Catalog, initial_estimated_total
from bot.db.sessions_repo import Session, SessionsRepository
from bot.services import events
from bot.services.errors import StaleCallbackError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, repo: SessionsRepository, catalog: Catalog) -> None:
        self._repo = repo
        self._catalog = catalog
        self._estimated_total = initial_estimated_total(catalog)
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        return self._locks.setdefault(user_id, asyncio.Lock())

    async def start_or_resume(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._repo.load_active(user_id)
            if session is not None:
                state = TestState.from_json(session.state_json)
                return events.Resume(
                    session_id=session.id,
                    comparisons_done=state.comparisons_done(),
                    estimated_total=state.estimated_total(self._catalog),
                )
            if await self._repo.latest_result(user_id) is not None:
                return events.AlreadyFinished()
            return events.Welcome(estimated_total=self._estimated_total)

    async def create_new(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            return await self._create_new_unlocked(user_id)

    async def continue_session(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._repo.load_active(user_id)
            if session is None:
                return await self._create_new_unlocked(user_id)
            return await self._render_state_unlocked(session)

    async def advance(
        self,
        user_id: int,
        session_id: int,
        question_id: int,
        choice: int,
    ) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._require_active_session(user_id, session_id, question_id)
            state = TestState.from_json(session.state_json)
            prev_state_json = session.state_json
            state.step(choice, self._catalog)
            comparisons_done = state.comparisons_done()
            estimated_total = state.estimated_total(self._catalog)
            next_question_id = session.question_id + 1
            logger.info(
                "session_advanced",
                extra={"user_id": user_id, "comparisons_done": comparisons_done},
            )

            if state.is_done():
                return await self._finish_unlocked(session, state)

            await self._repo.save(
                session.id,
                state_json=state.to_json(),
                prev_state_json=prev_state_json,
                comparisons_done=comparisons_done,
                estimated_total=estimated_total,
                question_id=next_question_id,
            )
            return self._question_event(session.id, next_question_id, state)

    async def undo(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session_before = await self._repo.load_active(user_id)
            if session_before is None or not session_before.prev_state_json:
                return events.UndoUnavailable()

            session = await self._repo.undo(session_before.id)
            if session is None:
                return events.UndoUnavailable()

            logger.info("session_undone", extra={"user_id": user_id})
            return await self._render_state_unlocked(session)

    async def restart(self, user_id: int, session_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._repo.load_active(user_id)
            if session is None or session.id != session_id:
                raise StaleCallbackError()
            await self._repo.delete(session.id)
            logger.info("session_restarted", extra={"user_id": user_id})
            return await self._create_new_unlocked(user_id)

    async def show_result(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            result_json = await self._repo.latest_result(user_id)
            if result_json is None:
                return events.NoResult()
            data = json.loads(result_json)
            return events.Finished(result=TestResult.from_dict(data))

    def restart_confirm(self, session_id: int) -> events.RestartConfirm:
        return events.RestartConfirm(session_id=session_id)

    async def record_last_question(
        self,
        session_id: int,
        *,
        chat_id: int,
        message_id: int,
    ) -> None:
        await self._repo.update_last_question_message(
            session_id,
            chat_id=chat_id,
            message_id=message_id,
        )

    async def load_session(self, user_id: int) -> Session | None:
        return await self._repo.load_active(user_id)

    async def _create_new_unlocked(self, user_id: int) -> events.SessionEvent:
        active = await self._repo.load_active(user_id)
        if active is not None:
            await self._repo.delete(active.id)

        state = TestState.initial(self._catalog)
        estimated_total = state.estimated_total(self._catalog)
        session = await self._repo.create(
            user_id,
            state_json=state.to_json(),
            prev_state_json=None,
            comparisons_done=0,
            estimated_total=estimated_total,
            question_id=1,
        )
        logger.info("new_session_created", extra={"user_id": user_id})
        return self._question_event(session.id, session.question_id, state)

    async def _render_state_unlocked(self, session: Session) -> events.SessionEvent:
        state = TestState.from_json(session.state_json)
        if state.is_done():
            return await self._finish_unlocked(session, state)

        track = state.current_track()
        keys = state.current_keys()
        if track is None or keys is None:
            return await self._finish_unlocked(session, state)

        return self._question_event(session.id, session.question_id, state)

    async def _finish_unlocked(self, session: Session, state: TestState) -> events.Finished:
        result = state.result(self._catalog)
        result_json = json.dumps(result.to_dict(), ensure_ascii=False)
        await self._repo.finish(
            session,
            result_json=result_json,
            comparisons_done=state.comparisons_done(),
            estimated_total=state.estimated_total(self._catalog),
        )
        logger.info("session_finished", extra={"user_id": session.user_id})
        return events.Finished(result=result)

    async def _require_active_session(
        self,
        user_id: int,
        session_id: int,
        question_id: int,
    ) -> Session:
        session = await self._repo.load_active(user_id)
        if session is None or session.id != session_id:
            raise StaleCallbackError()
        if session.question_id != question_id:
            raise StaleCallbackError()
        return session

    def _question_event(
        self,
        session_id: int,
        question_id: int,
        state: TestState,
    ) -> events.Question:
        track = state.current_track()
        keys = state.current_keys()
        if track is None or keys is None:
            raise RuntimeError("No active question")
        return events.Question(
            session_id=session_id,
            question_id=question_id,
            track=track,
            keys=keys,
            comparisons_done=state.comparisons_done(),
            estimated_total=state.estimated_total(self._catalog),
        )
