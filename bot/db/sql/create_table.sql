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
