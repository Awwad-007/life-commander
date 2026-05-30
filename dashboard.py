"""
Digital Life Command Center - INTERACTIVE DASHBOARD
===================================================
Single-file, stdlib-only web dashboard (no pip installs). It serves a UI at
http://localhost:8765 backed by the same JSONL snapshots + sqlite SQL joins
as demo.py. Add/delete projects, events, and tasks from the page and watch the
cross-source insights recompute live.

Run:  python dashboard.py     then open  http://localhost:8765
"""
import json, sqlite3, os, http.server, socketserver
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PORT = 8765
DEF_TODAY = "2026-05-30"

# source key -> (file, columns, id-prefix)
SRC = {
    "notion":   ("notion_pages.jsonl",    ["id", "name", "status"],          "n"),
    "calendar": ("calendar_events.jsonl", ["id", "summary", "start_time"],   "e"),
    "todoist":  ("todoist_tasks.jsonl",   ["id", "content", "due_date"],     "t"),
}
TBL = {"notion": "notion_pages", "calendar": "calendar_events", "todoist": "todoist_tasks"}

def read(src):
    rows = []
    path = os.path.join(DATA, SRC[src][0])
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows

def write(src, rows):
    cols = SRC[src][1]
    path = os.path.join(DATA, SRC[src][0])
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({c: r.get(c, "") for c in cols}) + "\n")

def next_id(src):
    pre = SRC[src][2]
    rows = read(src)
    nums = [int(r["id"][len(pre):]) for r in rows if str(r["id"]).startswith(pre)
            and str(r["id"])[len(pre):].isdigit()]
    return f"{pre}{(max(nums) + 1) if nums else 1}"

def db():
    con = sqlite3.connect(":memory:")
    for src, (fname, cols, _) in SRC.items():
        con.execute(f"CREATE TABLE {TBL[src]} ({', '.join(cols)})")
        rows = [tuple(r.get(c, "") for c in cols) for r in read(src)]
        ph = ", ".join("?" * len(cols))
        con.executemany(f"INSERT INTO {TBL[src]} VALUES ({ph})", rows)
    return con

# ---- The 3 cross-source queries -------------------------------------------
Q = {
    "A": ("Goals with no time blocked", "Notion x Calendar", """
        SELECT p.name AS project
        FROM notion_pages p
        LEFT JOIN calendar_events e ON e.summary LIKE '%' || p.name || '%'
        WHERE e.id IS NULL ORDER BY p.name""", 0),
    "B": ("Due soon but unscheduled", "Todoist x Calendar", """
        SELECT t.content AS task, t.due_date AS due
        FROM todoist_tasks t
        LEFT JOIN calendar_events e ON date(e.start_time) = t.due_date
        WHERE t.due_date <= date(?, '+7 day') AND e.id IS NULL
        ORDER BY t.due_date""", 1),
    "C": ("Today's command center", "all three sources", """
        SELECT 'event' AS kind, e.summary AS item, e.start_time AS at
        FROM calendar_events e WHERE date(e.start_time) = ?
        UNION ALL
        SELECT 'task', t.content, t.due_date FROM todoist_tasks t
        WHERE t.due_date = ? ORDER BY at""", 2),
}

def run_q(con, key, today):
    title, sub, sql, nparams = Q[key]
    params = {0: (), 1: (today,), 2: (today, today)}[nparams]
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    return {"title": title, "sub": sub, "sql": " ".join(sql.split()), "cols": cols, "rows": rows}

def state(today):
    con = db()
    out = {"today": today, "queries": {k: run_q(con, k, today) for k in Q},
           "data": {s: read(s) for s in SRC}}
    con.close()
    return out

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self._send(200, HTML, "text/html; charset=utf-8")
        elif u.path == "/api/state":
            q = parse_qs(u.query)
            today = q.get("today", [DEF_TODAY])[0]
            self._send(200, json.dumps(state(today)))
        else:
            self._send(404, "{}")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or "{}")
        u = urlparse(self.path)
        if u.path == "/api/add":
            src = body["src"]
            row = {"id": next_id(src)}
            for c in SRC[src][1][1:]:
                row[c] = body.get(c, "")
            rows = read(src)
            rows.append(row)
            write(src, rows)
            self._send(200, json.dumps({"ok": True, "id": row["id"]}))
        elif u.path == "/api/del":
            src, rid = body["src"], body["id"]
            write(src, [r for r in read(src) if r["id"] != rid])
            self._send(200, json.dumps({"ok": True}))
        else:
            self._send(404, "{}")

HTML = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Life Commander</title>
<style>
 :root{
  --bg:#0a0a0b;--panel:#101012;--bd:#1e1e22;--bd2:#2a2a30;
  --fg:#ededf0;--mut:#7c7c85;--faint:#56565e;--ac:#5b8cff;
 }
 *{box-sizing:border-box}
 html,body{margin:0;background:var(--bg);color:var(--fg);
  font:14px/1.55 ui-sans-serif,system-ui,"Segoe UI",Inter,sans-serif;
  -webkit-font-smoothing:antialiased}
 a{color:var(--ac);text-decoration:none}
 header{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;
  padding:22px 32px;border-bottom:1px solid var(--bd)}
 header .brand{font-size:15px;font-weight:600;letter-spacing:-.01em}
 header .sub{color:var(--mut);font-size:12.5px}
 header .sp{flex:1}
 .ctl{display:flex;align-items:center;gap:8px;color:var(--mut);font-size:12.5px}
 input,select,button{font:inherit;color:var(--fg);background:var(--panel);
  border:1px solid var(--bd2);border-radius:7px;padding:7px 10px;outline:none}
 input:focus{border-color:var(--ac)}
 input[type=date],input[type=datetime-local]{color-scheme:dark}
 button{cursor:pointer;background:transparent;border-color:var(--bd2);color:var(--fg);transition:.12s}
 button:hover{border-color:var(--ac);color:#fff}
 button.pri{background:var(--fg);color:#000;border-color:var(--fg);font-weight:500}
 button.pri:hover{opacity:.9}
 button.x{border:0;background:0;color:var(--faint);padding:2px 6px;font-size:14px}
 button.x:hover{color:#ff6b6b}
 .lbl{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);
  padding:28px 32px 12px;font-weight:600}
 .grid{padding:0 32px;display:grid;gap:16px;
  grid-template-columns:repeat(auto-fill,minmax(330px,1fr));max-width:1320px}
 .card{background:var(--panel);border:1px solid var(--bd);border-radius:12px;
  padding:18px 18px 14px}
 .card .h{display:flex;align-items:baseline;gap:8px;margin-bottom:2px}
 .card .h .t{font-size:13.5px;font-weight:600;letter-spacing:-.01em}
 .card .h .n{margin-left:auto;font-size:12px;color:var(--mut);
  border:1px solid var(--bd2);border-radius:20px;padding:0 8px;min-width:22px;text-align:center}
 .card .s{color:var(--faint);font-size:11.5px;letter-spacing:.02em;margin-bottom:12px}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th{text-align:left;color:var(--faint);font-weight:500;font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;padding:0 8px 7px}
 td{padding:7px 8px;border-top:1px solid var(--bd);vertical-align:middle}
 tr:hover td{background:#141417}
 .empty{color:var(--faint);font-size:12.5px;padding:10px 2px}
 details{margin-top:12px;border-top:1px solid var(--bd);padding-top:10px}
 summary{cursor:pointer;color:var(--mut);font-size:11.5px;letter-spacing:.04em;list-style:none}
 summary::-webkit-details-marker{display:none}
 summary:before{content:"+ ";color:var(--faint)}
 details[open] summary:before{content:"- "}
 code{display:block;background:#0c0c0e;border:1px solid var(--bd);border-radius:8px;
  padding:10px;margin-top:8px;font:11.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  white-space:pre-wrap;color:var(--mut)}
 .tag{font:10px/1 ui-monospace,monospace;letter-spacing:.08em;color:var(--faint);
  border:1px solid var(--bd2);border-radius:4px;padding:3px 5px}
 .form{display:flex;gap:7px;flex-wrap:wrap;margin-top:13px;padding-top:13px;border-top:1px solid var(--bd)}
 .form input{flex:1;min-width:90px}
 footer{padding:32px;color:var(--faint);font-size:11.5px;max-width:1320px}
</style></head><body>
<header>
 <span class=brand>Life Commander</span>
 <span class=sub>SQL joins across Notion, Calendar, and Todoist via Coral</span>
 <span class=sp></span>
 <span class=ctl>Today <input id=today type=date></span>
 <button onclick=load()>Refresh</button>
</header>

<div class=lbl>Insights</div>
<div class=grid id=insights></div>

<div class=lbl>Sources</div>
<div class=grid id=sources></div>

<footer>One SQL query per insight. No multi-step tool calls. Edits persist to data/*.jsonl.</footer>

<script>
const el=h=>{const d=document.createElement('div');d.innerHTML=h.trim();return d.firstChild}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))
let ST={}
async function load(){
 const t=document.getElementById('today').value||'2026-05-30'
 ST=await (await fetch('/api/state?today='+t)).json()
 document.getElementById('today').value=ST.today
 render()
}
async function add(src,fields){
 const b={src};for(const k in fields)b[k]=document.getElementById(fields[k]).value
 await fetch('/api/add',{method:'POST',body:JSON.stringify(b)});load()
}
async function del(src,id){await fetch('/api/del',{method:'POST',body:JSON.stringify({src,id})});load()}
function qcard(k){
 const q=ST.queries[k],r=q.rows
 const body=r.length?`<table><tr>${q.cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr>`+
   r.map(row=>`<tr>${row.map((v,i)=>(k=='C'&&i==0)
     ?`<td><span class=tag>${v=='event'?'EVT':'TSK'}</span></td>`
     :`<td>${esc(v)}</td>`).join('')}</tr>`).join('')+`</table>`
   :`<div class=empty>All clear.</div>`
 return `<div class=card><div class=h><span class=t>${esc(q.title)}</span><span class=n>${r.length}</span></div>
   <div class=s>${esc(q.sub)}</div>${body}
   <details><summary>SQL</summary><code>${esc(q.sql)}</code></details></div>`
}
function dcard(src,cols,labels,form){
 const rows=ST.data[src]
 const t=`<table><tr>${labels.map(l=>`<th>${l}</th>`).join('')}<th></th></tr>`+
  rows.map(r=>`<tr>${cols.map(c=>`<td>${esc(r[c])}</td>`).join('')}
   <td style=text-align:right><button class=x onclick="del('${src}','${r.id}')" title=delete>&times;</button></td></tr>`).join('')+`</table>`
 return `<div class=card><div class=h><span class=t>${src[0].toUpperCase()+src.slice(1)}</span><span class=n>${rows.length}</span></div>
   <div class=s>source</div>${t}<div class=form>${form}</div></div>`
}
function render(){
 const ins=document.getElementById('insights');ins.innerHTML=''
 ;['A','B','C'].forEach(k=>ins.appendChild(el(qcard(k))))
 const s=document.getElementById('sources');s.innerHTML=''
 s.appendChild(el(dcard('notion',['name','status'],['Project','Status'],
   `<input id=np placeholder="New goal"><input id=ns placeholder=status value="In Progress" style=flex:0;width:110px>
    <button class=pri onclick="add('notion',{name:'np',status:'ns'})">Add</button>`)))
 s.appendChild(el(dcard('calendar',['summary','start_time'],['Event','Start'],
   `<input id=cs placeholder="Event title"><input id=ct type=datetime-local style=flex:0>
    <button class=pri onclick="addEv()">Add</button>`)))
 s.appendChild(el(dcard('todoist',['content','due_date'],['Task','Due'],
   `<input id=tc placeholder="Task"><input id=td type=date style=flex:0>
    <button class=pri onclick="add('todoist',{content:'tc',due_date:'td'})">Add</button>`)))
}
function addEv(){
 const v=document.getElementById('ct').value
 const b={src:'calendar',summary:document.getElementById('cs').value,
          start_time:v?v.replace('T',' ')+':00':''}
 fetch('/api/add',{method:'POST',body:JSON.stringify(b)}).then(load)
}
load()
</script></body></html>"""

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), H) as srv:
        print(f"Dashboard running -> http://localhost:{PORT}  (Ctrl+C to stop)")
        srv.serve_forever()
