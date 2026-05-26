from __future__ import annotations

from aiogram.types import Message

from bot.core.values import Catalog
from bot.services import events
from bot.views import formatting, keyboards
from bot.views.targets import MessageTarget
from bot.views.texts import (
    ALREADY_FINISHED,
    NO_RESULT,
    RESTART_CONFIRM,
    RESUME_PROMPT,
    UNDO_UNAVAILABLE,
    WELCOME,
)


class Renderer:
    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    async def render(
        self, event: events.SessionEvent, target: MessageTarget
    ) -> Message | bool | None:
        match event:
            case events.Welcome(estimated_total=total):
                return await target.send(
                    WELCOME.format(total=total),
                    keyboards.start_keyboard(),
                )
            case events.Resume(
                session_id=session_id,
                comparisons_done=done,
                estimated_total=total,
            ):
                bar = formatting.progress_bar(done, total)
                return await target.send(
                    RESUME_PROMPT.format(bar=bar),
                    keyboards.resume_keyboard(session_id),
                )
            case events.Question() as question:
                text = formatting.format_question_text(
                    self._catalog,
                    question.track,
                    question.keys,
                    comparisons_done=question.comparisons_done,
                    estimated_total=question.estimated_total,
                )
                labels = [
                    formatting.button_label(self._catalog, question.track, key)
                    for key in question.keys
                ]
                return await target.send(
                    text,
                    keyboards.question_keyboard(
                        labels,
                        session_id=question.session_id,
                        question_id=question.question_id,
                    ),
                )
            case events.Finished(result=result):
                return await target.send(
                    formatting.format_result_text(self._catalog, result),
                    None,
                )
            case events.AlreadyFinished():
                return await target.send(ALREADY_FINISHED, None)
            case events.NoResult():
                return await target.send(NO_RESULT, None)
            case events.UndoUnavailable():
                return await target.send(UNDO_UNAVAILABLE, None)
            case events.RestartConfirm(session_id=session_id):
                return await target.send(
                    RESTART_CONFIRM,
                    keyboards.restart_confirm_keyboard(session_id),
                )
        return None
