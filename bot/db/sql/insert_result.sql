INSERT INTO results (
    session_id,
    user_id,
    result_json,
    comparisons_done,
    estimated_total,
    finished_at
) VALUES (?, ?, ?, ?, ?, ?);
