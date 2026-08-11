---
name: second-brain
description: Installs automatic project logging via the second-brain MCP server. Use when the user says "install second brain", "set up second brain", "install the second brain here", or asks to auto-log decisions/progress/bugs/mistakes for the current project. Also use ongoing (without being asked) once installed — read the project's Router at the start of a session, and log significant decisions, progress checkpoints, bug fixes, and lessons learned as they happen.
---

# Second Brain — project logging

This skill assumes the `second-brain` MCP server (from this repo's `server.py`) is already registered
with your MCP client. See the repo README for setup. Once registered, this skill just tells the agent
when to call which tool — it does not read/write vault files directly.

The vault holds logs for every project on this machine, at whatever path `SECOND_BRAIN_VAULT` points to:

```
<vault>/
├── Home.md
├── Patterns.md
└── Projects/
    └── <ProjectName>/
        ├── Router.md
        ├── Current-State.md
        ├── Decisions.md
        ├── Progress.md
        ├── Bugs-and-Fixes.md
        └── Lessons-Learned.md
```

- **Router.md** — read this first each session (`read_router`). A short, kept-in-sync briefing (open blockers, unresolved bugs, recent decisions/progress).
- **Current-State.md** — a living snapshot of the project's architecture/status (`read_current_state`, `update_current_state`). Overwritten as things change, not a log.
- **Decisions / Progress / Bugs-and-Fixes / Lessons-Learned** — append-only journals via `log_decision`, `log_progress`, `log_bug`, `log_lesson`.
- **Patterns.md** (vault root) — recurring bugs/decisions/lessons seen in more than one project, via `add_pattern`. Only add once a theme repeats across projects.
- **search_all** — find a past entry anywhere in the vault without knowing which project logged it.

This skill has two parts: **installing** logging into a project, and **ongoing logging** once installed.

## Installing into a project

Run this when the user asks to "install second brain" (or equivalent) in the current project.

1. Determine the project name from the current working directory's folder name. If it's generic (e.g. `src`, `app`), ask the user for a clearer project name instead of guessing.
2. Call the `install_project` MCP tool with that name, and pass the current project's root path as `project_root_path` so the tool can also wire up `CLAUDE.md` there.
3. Confirm to the user: which files were created vs. already existed, and that logging is now active for this project.

## Ongoing logging (after install)

- Read `Router.md` (via `read_router`) at the start of a session for orientation.
- Call `log_decision` / `log_progress` / `log_bug` / `log_lesson` as real decisions, progress checkpoints, bugs/fixes, or lessons occur — without waiting to be asked.
- Call `update_current_state`, `set_open_blockers`, `set_unresolved_bugs` as things change — these are living state, not logs.
- Call `add_pattern` when a repeated theme across projects has shown up a second time.
- Use `search_all` when you need to find something and don't remember which project it was logged under.
- Keep entries concise and judicious; don't log routine conversation.
