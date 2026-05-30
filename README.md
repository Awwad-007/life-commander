# Digital Life Command Center

An AI agent that unifies personal data (Notion, Google Calendar, Todoist)
through **[Coral](https://withcoral.com/)** — a local-first SQL runtime over
APIs. The agent writes **one SQL query** that JOINs across silos instead of
making slow, error-prone multi-step API/tool calls.

> **Core value prop:** replace multi-step tool-calling with clean SQL joins —
> more accurate, fewer tokens, lower latency.

## What's here

| File | Purpose |
|---|---|
| `demo.py` | **Runnable now.** Local proof using Python's built-in sqlite3 — no Coral, no OAuth. |
| `data/*.jsonl` | Sample snapshots of Notion / Calendar / Todoist. |
| `queries.sql` | The 3 cross-source queries in real Coral SQL. |
| `setup.ps1` | Real Coral setup: connect sources + bridge to your agent over MCP. |
| `agent_prompt.md` | System prompt that keeps the agent grounded + token-efficient. |

## Run the local demo (zero install)

```powershell
python demo.py
```

It joins three silos in single SQL statements and prints:
- **A.** Goals in Notion with *no* time blocked on the Calendar.
- **B.** Todoist tasks due soon with *no* Calendar slot to do them.
- **C.** Today's command center — events + due tasks in one query.

## Go live with real Coral

1. Download `coral-x86_64-pc-windows-msvc.zip` from the
   [Coral releases](https://github.com/withcoral/coral/releases), unzip,
   add `coral.exe` to PATH.
2. `./setup.ps1` — connects Notion + Calendar (bundled) and Todoist
   (community spec), then bridges Coral to your agent over MCP and installs
   the discovery-first skills (`npx skills add withcoral/skills`).
3. Ask your agent: *"What goals have no time blocked this week?"*

> The `file` backend lets you point Coral at the `data/*.jsonl` snapshots for a
> fast, offline, rate-limit-free stage run — same SQL, no live API flakiness.

## Demo Highlights (for judges)

1. **One query, three silos.** A single `JOIN` answers "which goals aren't on
   my calendar?" — the join the model never has to do in its head.
2. **3 tool calls -> 1.** Naive agents fetch each source separately and merge
   in-context; Coral merges in the runtime and returns the answer.
3. **Benchmarked:** Coral reports **20% more accurate, 2x more cost-efficient,
   42% lower latency** vs. direct provider MCPs.
4. **Local-first & private:** data, credentials, and history never leave the
   machine.
5. **Zero glue code:** we wrote SQL, not 3 API integrations — Coral handles
   auth, pagination, and rate limits.
6. **Grounded by design:** every agent answer shows the SQL it ran and the
   rows it returned — no hallucinated tasks.

## Architecture

```
  Notion ─┐
Calendar ─┼─►  Coral runtime  ──(SQL)──►  Agent (Claude Code / Cursor)
 Todoist ─┘    auth+joins+limits           over MCP
```

## Honest scope notes

- These sources share no foreign keys, so joins are on **dates** and **text
  overlap** (`event.summary LIKE '%' || project.name || '%'`). That's the real
  unified-context story.
- Gmail / YouTube / Readwise are **not** available in Coral yet — they'd need
  custom YAML source specs. Out of MVP scope.
- `demo.py` simulates Coral's SQL-over-silos behavior locally with sqlite so
  you can run it with no accounts; production swaps in the real `coral` runtime.
```
