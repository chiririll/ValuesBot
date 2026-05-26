UPDATE sessions
SET state_json = ?,
    prev_state_json = ?,
    comparisons_done = ?,
    estimated_total = ?,
    question_id = ?,
    updated_at = ?
WHERE id = ?;
