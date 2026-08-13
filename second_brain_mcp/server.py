"""Second Brain MCP server.

Exposes an Obsidian-style "second brain" vault as MCP tools, so any MCP client
(Claude Code, Claude Desktop, Cursor, Windsurf, or any other MCP-compatible
agent) can install per-project logging and read/append to it directly —
no skill or plugin required, just the MCP connection.

Vault location: set the SECOND_BRAIN_VAULT environment variable to an
absolute path. Defaults to ~/SecondBrain if unset. The vault is created and
seeded automatically on first run.

Per-project files are named "<Project Name> - <Stem>.md" (e.g. "PmsPoC -
Router.md") rather than bare "Router.md" — this keeps Obsidian's graph view
legible, since every project would otherwise have identically-named nodes.
"""

import os
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
VAULT_SEED_DIR = PACKAGE_DIR / "vault-seed"

VAULT_ROOT = Path(os.environ.get("SECOND_BRAIN_VAULT", str(Path.home() / "SecondBrain")))
PROJECTS_DIR = VAULT_ROOT / "Projects"
HOME_FILE = VAULT_ROOT / "Home.md"
PATTERNS_FILE = VAULT_ROOT / "Patterns.md"

JOURNALS = {
    "Decisions": "Decision-Log-Template.md",
    "Progress": "Progress-Log-Template.md",
    "Bugs-and-Fixes": "Bugs-and-Fixes-Template.md",
    "Lessons-Learned": "Lessons-Learned-Template.md",
}
LIVING_FILES = {
    "Router": "Router-Template.md",
    "Current-State": "Current-State-Template.md",
}
ALL_STEMS = [*LIVING_FILES, *JOURNALS]

SECOND_BRAIN_SECTION = """## Second Brain Logging

This project logs to a central vault via the `second-brain` MCP server, project name `{project}`.
(Vault location is wherever SECOND_BRAIN_VAULT points on this machine.)

At the start of a session, call `read_router("{project}")` first for quick orientation before doing anything else.

Proactively keep the vault current (don't ask permission for routine entries, but mention briefly what you logged/updated):
- `log_decision` — when a real technical/product decision is made, especially with tradeoffs
- `log_progress` — when a work session or meaningful chunk of work wraps up
- `log_bug` — when a non-trivial bug is found and fixed
- `log_lesson` — when a mistake happens, or something non-obvious is learned
- `update_current_state` — when architecture/status/active focus changes
- `set_open_blockers` / `set_unresolved_bugs` — when the live blocker/bug list changes
- `add_pattern` — if a bug/decision/lesson here clearly echoes one already logged in a *different* project
- `search_all` — to find a past decision/bug/lesson without knowing which project logged it

Be judicious — log what future-you would actually want to find, not routine back-and-forth.
"""

mcp = MCPServer("second-brain")


def _today() -> str:
    return date.today().isoformat()


def _ensure_vault() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    if not HOME_FILE.exists():
        shutil.copy(VAULT_SEED_DIR / "Home.md", HOME_FILE)
    if not PATTERNS_FILE.exists():
        shutil.copy(VAULT_SEED_DIR / "Patterns.md", PATTERNS_FILE)


def _validate_name(name: str) -> str:
    name = name.strip()
    if not name or not re.match(r"^[A-Za-z0-9._ -]+$", name) or ".." in name:
        raise ValueError(f"Invalid project name: {name!r}")
    return name


def _project_dir(project_name: str) -> Path:
    return PROJECTS_DIR / _validate_name(project_name)


def _file(project_name: str, stem: str) -> Path:
    """Path for a project's file, using the project-prefixed naming scheme."""
    return _project_dir(project_name) / f"{project_name} - {stem}.md"


def _link(project_name: str, stem: str, display: str = None) -> str:
    """Wikilink to a project's file, aliased so the visible text stays just the stem."""
    return f"[[{project_name} - {stem}|{display or stem}]]"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _require_installed(project_name: str) -> Path:
    pdir = _project_dir(project_name)
    if not pdir.exists():
        raise ValueError(f"Project '{project_name}' is not installed. Call install_project first.")
    return pdir


def _render_template(template_file: str, project_name: str) -> str:
    text = _read(TEMPLATES_DIR / template_file)
    text = text.replace("{{Project Name}}", project_name)
    if template_file == "Current-State-Template.md":
        text = text.replace("{{YYYY-MM-DD}}", _today())
    for stem in ALL_STEMS:
        text = text.replace(f"[[{stem}]]", _link(project_name, stem))
    return text


def _append_entry(path: Path, entry_body: str) -> None:
    text = _read(path)
    if "{{" in text:
        header, _, _ = text.partition("---")
        text = header.rstrip() + "\n\n---\n"
    text = text.rstrip("\n") + "\n\n" + entry_body.strip() + "\n\n---\n"
    _write(path, text)


def _bullets(items) -> str:
    items = [i for i in (items or []) if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) if items else "-"


def _set_block_section(text: str, header: str, lines) -> str:
    """Replace the bullet block under `## {header}` up to the next `## ` or `**Full logs`/`**History` marker."""
    src_lines = text.split("\n")
    out = []
    i = 0
    n = len(src_lines)
    found = False
    body_lines = _bullets(lines).split("\n")
    while i < n:
        line = src_lines[i]
        out.append(line)
        if line.strip() == f"## {header}":
            found = True
            i += 1
            while (
                i < n
                and not src_lines[i].startswith("##")
                and not src_lines[i].startswith("**Full logs")
                and not src_lines[i].startswith("**History")
            ):
                i += 1
            out.extend(body_lines)
            out.append("")
            continue
        i += 1
    if not found:
        raise ValueError(f"Section '## {header}' not found")
    return "\n".join(out)


def _latest_headers(path: Path, limit: int = 5):
    text = _read(path)
    headers = re.findall(r"^## (.+)$", text, re.M)
    return headers[-limit:][::-1]


def _refresh_router_from_journal(project_name: str, journal: str, router_section: str) -> None:
    headers = _latest_headers(_file(project_name, journal), limit=5)
    links = [f"[[{project_name} - {journal}#{h}|{h}]]" for h in headers]
    router_path = _file(project_name, "Router")
    text = _read(router_path)
    text = _set_block_section(text, router_section, links)
    _write(router_path, text)


@mcp.tool()
def list_projects() -> list[str]:
    """List all project names currently installed in the second-brain vault."""
    _ensure_vault()
    if not PROJECTS_DIR.exists():
        return []
    return sorted(p.name for p in PROJECTS_DIR.iterdir() if p.is_dir())


@mcp.tool()
def install_project(project_name: str, project_root_path: str = "") -> dict:
    """Install second-brain logging for a project: creates its vault folder + six files
    (Router, Current-State, Decisions, Progress, Bugs-and-Fixes, Lessons-Learned) from
    templates, links it from Home.md, and (if project_root_path is given) writes/updates
    the 'Second Brain Logging' section in that project's CLAUDE.md.
    """
    _ensure_vault()
    project_name = _validate_name(project_name)
    pdir = _project_dir(project_name)
    pdir.mkdir(parents=True, exist_ok=True)

    created, existing = [], []
    all_files = {**LIVING_FILES, **JOURNALS}
    for stem, template_file in all_files.items():
        target = _file(project_name, stem)
        if target.exists():
            existing.append(target.name)
        else:
            _write(target, _render_template(template_file, project_name))
            created.append(target.name)

    home_text = _read(HOME_FILE)
    link_line = f"- [[Projects/{project_name}/{project_name} - Router|{project_name}]]"
    home_updated = False
    if link_line not in home_text:
        m = re.search(r"(## Projects\n)(.*?)(\n## )", home_text, re.S)
        if m:
            body_lines = [
                l for l in m.group(2).split("\n") if l.strip() and not l.strip().startswith("*(")
            ]
            body_lines.append(link_line)
            new_body = "\n" + "\n".join(body_lines) + "\n"
            home_text = home_text[: m.start(2)] + new_body + home_text[m.end(2) :]
            _write(HOME_FILE, home_text)
            home_updated = True

    claude_md_status = "skipped (no project_root_path given)"
    if project_root_path:
        root = Path(project_root_path)
        if not root.exists():
            claude_md_status = f"project_root_path does not exist: {project_root_path}"
        else:
            claude_md = root / "CLAUDE.md"
            section = SECOND_BRAIN_SECTION.format(project=project_name)
            if claude_md.exists():
                text = _read(claude_md)
                if "## Second Brain Logging" in text:
                    claude_md_status = "already present"
                else:
                    _write(claude_md, text.rstrip() + "\n\n" + section + "\n")
                    claude_md_status = "appended"
            else:
                _write(claude_md, section + "\n")
                claude_md_status = "created"

    return {
        "project": project_name,
        "created_files": created,
        "existing_files": existing,
        "home_updated": home_updated,
        "claude_md": claude_md_status,
    }


@mcp.tool()
def read_router(project_name: str) -> str:
    """Read a project's Router.md — the quick-orientation briefing. Read this first each session."""
    _require_installed(project_name)
    return _read(_file(project_name, "Router"))


@mcp.tool()
def read_current_state(project_name: str) -> str:
    """Read a project's Current-State.md — the living architecture/status snapshot."""
    _require_installed(project_name)
    return _read(_file(project_name, "Current-State"))


@mcp.tool()
def read_journal(project_name: str, journal: str) -> str:
    """Read a full journal file for a project. journal must be one of:
    Decisions, Progress, Bugs-and-Fixes, Lessons-Learned.
    """
    if journal not in JOURNALS:
        raise ValueError(f"journal must be one of {list(JOURNALS)}")
    _require_installed(project_name)
    return _read(_file(project_name, journal))


@mcp.tool()
def log_decision(
    project_name: str, title: str, context: str, decision: str, why: str, alternatives: str = ""
) -> str:
    """Append a dated decision entry to a project's Decisions.md and refresh its Router."""
    _require_installed(project_name)
    entry = (
        f"## {_today()} — {title}\n\n"
        f"**Context:** {context}\n\n"
        f"**Decision:** {decision}\n\n"
        f"**Why:** {why}\n\n"
        f"**Alternatives considered:** {alternatives or '—'}\n\n"
        f"**Related:** {_link(project_name, 'Progress')} · {_link(project_name, 'Bugs-and-Fixes')} · #decision"
    )
    _append_entry(_file(project_name, "Decisions"), entry)
    _refresh_router_from_journal(project_name, "Decisions", "Recent decisions")
    return f"Logged decision '{title}' for {project_name}."


@mcp.tool()
def log_progress(
    project_name: str,
    done: list[str],
    blocked: Optional[list[str]] = None,
    next_steps: Optional[list[str]] = None,
) -> str:
    """Append a dated progress entry to a project's Progress.md and refresh its Router."""
    _require_installed(project_name)
    entry = (
        f"## {_today()}\n\n"
        f"**Done:**\n{_bullets(done)}\n\n"
        f"**Blocked:**\n{_bullets(blocked)}\n\n"
        f"**Next:**\n{_bullets(next_steps)}\n\n"
        f"**Related:** {_link(project_name, 'Decisions')} · {_link(project_name, 'Bugs-and-Fixes')} · #progress"
    )
    _append_entry(_file(project_name, "Progress"), entry)
    _refresh_router_from_journal(project_name, "Progress", "Recent progress")
    return f"Logged progress for {project_name}."


@mcp.tool()
def log_bug(project_name: str, title: str, symptom: str, root_cause: str, fix: str, prevention: str = "") -> str:
    """Append a dated bug+fix entry to a project's Bugs-and-Fixes.md."""
    _require_installed(project_name)
    entry = (
        f"## {_today()} — {title}\n\n"
        f"**Symptom:** {symptom}\n\n"
        f"**Root cause:** {root_cause}\n\n"
        f"**Fix:** {fix}\n\n"
        f"**Prevention:** {prevention or '—'}\n\n"
        f"**Related:** {_link(project_name, 'Decisions')} · {_link(project_name, 'Lessons-Learned')} · #bug"
    )
    _append_entry(_file(project_name, "Bugs-and-Fixes"), entry)
    return f"Logged bug '{title}' for {project_name}."


@mcp.tool()
def log_lesson(project_name: str, title: str, what_happened: str, lesson: str, apply_next_time: str) -> str:
    """Append a dated lesson-learned entry to a project's Lessons-Learned.md."""
    _require_installed(project_name)
    entry = (
        f"## {_today()} — {title}\n\n"
        f"**What happened:** {what_happened}\n\n"
        f"**Lesson:** {lesson}\n\n"
        f"**Apply next time:** {apply_next_time}\n\n"
        f"**Related:** {_link(project_name, 'Bugs-and-Fixes')} · {_link(project_name, 'Decisions')} · #lesson"
    )
    _append_entry(_file(project_name, "Lessons-Learned"), entry)
    return f"Logged lesson '{title}' for {project_name}."


@mcp.tool()
def update_current_state(
    project_name: str,
    architecture: Optional[list[str]] = None,
    key_components: Optional[list[str]] = None,
    limitations: Optional[list[str]] = None,
    active_focus: Optional[list[str]] = None,
) -> str:
    """Overwrite sections of a project's Current-State.md. Pass only the sections that changed;
    omitted sections (left as None) are unchanged. This file is living truth, not a log.
    """
    _require_installed(project_name)
    path = _file(project_name, "Current-State")
    text = _read(path)
    text = re.sub(r"\*\*Last updated:\*\* .*", f"**Last updated:** {_today()}", text)
    if architecture is not None:
        text = _set_block_section(text, "Architecture", architecture)
    if key_components is not None:
        text = _set_block_section(text, "Key components", key_components)
    if limitations is not None:
        text = _set_block_section(text, "Known limitations / tech debt", limitations)
    if active_focus is not None:
        text = _set_block_section(text, "Active focus", active_focus)
    _write(path, text)
    return f"Updated Current-State for {project_name}."


@mcp.tool()
def set_open_blockers(project_name: str, blockers: list[str]) -> str:
    """Overwrite the 'Open blockers' list in a project's Router.md."""
    _require_installed(project_name)
    path = _file(project_name, "Router")
    _write(path, _set_block_section(_read(path), "Open blockers", blockers))
    return f"Updated open blockers for {project_name}."


@mcp.tool()
def set_unresolved_bugs(project_name: str, bugs: list[str]) -> str:
    """Overwrite the 'Unresolved bugs' list in a project's Router.md."""
    _require_installed(project_name)
    path = _file(project_name, "Router")
    _write(path, _set_block_section(_read(path), "Unresolved bugs", bugs))
    return f"Updated unresolved bugs for {project_name}."


@mcp.tool()
def add_pattern(title: str, seen_in: list[str], pattern: str, recommendation: str) -> str:
    """Append a cross-project pattern to the vault-root Patterns.md. Only use once the same
    bug/decision/lesson theme has shown up in more than one project.
    """
    _ensure_vault()
    seen_links = ", ".join(f"[[Projects/{p}/{p} - Bugs-and-Fixes|{p}]]" for p in seen_in)
    entry = (
        f"## {_today()} — {title}\n\n"
        f"**Seen in:** {seen_links}\n\n"
        f"**Pattern:** {pattern}\n\n"
        f"**Recommendation:** {recommendation}\n\n"
        f"**Related:** #pattern"
    )
    _append_entry(PATTERNS_FILE, entry)
    return f"Logged pattern '{title}'."


@mcp.tool()
def search_all(query: str, project_name: str = "", limit: int = 20) -> list[dict]:
    """Search every project's Router/Current-State/journals (and the vault-root Patterns.md)
    for a keyword or phrase. Returns matching entries with project, file, header, and a snippet.
    Use this to find a past decision/bug/lesson without knowing which project logged it —
    pass project_name to scope the search to one project instead of the whole vault.
    """
    _ensure_vault()
    query_lower = query.lower()
    results = []

    def scan_file(path: Path, project_label: str, file_label: str):
        if not path.exists():
            return
        text = _read(path)
        entries = re.split(r"(?=^## )", text, flags=re.M)
        for entry in entries:
            if not entry.startswith("## ") or query_lower not in entry.lower():
                continue
            header = entry.splitlines()[0][3:].strip()
            snippet = entry.strip()
            if len(snippet) > 400:
                snippet = snippet[:400].rsplit(" ", 1)[0] + "…"
            results.append(
                {"project": project_label, "file": file_label, "header": header, "snippet": snippet}
            )

    names = [_validate_name(project_name)] if project_name else list_projects()
    for name in names:
        for stem in ALL_STEMS:
            scan_file(_file(name, stem), name, stem)

    if not project_name:
        scan_file(PATTERNS_FILE, "(vault-wide)", "Patterns")

    return results[:limit]


@mcp.tool()
def recent_activity(days: int = 7, project_name: str = "") -> list[dict]:
    """Digest of what happened recently across projects: decisions, progress, bugs, and lessons
    logged in the last `days` days, newest first. Pass project_name to scope to one project
    instead of the whole vault. Use this for a "what happened recently" summary instead of
    reading each project's Router individually.
    """
    _ensure_vault()
    cutoff = date.today() - timedelta(days=days)
    results = []

    def scan(path: Path, project_label: str, journal_label: str):
        if not path.exists():
            return
        text = _read(path)
        entries = re.split(r"(?=^## )", text, flags=re.M)
        for entry in entries:
            if not entry.startswith("## "):
                continue
            m = re.match(r"## (\d{4}-\d{2}-\d{2})(?:\s*—\s*(.*))?", entry.splitlines()[0])
            if not m:
                continue
            try:
                entry_date = date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if entry_date < cutoff:
                continue
            snippet = entry.strip()
            if len(snippet) > 400:
                snippet = snippet[:400].rsplit(" ", 1)[0] + "…"
            results.append(
                {
                    "project": project_label,
                    "journal": journal_label,
                    "date": entry_date.isoformat(),
                    "title": m.group(2) or "",
                    "snippet": snippet,
                }
            )

    names = [_validate_name(project_name)] if project_name else list_projects()
    for name in names:
        for journal in JOURNALS:
            scan(_file(name, journal), name, journal)

    results.sort(key=lambda r: r["date"], reverse=True)
    return results


_ensure_vault()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
