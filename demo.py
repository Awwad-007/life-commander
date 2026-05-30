"""
Digital Life Command Center - LOCAL DEMO RUNNER
================================================
Proves the Coral value prop *without* installing Coral or any OAuth:
one SQL query joins three silos (Notion projects, Calendar events,
Todoist tasks) using Python's built-in sqlite3. Zero dependencies.

The real product (setup.ps1) swaps this sqlite engine for `coral mcp-stdio`
and the JSONL files for live APIs. The SQL stays the same shape.
"""
import json, sqlite3, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TODAY = "2026-05-30"  # pinned so the demo is deterministic on stage

# Each Coral source (notion.pages, calendar.events, todoist.tasks) becomes
# one sqlite table loaded from its JSONL snapshot.
SRC = {
    "notion_pages":     ("notion_pages.jsonl",     ["id", "name", "status"]),
    "calendar_events":  ("calendar_events.jsonl",  ["id", "summary", "start_time"]),
    "todoist_tasks":    ("todoist_tasks.jsonl",    ["id", "content", "due_date"]),
}

def load(db):
    for tbl, (fname, cols) in SRC.items():
        db.execute(f"CREATE TABLE {tbl} ({', '.join(cols)})")
        rows = []
        with open(os.path.join(DATA, fname), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    rows.append(tuple(r[c] for c in cols))
        ph = ", ".join("?" * len(cols))
        db.executemany(f"INSERT INTO {tbl} VALUES ({ph})", rows)

def show(db, title, sql, params=()):
    cur = db.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"\n=== {title} ===")
    print(f"SQL: {' '.join(sql.split())}")
    w = [max(len(cols[i]), *(len(str(r[i])) for r in rows)) if rows else len(cols[i])
         for i in range(len(cols))]
    line = " | ".join(cols[i].ljust(w[i]) for i in range(len(cols)))
    print(line); print("-" * len(line))
    if not rows:
        print("(no rows)")
    for r in rows:
        print(" | ".join(str(r[i]).ljust(w[i]) for i in range(len(cols))))

# ---- The 3 cross-source "wow" queries -------------------------------------

# A: Notion goals with NO calendar time blocked  (Notion x Calendar)
Q_A = """
SELECT p.name AS proj
FROM notion_pages p
LEFT JOIN calendar_events e
  ON e.summary LIKE '%' || p.name || '%'
WHERE e.id IS NULL
ORDER BY p.name
"""

# B: Tasks due soon with no calendar block to do them  (Todoist x Calendar)
Q_B = """
SELECT t.content AS task, t.due_date AS due
FROM todoist_tasks t
LEFT JOIN calendar_events e
  ON date(e.start_time) = t.due_date
WHERE t.due_date <= date(?, '+7 day')
  AND e.id IS NULL
ORDER BY t.due_date
"""

# C: Today's command center  (all three sources in one statement)
Q_C = """
SELECT 'event' AS kind, e.summary AS item, e.start_time AS at
FROM calendar_events e WHERE date(e.start_time) = ?
UNION ALL
SELECT 'task', t.content, t.due_date
FROM todoist_tasks t WHERE t.due_date = ?
ORDER BY at
"""

def main():
    db = sqlite3.connect(":memory:")
    load(db)
    print(f"Digital Life Command Center  -  demo date {TODAY}")
    show(db, "A. Goals with NO time blocked (Notion x Calendar)", Q_A)
    show(db, "B. Due soon but unscheduled (Todoist x Calendar)", Q_B, (TODAY,))
    show(db, "C. Today's command center (all 3 sources)", Q_C, (TODAY, TODAY))
    print("\nDone. 3 silos, joined in SQL, zero multi-step tool calls.")

if __name__ == "__main__":
    main()
