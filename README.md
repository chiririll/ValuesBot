# ValuesBot

Telegram-бот для прохождения теста на ранжирование личных ценностей по методологии Рокича. Пользователь сравнивает пары элементов и получает кластеризованный результат: важные и менее важные ценности в каждой категории.

## Как это работает

Тест состоит из **двух категорий** — терминальные и инструментальные ценности. Внутри каждой категории три этапа:

1. **Сравнение тем** — ранжирование 4 тематических групп (попарно).
2. **Сравнение ценностей** — плоская сортировка ценностей из двух самых важных тем (попарно).
3. **Отсев в нижних темах** — для оставшихся ценностей показываются тройки, нужно вычеркнуть наименее важную. Это даёт основание разделить их на «также важные» и «менее важные» без полной сортировки.

Вопросы из обеих категорий **чередуются**, но в одном вопросе всегда сравниваются элементы одного типа.

Алгоритм — **пошаговая сортировка слиянием (merge sort)** + **тройное вычёркивание** на нижнем этапе. Worst case — около **100 сравнений**.

**Результат** — три блока в каждой категории:
- **Важные** (отсортированные) — из топ-2 тем
- **Также важные** (без порядка) — пережившие тройной отсев из нижних тем
- **Менее важные** — вычеркнутые на этапе тройного отсева

Прогресс сохраняется в SQLite. Доступны `/undo`, `/restart` и `/result`.

## Требования

- Python 3.11–3.12
- [uv](https://docs.astral.sh/uv/) (рекомендуется)

## Установка

```bash
git clone <repository-url>
cd ValuesBot
uv sync --group dev
```

## Настройка

1. Создайте бота у [@BotFather](https://t.me/BotFather) в Telegram и получите токен.
2. Скопируйте файл окружения:

```bash
cp example.env .env
```

3. Укажите токен в `.env`:

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

## Запуск

```bash
uv run python main.py
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начать тест или продолжить незавершённый |
| `/undo` | Отменить последний выбор |
| `/restart` | Начать тест заново (с подтверждением) |
| `/result` | Показать итоговый результат |

## Разработка

```bash
# Тесты с покрытием
uv run pytest
uv run pytest --cov=bot --cov-report=term-missing

# Линтер и типы
uv run ruff check bot tests
uv run ruff format bot tests
uv run mypy bot

# Pre-commit (один раз)
uv run pre-commit install
uv run pre-commit run --all-files
```

Тесты используют компактный каталог `tests/fixtures/values.json`, а не продакшен-данные из `data/values.json`.

**Known limitation:** защита от гонок при быстрых тапах реализована через `asyncio.Lock` на пользователя в рамках одного процесса polling. Multi-process deployment потребует версионирования строк в БД или внешней блокировки.

## Структура проекта

```
ValuesBot/
├── bot/
│   ├── config.py              # Settings, load_settings()
│   ├── bot.py                 # DI-сборка и start_polling
│   ├── core/
│   │   ├── sort.py            # инкрементальный merge sort
│   │   ├── stages.py          # Stage-стратегии (themes/values/lower)
│   │   ├── testflow.py        # TestState, TestResult
│   │   └── values.py          # Catalog, load_catalog
│   ├── db/
│   │   └── sessions_repo.py   # SQLite-сессии
│   ├── services/
│   │   ├── events.py          # SessionEvent (Welcome/Question/Finished/…)
│   │   └── session_service.py # бизнес-логика сессии + per-user lock
│   ├── views/
│   │   ├── formatting.py      # тексты вопросов и результатов
│   │   ├── renderer.py        # SessionEvent → сообщение
│   │   ├── targets.py         # AnswerTarget / EditMessageTarget
│   │   ├── keyboards.py
│   │   └── texts.py
│   └── handlers/
│       ├── commands.py        # /start, /undo, /restart, /result
│       └── callbacks.py       # start:*, pick:*, restart:*
├── tests/
│   ├── fixtures/values.json
│   ├── core/
│   ├── views/
│   ├── db/
│   ├── services/
│   └── handlers/
├── data/
│   └── values.json
├── main.py
└── pyproject.toml
```

## Формат данных

Файл `data/values.json` содержит две категории (`terminal`, `instrumental`), каждая с тематическими группами и словарём ценностей:

```json
{
  "terminal": {
    "name": "Терминальные ценности",
    "groups": [
      {
        "name": "Личное развитие и самореализация",
        "values": {
          "Самосовершенствование": "Постоянный личностный рост..."
        }
      }
    ]
  }
}
```
