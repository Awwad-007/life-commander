"""
Digital Life Command Center - Streamlit Dashboard
==================================================
Streamlit-compatible version of dashboard.py.
Works on Streamlit Cloud with the same JSONL data and SQL joins.
"""

import json
import sqlite3
import os
import streamlit as st
from datetime import date, datetime

st.set_page_config(
    page_title="Life Commander",
    page_icon="⚡",
    layout="wide",
)

# ── Dark theme CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

.stApp {
    background: #08090a;
    color: #e8e8ec;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

.brand-header {
    padding: 8px 0 24px 0;
    border-bottom: 1px solid #1e1e24;
    margin-bottom: 28px;
}
.brand-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #fff;
}
.brand-sub {
    font-size: 13px;
    color: #55555e;
    margin-top: 2px;
}

.section-label {
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #44444d;
    font-weight: 600;
    margin: 28px 0 14px 0;
}

.insight-card {
    background: #0f0f12;
    border: 1px solid #1c1c22;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
}
.insight-card .card-title {
    font-size: 14px;
    font-weight: 600;
    color: #e8e8ec;
    margin-bottom: 2px;
}
.insight-card .card-sub {
    font-size: 11.5px;
    color: #44444d;
    margin-bottom: 14px;
}
.insight-card .count-badge {
    float: right;
    font-size: 11px;
    color: #55555e;
    border: 1px solid #1c1c22;
    border-radius: 20px;
    padding: 1px 8px;
}

.sql-block {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    background: #0a0a0c;
    border: 1px solid #1c1c22;
    border-radius: 8px;
    padding: 10px 12px;
    color: #55555e;
    white-space: pre-wrap;
    margin-top: 10px;
}

.row-table {
    font-size: 12.5px;
    width: 100%;
}
.row-table th {
    color: #44444d;
    font-size: 10.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 4px 0 8px 0;
    text-align: left;
}
.row-table td {
    padding: 7px 0;
    border-top: 1px solid #161619;
    color: #c0c0c8;
}
.tag-evt {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    background: #0d1a2e;
    color: #4d8eff;
    border: 1px solid #1a2e50;
    border-radius: 4px;
    padding: 2px 5px;
}
.tag-tsk {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    background: #1a1a0d;
    color: #bba44d;
    border: 1px solid #2e2a1a;
    border-radius: 4px;
    padding: 2px 5px;
}
.empty-msg {
    color: #33333b;
    font-size: 12.5px;
    padding: 8px 0;
}

.stDataFrame { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Data paths ───────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SRC_CFG = {
    "notion":   ("notion_pages.jsonl",   ["id", "name", "status"],          "n"),
    "calendar": ("calendar_events.jsonl",["id", "summary", "start_time"],   "e"),
    "todoist":  ("todoist_tasks.jsonl",  ["id", "content", "due_date"],     "t"),
}

def read_src(src):
    rows = []
    path = os.path.join(DATA, SRC_CFG[src][0])
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows

def write_src(src, rows):
    cols = SRC_CFG[src][1]
    path = os.path.join(DATA, SRC_CFG[src][0])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({c: r.get(c, "") for c in cols}) + "\n")

def next_id(src):
    pre = SRC_CFG[src][2]
    rows = read_src(src)
    nums = [int(r["id"][len(pre):]) for r in rows
            if str(r["id"]).startswith(pre) and str(r["id"])[len(pre):].isdigit()]
    return f"{pre}{(max(nums) + 1) if nums else 1}"

def build_db():
    con = sqlite3.connect(":memory:")
    for src, (fname, cols, _) in SRC_CFG.items():
        con.execute(f"CREATE TABLE {src} ({', '.join(cols)})")
        rows = [tuple(r.get(c, "") for c in cols) for r in read_src(src)]
        ph = ", ".join("?" * len(cols))
        con.executemany(f"INSERT INTO {src} VALUES ({ph})", rows)
    return con

# ── Queries ──────────────────────────────────────────────────────────────────
QUERIES = {
    "A": {
        "title": "Goals with no time blocked",
        "sub": "Notion × Calendar",
        "sql": """SELECT p.name AS project
FROM notion p
LEFT JOIN calendar e ON e.summary LIKE '%' || p.name || '%'
WHERE e.id IS NULL ORDER BY p.name""",
        "params": lambda t: (),
    },
    "B": {
        "title": "Due soon but unscheduled",
        "sub": "Todoist × Calendar",
        "sql": """SELECT t.content AS task, t.due_date AS due
FROM todoist t
LEFT JOIN calendar e ON date(e.start_time) = t.due_date
WHERE t.due_date <= date(?, '+7 day') AND e.id IS NULL
ORDER BY t.due_date""",
        "params": lambda t: (t,),
    },
    "C": {
        "title": "Today's command center",
        "sub": "All three sources",
        "sql": """SELECT 'event' AS kind, e.summary AS item, e.start_time AS at
FROM calendar e WHERE date(e.start_time) = ?
UNION ALL
SELECT 'task', t.content, t.due_date FROM todoist t
WHERE t.due_date = ? ORDER BY at""",
        "params": lambda t: (t, t),
    },
}

def run_query(con, key, today):
    q = QUERIES[key]
    cur = con.execute(q["sql"], q["params"](today))
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows

def render_table(cols, rows, key):
    if not rows:
        st.markdown('<div class="empty-msg">All clear ✓</div>', unsafe_allow_html=True)
        return
    header = "".join(f"<th>{c}</th>" for c in cols)
    body = ""
    for row in rows:
        cells = ""
        for i, v in enumerate(row):
            if key == "C" and i == 0:
                tag_cls = "tag-evt" if v == "event" else "tag-tsk"
                label = "EVT" if v == "event" else "TSK"
                cells += f'<td><span class="{tag_cls}">{label}</span></td>'
            else:
                cells += f"<td>{v}</td>"
        body += f"<tr>{cells}</tr>"
    st.markdown(
        f'<table class="row-table"><tr>{header}</tr>{body}</table>',
        unsafe_allow_html=True
    )

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
  <div class="brand-title">⚡ Life Commander</div>
  <div class="brand-sub">SQL joins across Notion, Calendar, and Todoist — one query per insight</div>
</div>
""", unsafe_allow_html=True)

today = st.date_input("Today's date", value=date(2026, 5, 30), label_visibility="collapsed")
today_str = today.strftime("%Y-%m-%d")

con = build_db()

# ── Insights ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Insights</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
for col, key in zip([col1, col2, col3], ["A", "B", "C"]):
    with col:
        q = QUERIES[key]
        cols_q, rows_q = run_query(con, key, today_str)
        st.markdown(f"""
        <div class="insight-card">
          <span class="count-badge">{len(rows_q)}</span>
          <div class="card-title">{q['title']}</div>
          <div class="card-sub">{q['sub']}</div>
        </div>
        """, unsafe_allow_html=True)
        render_table(cols_q, rows_q, key)
        with st.expander("SQL"):
            st.code(q["sql"], language="sql")

con.close()

# ── Sources ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Sources</div>', unsafe_allow_html=True)

src_col1, src_col2, src_col3 = st.columns(3)

# Notion
with src_col1:
    notion_rows = read_src("notion")
    st.markdown(f'<div class="insight-card"><span class="count-badge">{len(notion_rows)}</span><div class="card-title">Notion</div><div class="card-sub">Goals / Projects</div></div>', unsafe_allow_html=True)
    for r in notion_rows:
        c1, c2 = st.columns([3, 1])
        c1.caption(r.get("name", ""))
        if c2.button("✕", key=f"del_n_{r['id']}"):
            write_src("notion", [x for x in notion_rows if x["id"] != r["id"]])
            st.rerun()
    with st.form("add_notion", clear_on_submit=True):
        new_name = st.text_input("New goal", placeholder="Goal name")
        new_status = st.text_input("Status", value="In Progress")
        if st.form_submit_button("Add"):
            notion_rows.append({"id": next_id("notion"), "name": new_name, "status": new_status})
            write_src("notion", notion_rows)
            st.rerun()

# Calendar
with src_col2:
    cal_rows = read_src("calendar")
    st.markdown(f'<div class="insight-card"><span class="count-badge">{len(cal_rows)}</span><div class="card-title">Calendar</div><div class="card-sub">Google Calendar events</div></div>', unsafe_allow_html=True)
    for r in cal_rows:
        c1, c2 = st.columns([3, 1])
        c1.caption(f"{r.get('summary','')} · {r.get('start_time','')[:10]}")
        if c2.button("✕", key=f"del_e_{r['id']}"):
            write_src("calendar", [x for x in cal_rows if x["id"] != r["id"]])
            st.rerun()
    with st.form("add_cal", clear_on_submit=True):
        new_sum = st.text_input("Event title", placeholder="Meeting / Focus block")
        new_dt = st.date_input("Date", value=today)
        new_time = st.time_input("Time", value=datetime.strptime("09:00", "%H:%M").time())
        if st.form_submit_button("Add"):
            start = f"{new_dt} {new_time}"
            cal_rows.append({"id": next_id("calendar"), "summary": new_sum, "start_time": start})
            write_src("calendar", cal_rows)
            st.rerun()

# Todoist
with src_col3:
    todo_rows = read_src("todoist")
    st.markdown(f'<div class="insight-card"><span class="count-badge">{len(todo_rows)}</span><div class="card-title">Todoist</div><div class="card-sub">Tasks</div></div>', unsafe_allow_html=True)
    for r in todo_rows:
        c1, c2 = st.columns([3, 1])
        c1.caption(f"{r.get('content','')} · {r.get('due_date','')}")
        if c2.button("✕", key=f"del_t_{r['id']}"):
            write_src("todoist", [x for x in todo_rows if x["id"] != r["id"]])
            st.rerun()
    with st.form("add_todo", clear_on_submit=True):
        new_task = st.text_input("Task", placeholder="Task description")
        new_due = st.date_input("Due date", value=today)
        if st.form_submit_button("Add"):
            todo_rows.append({"id": next_id("todoist"), "content": new_task, "due_date": str(new_due)})
            write_src("todoist", todo_rows)
            st.rerun()

st.markdown("---")
st.caption("One SQL query per insight. No multi-step tool calls. Local-first & private.")
