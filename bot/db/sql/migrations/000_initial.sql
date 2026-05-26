CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    state_json TEXT NOT NULL,
    prev_state_json TEXT,
    comparisons_done INTEGER NOT NULL DEFAULT 0,
    estimated_total INTEGER NOT NULL DEFAULT 119,
    question_id INTEGER NOT NULL DEFAULT 1,
    last_question_chat_id INTEGER,
    last_question_message_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    session_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    comparisons_done INTEGER NOT NULL DEFAULT 0,
    estimated_total INTEGER NOT NULL DEFAULT 119,
    finished_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_results_user_id ON results(user_id);
