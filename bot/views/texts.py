"""Single source of truth for all user-visible text.

Everything translatable lives here: messages, button labels, headers
inside the formatted result, the BotFather command menu, etc.
"""

from __future__ import annotations

BOT_COMMANDS: tuple[tuple[str, str], ...] = (
    ("start", "Начать или продолжить тест"),
    ("undo", "Отменить последний выбор"),
    ("restart", "Начать тест заново"),
    ("result", "Показать результат"),
)

_COMMANDS_BLOCK = "\n".join(
    f"/{command} — {description.lower()}" for command, description in BOT_COMMANDS
)

WELCOME = (
    "Привет! Это бот для ранжирования личных ценностей.\n\n"
    "Тест состоит из двух частей: терминальные и инструментальные ценности. "
    "Сначала вы ранжируете тематические группы, затем — конкретные ценности "
    "из самых важных для вас тем. Всего около {total} сравнений.\n\n"
    "Команды:\n"
    f"{_COMMANDS_BLOCK}"
)

RESUME_PROMPT = "У вас есть незавершённый тест.\n{bar}\n\nПродолжить или начать заново?"

QUESTION_PROMPT = "Что для вас важнее?"

LOWER_PROMPT = "Какая из этих ценностей наименее важна для вас?"

RESTART_CONFIRM = "Вы уверены, что хотите начать тест заново?\nТекущий прогресс будет потерян."

UNDO_UNAVAILABLE = "Отменить последний выбор пока нельзя."

ALREADY_FINISHED = "Тест уже завершён. Используйте /result, чтобы посмотреть результат."

NO_RESULT = "Результат пока недоступен. Сначала пройдите тест командой /start."

TEST_FINISHED = "Тест завершён! Вот ваши результаты:"

SESSION_NOT_FOUND_ALERT = "Сессия не найдена. Нажмите /start."

BTN_START = "Начать"
BTN_CONTINUE = "Продолжить"
BTN_RESTART = "Начать заново"
BTN_RESTART_CONFIRM_YES = "Да, начать заново"
BTN_RESTART_CONFIRM_NO = "Отмена"

CATEGORY_HEADER_SUFFIX_THEMES = " · Сравнение тем"
CATEGORY_HEADER_SUFFIX_LOWER = " · Дополнительные ценности"

THEME_EXAMPLES_PREFIX = "например"

RESULT_HEADER_IMPORTANT = "Важные (по убыванию значимости):"
RESULT_HEADER_ALSO_IMPORTANT = "Также важные (без определённого порядка):"
RESULT_HEADER_LESS_IMPORTANT = "Менее важные:"
