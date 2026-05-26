UPDATE sessions
SET state_json = ?,
    prev_state_json = NULL,
    comparisons_done = ?,
    is_finished = 0,
    result_json = NULL,
    updated_at = ?
WHERE user_id = ?;
