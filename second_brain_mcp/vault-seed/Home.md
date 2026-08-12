# 🧠 Second Brain — Home

Central knowledge base for all projects. Each project gets its own folder under `Projects/` with six linked files: a Router (session briefing), Current State (living snapshot), and four journals — Decisions, Progress, Bugs & Fixes, and Lessons Learned.

## Projects

*(links appear here as projects are installed via the `install_project` MCP tool)*

## Cross-project

- [[Patterns]] — recurring bugs/decisions/lessons seen across more than one project

## How this works

- A dedicated MCP server (`second-brain-mcp`) exposes this vault as tools — `install_project`, `log_decision`, `log_progress`, `log_bug`, `log_lesson`, `update_current_state`, `set_open_blockers`, `set_unresolved_bugs`, `add_pattern`, `read_router`, `read_current_state`, `read_journal`, `list_projects`, `search_all` — available to any MCP-compatible agent, in any project, once the server is registered.
- `search_all` greps every project's Router/Current-State/journals plus vault-wide `Patterns.md` for a keyword — find a past decision/bug/lesson without knowing which project logged it.
- In any project, ask your agent to "install second brain" (or call `install_project` directly) to wire up logging for that project.
- Each session, the agent should read that project's `Router.md` first for quick orientation (open blockers, unresolved bugs, recent activity).
- From then on, the agent proactively logs to this vault as work happens:
  - **Decisions** — what was decided and why
  - **Progress** — what got done, what's blocked, what's next
  - **Bugs & Fixes** — issues hit and how they were resolved
  - **Lessons Learned** — mistakes and knowledge worth remembering
  - **Current State** — kept up to date (overwritten, not appended) as architecture/status changes
  - **Router** — kept in sync with the latest few items from each journal
- If the same bug/decision/lesson shows up in a second project, it gets promoted to [[Patterns]] instead of staying siloed.
- Entries use `[[wikilinks]]` and `#tags` so Obsidian's graph view and backlinks surface how decisions, bugs, and lessons connect across time and across projects.
