import importlib

import pytest


@pytest.fixture
def server(tmp_path, monkeypatch):
    """A fresh, isolated second_brain_mcp.server module pointed at a throwaway vault."""
    monkeypatch.setenv("SECOND_BRAIN_VAULT", str(tmp_path))
    import second_brain_mcp.server as mod

    importlib.reload(mod)
    return mod


def test_install_project_creates_all_six_files(server):
    result = server.install_project("Demo")
    assert set(result["created_files"]) == {
        "Demo - Router.md",
        "Demo - Current-State.md",
        "Demo - Decisions.md",
        "Demo - Progress.md",
        "Demo - Bugs-and-Fixes.md",
        "Demo - Lessons-Learned.md",
    }
    assert result["existing_files"] == []
    assert result["home_updated"] is True


def test_install_project_does_not_overwrite_existing(server):
    server.install_project("Demo")
    router_path = server._file("Demo", "Router")
    router_path.write_text("custom content", encoding="utf-8")

    result = server.install_project("Demo")

    assert "Demo - Router.md" in result["existing_files"]
    assert router_path.read_text(encoding="utf-8") == "custom content"


def test_install_project_links_home(server):
    server.install_project("Demo")
    home_text = server._read(server.HOME_FILE)
    assert "[[Projects/Demo/Demo - Router|Demo]]" in home_text


def test_set_block_section_keeps_blank_line_before_next_header(server):
    text = "## Open blockers\n-\n\n## Unresolved bugs\n-\n"
    new_text = server._set_block_section(text, "Open blockers", ["Waiting on review"])
    lines = new_text.split("\n")
    blocker_idx = lines.index("- Waiting on review")
    assert lines[blocker_idx + 1] == ""
    assert lines[blocker_idx + 2] == "## Unresolved bugs"


def test_set_block_section_before_full_logs_marker(server):
    text = "## Recent progress\n-\n\n**Full logs:** [[x]]"
    new_text = server._set_block_section(text, "Recent progress", ["2026-01-01"])
    assert "- 2026-01-01\n\n**Full logs:**" in new_text


def test_log_decision_appends_and_refreshes_router(server):
    server.install_project("Demo")
    server.log_decision("Demo", "Use SQLite", "Needed local cache", "Use SQLite", "Simple")

    decisions = server.read_journal("Demo", "Decisions")
    assert "Use SQLite" in decisions
    assert "[[Demo - Progress|Progress]]" in decisions

    router = server.read_router("Demo")
    assert "Demo - Decisions#" in router
    assert "Use SQLite" in router


def test_log_progress_appends_and_refreshes_router(server):
    server.install_project("Demo")
    server.log_progress("Demo", ["Did a thing"], ["Blocked on review"], ["Next thing"])

    progress = server.read_journal("Demo", "Progress")
    assert "Did a thing" in progress
    assert "Blocked on review" in progress

    router = server.read_router("Demo")
    assert "Demo - Progress#" in router


def test_log_bug_appends(server):
    server.install_project("Demo")
    server.log_bug("Demo", "Cache never expired", "Entries never evicted", "TTL never set", "Added TTL")
    bugs = server.read_journal("Demo", "Bugs-and-Fixes")
    assert "Cache never expired" in bugs
    assert "[[Demo - Lessons-Learned|Lessons-Learned]]" in bugs


def test_log_lesson_appends(server):
    server.install_project("Demo")
    server.log_lesson("Demo", "Test expiry", "Shipped without a test", "Needs explicit tests", "Add test")
    lessons = server.read_journal("Demo", "Lessons-Learned")
    assert "Test expiry" in lessons


def test_update_current_state_overwrites_only_given_sections(server):
    server.install_project("Demo")
    server.update_current_state("Demo", architecture=["SQLite cache added"])
    state = server.read_current_state("Demo")
    assert "SQLite cache added" in state
    assert "## Key components\n-" in state


def test_set_open_blockers_and_unresolved_bugs(server):
    server.install_project("Demo")
    server.set_open_blockers("Demo", ["Waiting on DBA"])
    server.set_unresolved_bugs("Demo", ["Slow report query"])
    router = server.read_router("Demo")
    assert "Waiting on DBA" in router
    assert "Slow report query" in router


def test_add_pattern_links_real_projects(server):
    server.install_project("Alpha")
    server.install_project("Beta")
    server.add_pattern("Forgot TTL", ["Alpha", "Beta"], "TTL keeps getting forgotten", "Add to checklist")
    patterns = server._read(server.PATTERNS_FILE)
    assert "[[Projects/Alpha/Alpha - Bugs-and-Fixes|Alpha]]" in patterns
    assert "[[Projects/Beta/Beta - Bugs-and-Fixes|Beta]]" in patterns


def test_search_all_finds_match_across_projects(server):
    server.install_project("Alpha")
    server.install_project("Beta")
    server.log_bug("Alpha", "Cache bug", "cache never expired", "no ttl", "added ttl")

    results = server.search_all("cache")
    assert any(r["project"] == "Alpha" for r in results)
    assert not any(r["project"] == "Beta" for r in results)


def test_search_all_scoped_to_project(server):
    server.install_project("Alpha")
    server.install_project("Beta")
    server.log_bug("Alpha", "Cache bug", "cache never expired", "no ttl", "added ttl")
    server.log_bug("Beta", "Cache bug too", "cache never expired here too", "no ttl", "added ttl")

    results = server.search_all("cache", project_name="Alpha")
    assert all(r["project"] == "Alpha" for r in results)


def test_search_all_no_match_returns_empty(server):
    server.install_project("Alpha")
    assert server.search_all("nonexistentterm12345") == []


def test_recent_activity_includes_todays_entry(server):
    server.install_project("Alpha")
    server.log_decision("Alpha", "Use SQLite", "context", "decision", "why")

    results = server.recent_activity(days=7)
    assert any(r["project"] == "Alpha" and "Use SQLite" in r["title"] for r in results)


def test_recent_activity_excludes_entries_outside_window(server):
    import datetime

    server.install_project("Alpha")
    server.log_decision("Alpha", "Recent one", "context", "decision", "why")

    old_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    path = server._file("Alpha", "Decisions")
    text = server._read(path)
    text = text.rstrip("\n") + f"\n\n## {old_date} — Ancient decision\n\n**Context:** old\n\n---\n"
    server._write(path, text)

    results = server.recent_activity(days=7)
    titles = [r["title"] for r in results]
    assert "Recent one" in titles
    assert "Ancient decision" not in titles


def test_recent_activity_scoped_to_project(server):
    server.install_project("Alpha")
    server.install_project("Beta")
    server.log_decision("Alpha", "Alpha decision", "context", "decision", "why")
    server.log_decision("Beta", "Beta decision", "context", "decision", "why")

    results = server.recent_activity(days=7, project_name="Alpha")
    assert all(r["project"] == "Alpha" for r in results)


def test_recent_activity_sorted_newest_first(server):
    import datetime

    server.install_project("Alpha")
    server.log_decision("Alpha", "Today decision", "context", "decision", "why")

    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    path = server._file("Alpha", "Progress")
    text = server._read(path)
    text = text.rstrip("\n") + f"\n\n## {yesterday}\n\n**Done:**\n- something\n\n---\n"
    server._write(path, text)

    results = server.recent_activity(days=7)
    dates = [r["date"] for r in results]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.parametrize("bad_name", ["../escape", "a/b", "a\\b", "..", "   ", ""])
def test_validate_name_rejects_path_traversal_and_invalid(server, bad_name):
    with pytest.raises(ValueError):
        server._validate_name(bad_name)


def test_require_installed_raises_for_unknown_project(server):
    with pytest.raises(ValueError):
        server.read_router("DoesNotExist")


def test_render_template_prefixes_bare_links(server):
    text = server._render_template("Router-Template.md", "Demo")
    assert "[[Demo - Decisions|Decisions]]" in text
    assert "[[Decisions]]" not in text


def test_ensure_vault_seeds_home_and_patterns(server):
    assert server.HOME_FILE.exists()
    assert server.PATTERNS_FILE.exists()
    assert "{{" in server._read(server.PATTERNS_FILE)


def test_list_projects_empty_then_populated(server):
    assert server.list_projects() == []
    server.install_project("Demo")
    assert server.list_projects() == ["Demo"]


def test_archive_project_moves_folder_and_removes_from_list(server):
    server.install_project("Demo")
    pdir = server._project_dir("Demo")
    assert pdir.exists()

    result = server.archive_project("Demo")

    assert not pdir.exists()
    archived = server.PROJECTS_DIR / server.ARCHIVE_DIRNAME / "Demo"
    assert archived.exists()
    assert (archived / "Demo - Router.md").exists()
    assert "Demo" not in server.list_projects()
    assert "Archived" in result


def test_archive_project_removes_home_link(server):
    server.install_project("Demo")
    assert "[[Projects/Demo/Demo - Router|Demo]]" in server._read(server.HOME_FILE)

    server.archive_project("Demo")

    assert "[[Projects/Demo/Demo - Router|Demo]]" not in server._read(server.HOME_FILE)


def test_archive_project_raises_if_not_installed(server):
    with pytest.raises(ValueError):
        server.archive_project("DoesNotExist")


def test_archive_project_raises_if_already_archived(server):
    server.install_project("Demo")
    server.archive_project("Demo")
    server.install_project("Demo")

    with pytest.raises(ValueError):
        server.archive_project("Demo")


def test_archived_project_excluded_from_search_and_activity(server):
    server.install_project("Demo")
    server.log_decision("Demo", "Some decision", "context", "decision", "why")
    server.archive_project("Demo")

    assert server.search_all("decision") == []
    assert server.recent_activity(days=7) == []


def test_project_name_cannot_be_reserved_archive_name(server):
    with pytest.raises(ValueError):
        server.install_project("_Archive")


def test_list_archived_projects_empty_then_populated(server):
    assert server.list_archived_projects() == []
    server.install_project("Demo")
    server.archive_project("Demo")
    assert server.list_archived_projects() == ["Demo"]


def test_delete_archived_project_removes_folder(server):
    server.install_project("Demo")
    server.archive_project("Demo")
    archived = server.PROJECTS_DIR / server.ARCHIVE_DIRNAME / "Demo"
    assert archived.exists()

    result = server.delete_archived_project("Demo", confirm_name="Demo")

    assert not archived.exists()
    assert server.list_archived_projects() == []
    assert "Permanently deleted" in result


def test_delete_archived_project_requires_exact_confirm_match(server):
    server.install_project("Demo")
    server.archive_project("Demo")

    with pytest.raises(ValueError):
        server.delete_archived_project("Demo", confirm_name="demo")

    with pytest.raises(ValueError):
        server.delete_archived_project("Demo", confirm_name="Dem")

    # nothing was deleted by the failed attempts
    assert server.list_archived_projects() == ["Demo"]


def test_delete_archived_project_raises_if_not_archived(server):
    server.install_project("Demo")
    with pytest.raises(ValueError):
        server.delete_archived_project("Demo", confirm_name="Demo")


def test_delete_archived_project_raises_if_unknown(server):
    with pytest.raises(ValueError):
        server.delete_archived_project("NeverExisted", confirm_name="NeverExisted")
