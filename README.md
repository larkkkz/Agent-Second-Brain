# second-brain-mcp

An Obsidian-style "second brain" for AI coding agents, exposed as an [MCP](https://modelcontextprotocol.io) server —
so any MCP-compatible client (Claude Code, Claude Desktop, Cursor, Windsurf, etc.) can log and recall
per-project decisions, progress, bugs, and lessons across sessions, without you having to repeat context
every time you open a new chat.

## Why

Agent sessions are forgetful — context resets between chats, and useful history (why a decision was made,
what a bug's root cause was, what's still blocked) gets lost. This gives agents a small, structured,
human-readable memory:

- Every entry type (decision, progress, bug, lesson) has a fixed schema, enforced by the tool's function
  signature — not a convention the agent has to remember to follow, so entries stay consistent no matter
  which session or agent wrote them.
- A `Router.md` per project auto-refreshes with the latest decisions/progress whenever you log something,
  so a new session gets oriented in one read instead of scanning full history.
- Recurring themes across *different* projects get promoted into a shared `Patterns.md` instead of staying
  siloed per-project.
- `search_all` finds a past entry across every project without knowing which one logged it.
- Everything is plain Markdown in a folder — browsable and editable in Obsidian (or any editor), no
  database, no lock-in.

## Setup

### Option A — one-paste installer (recommended)

Installs `uv` if needed, and registers the server in your Claude Code config automatically:

```bash
# macOS/Linux
bash <(curl -fsSL https://raw.githubusercontent.com/larkkkz/Agent-Second-Brain/main/install.sh)
```

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/larkkkz/Agent-Second-Brain/main/install.ps1 | iex
```

Vault defaults to `~/SecondBrain` — override with `SECOND_BRAIN_VAULT=/your/path` before running, or pass
it as a second argument (`bash <(curl ...) ~/.claude.json /your/vault/path`).

After it finishes: restart Claude Code, then run `/mcp` and approve the `second-brain` server the first
time it's used — that one approval step is a Claude Code security gate that applies to any MCP server, not
something an installer can (or should) skip.

### Option B — manual config edit, no cloning

Requires [`uv`](https://docs.astral.sh/uv/) (`winget install astral-sh.uv` / `brew install uv` / see their docs).
Add this to your MCP client's config yourself — no `git clone`, no `pip install`, `uv` fetches and runs it
straight from GitHub in an isolated environment:

```json
{
  "mcpServers": {
    "second-brain": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/larkkkz/Agent-Second-Brain", "second-brain-mcp"],
      "env": { "SECOND_BRAIN_VAULT": "C:\\Users\\you\\SecondBrain" }
    }
  }
}
```

If `SECOND_BRAIN_VAULT` is omitted, it defaults to `~/SecondBrain`. The vault folder is created and seeded
automatically the first time the server runs — nothing to set up by hand.

### Option C — clone and run manually

1. **Install Python 3.10+** if you don't have it.
2. Clone the repo, then install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. **Choose a vault location** (where your logs will live) and set it as an environment variable:
   ```
   # Windows (PowerShell)
   $env:SECOND_BRAIN_VAULT = "C:\Users\you\SecondBrain"

   # macOS/Linux
   export SECOND_BRAIN_VAULT=~/SecondBrain
   ```
4. **Register the server with your MCP client:**
   ```json
   {
     "mcpServers": {
       "second-brain": {
         "type": "stdio",
         "command": "python",
         "args": ["/absolute/path/to/second-brain-mcp/second_brain_mcp/server.py"],
         "env": { "SECOND_BRAIN_VAULT": "C:\\Users\\you\\SecondBrain" }
       }
     }
   }
   ```

### After either option

- Other MCP clients (Claude Desktop, Cursor, etc.) use a similar `mcpServers` config shape — check your
  client's docs for where it lives.
- Restart your MCP client so it picks up the new server.
- (Optional, Claude Code only) Copy `skills/second-brain/SKILL.md` into `~/.claude/skills/second-brain/`
  so the agent knows *when* to use the tools (install on request, log proactively, etc.) without you
  having to explain it each session.

## Tools

| Tool | Purpose |
|---|---|
| `install_project` | Create a project's Router/Current-State/journals from templates; optionally wires up `CLAUDE.md` |
| `archive_project` | Move a project to `Projects/_Archive/` and unlink it from Home.md — nothing is deleted |
| `list_projects` | List active (non-archived) projects |
| `read_router` | Read a project's quick-orientation briefing |
| `read_current_state` | Read a project's living architecture/status snapshot |
| `read_journal` | Read a full journal (Decisions/Progress/Bugs-and-Fixes/Lessons-Learned) |
| `log_decision` | Append a decision entry, auto-refresh Router |
| `log_progress` | Append a progress entry, auto-refresh Router |
| `log_bug` | Append a bug+fix entry |
| `log_lesson` | Append a lesson-learned entry |
| `update_current_state` | Overwrite specific sections of the living state snapshot |
| `set_open_blockers` / `set_unresolved_bugs` | Overwrite the live blocker/bug list in Router |
| `add_pattern` | Log a theme that's recurred across more than one project |
| `search_all` | Keyword search across every project's logs + Patterns |
| `recent_activity` | Digest of what was logged in the last N days, across projects or one |

## Vault layout

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

## License

MIT — see [LICENSE](LICENSE).
