-- Digital Life Command Center :: Coral cross-source queries
-- Run with the real runtime:  coral sql "<paste a query>"
-- NOTE: confirm exact column names first with:
--   coral sql "SELECT schema_name, table_name FROM coral.tables ORDER BY 1,2"
--   coral describe-table notion.pages   (and calendar.events, todoist.tasks)
-- The local demo.py uses the same SQL with sqlite table names (underscores).

-- A. Goals with NO calendar time blocked  (Notion x Calendar)
SELECT p.name AS proj
FROM notion.pages p
LEFT JOIN calendar.events e
  ON e.summary LIKE '%' || p.name || '%'
 AND e.start_time >= current_date
WHERE e.id IS NULL
LIMIT 20;

-- B. Tasks due soon with no calendar block  (Todoist x Calendar)
SELECT t.content AS task, t.due_date AS due
FROM todoist.tasks t
LEFT JOIN calendar.events e
  ON CAST(e.start_time AS DATE) = t.due_date
WHERE t.due_date <= current_date + INTERVAL '7' DAY
  AND e.id IS NULL
ORDER BY t.due_date
LIMIT 20;

-- C. Today's command center  (all three sources, one statement)
WITH d AS (SELECT current_date AS t)
SELECT 'event' AS kind, e.summary AS item, e.start_time AS at
FROM calendar.events e, d WHERE CAST(e.start_time AS DATE) = d.t
UNION ALL
SELECT 'task', t.content, t.due_date
FROM todoist.tasks t, d WHERE t.due_date = d.t
ORDER BY at;
