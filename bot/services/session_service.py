from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from bot.core.testflow import TestResult, TestState
from bot.core.values import Catalog, initial_estimated_total
from bot.db.sessions_repo import Session, SessionsRepository
from bot.services import events

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
            session = await self._repo.load(user_id)
            if session and session.is_finished:
                return events.AlreadyFinished()
            if session and not session.is_finished:
                state = TestState.from_json(session.state_json)
                return events.Resume(
                    comparisons_done=state.comparisons_done(),
                    estimated_total=state.estimated_total(self._catalog),
                )
            return events.Welcome(estimated_total=self._estimated_total)

    async def create_new(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            state = TestState.initial(self._catalog)
            estimated_total = state.estimated_total(self._catalog)
            await self._repo.save(
                user_id,
                state_json=state.to_json(),
                prev_state_json=None,
                comparisons_done=0,
                estimated_total=estimated_total,
            )
            logger.info("new_session_created", extra={"user_id": user_id})
            return self._question_event(state)

    async def continue_session(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._repo.load(user_id)
            if session is None or session.is_finished:
                return await self._create_new_unlocked(user_id)
            return await self._render_state_unlocked(user_id, session)

    async def advance(self, user_id: int, choice: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._repo.load(user_id)
            if session is None or session.is_finished:
                raise RuntimeError("Session not found or already finished")

            state = TestState.from_json(session.state_json)
            prev_state_json = session.state_json
            state.step(choice, self._catalog)
            comparisons_done = state.comparisons_done()
            estimated_total = state.estimated_total(self._catalog)
            logger.info(
                "session_advanced",
                extra={"user_id": user_id, "comparisons_done": comparisons_done},
            )

            if state.is_done():
                return await self._finish_unlocked(user_id, state)

            await self._repo.save(
                user_id,
                state_json=state.to_json(),
                prev_state_json=prev_state_json,
                comparisons_done=comparisons_done,
                estimated_total=estimated_total,
            )
            return self._question_event(state)

    async def undo(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session_before = await self._repo.load(user_id)
            if (
                session_before is None
                or session_before.is_finished
                or not session_before.prev_state_json
            ):
                return events.UndoUnavailable()

            session = await self._repo.undo(user_id)
            if session is None:
                return events.UndoUnavailable()

            logger.info("session_undone", extra={"user_id": user_id})
            return await self._render_state_unlocked(user_id, session)

    async def restart(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            await self._repo.delete(user_id)
            logger.info("session_restarted", extra={"user_id": user_id})
            return await self._create_new_unlocked(user_id)

    async def show_result(self, user_id: int) -> events.SessionEvent:
        async with self._lock_for(user_id):
            session = await self._repo.load(user_id)
            if session is None or not session.is_finished or not session.result_json:
                return events.NoResult()
            data = json.loads(session.result_json)
            return events.Finished(result=TestResult.from_dict(data))

    def restart_confirm(self) -> events.RestartConfirm:
        return events.RestartConfirm()

    async def record_last_question(
        self,
        user_id: int,
        *,
        chat_id: int,
        message_id: int,
    ) -> None:
        async with self._lock_for(user_id):
            await self._repo.update_last_question_message(
                user_id,
                chat_id=chat_id,
                message_id=message_id,
            )

    async def load_session(self, user_id: int) -> Session | None:
        return await self._repo.load(user_id)

    async def _create_new_unlocked(self, user_id: int) -> events.SessionEvent:
        state = TestState.initial(self._catalog)
        estimated_total = state.estimated_total(self._catalog)
        await self._repo.save(
            user_id,
            state_json=state.to_json(),
            prev_state_json=None,
            comparisons_done=0,
            estimated_total=estimated_total,
        )
        logger.info("new_session_created", extra={"user_id": user_id})
        return self._question_event(state)

    async def _render_state_unlocked(self, user_id: int, session: Session) -> events.SessionEvent:
        if session.is_finished and session.result_json:
            data = json.loads(session.result_json)
            return events.Finished(result=TestResult.from_dict(data))

        state = TestState.from_json(session.state_json)
        if state.is_done():
            return await self._finish_unlocked(user_id, state)

        track = state.current_track()
        keys = state.current_keys()
        if track is None or keys is None:
            return await self._finish_unlocked(user_id, state)

        return self._question_event(state)

    async def _finish_unlocked(self, user_id: int, state: TestState) -> events.Finished:
        result = state.result(self._catalog)
        result_json = json.dumps(result.to_dict(), ensure_ascii=False)
        await self._repo.finish(
            user_id,
            state_json=state.to_json(),
            comparisons_done=state.comparisons_done(),
            estimated_total=state.estimated_total(self._catalog),
            result_json=result_json,
        )
        logger.info("session_finished", extra={"user_id": user_id})
        return events.Finished(result=result)

    def _question_event(self, state: TestState) -> events.Question:
        track = state.current_track()
        keys = state.current_keys()
        if track is None or keys is None:
            raise RuntimeError("No active question")
        return events.Question(
            track=track,
            keys=keys,
            comparisons_done=state.comparisons_done(),
            estimated_total=state.estimated_total(self._catalog),
        )
