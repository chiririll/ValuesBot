SELECT result_json
FROM results
WHERE user_id = ?
ORDER BY finished_at DESC
LIMIT 1;
