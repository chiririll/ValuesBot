UPDATE sessions
SET last_question_chat_id = ?,
    last_question_message_id = ?,
    updated_at = ?
WHERE id = ?;
