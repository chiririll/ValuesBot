UPDATE sessions
SET state_json = ?,
    prev_state_json = NULL,
    comparisons_done = ?,
    question_id = ?,
    updated_at = ?
WHERE id = ?;
