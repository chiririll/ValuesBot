INSERT INTO sessions (
    user_id,
    state_json,
    prev_state_json,
    comparisons_done,
    estimated_total,
    question_id,
    last_question_chat_id,
    last_question_message_id,
    created_at,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
