INSERT INTO sessions (
    user_id,
    state_json,
    prev_state_json,
    comparisons_done,
    estimated_total,
    is_finished,
    result_json,
    last_question_chat_id,
    last_question_message_id,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(user_id) DO UPDATE SET
    state_json = excluded.state_json,
    prev_state_json = excluded.prev_state_json,
    comparisons_done = excluded.comparisons_done,
    estimated_total = excluded.estimated_total,
    is_finished = excluded.is_finished,
    result_json = excluded.result_json,
    last_question_chat_id = excluded.last_question_chat_id,
    last_question_message_id = excluded.last_question_message_id,
    updated_at = excluded.updated_at;
