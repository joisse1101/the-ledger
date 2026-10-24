"""A project's sessions include the ones that ran in its Claude Code worktrees."""

from app.repositories import claude_transcripts, settings_store
from app.repositories.db import history, paths, queries, scanner, snapshot

REPO = "/home/x/the-ledger"
OTHER = "/home/x/other"


def _write_session(isolated_db, write_transcript, started_in: str, session_id: str, cwds: list[str]):
    path = isolated_db / "projects" / paths.sanitize_project_path(started_in) / f"{session_id}.jsonl"
    lines = [
        {"type": "user", "timestamp": f"2024-01-01T10:0{i}:00Z", "cwd": cwd, "sessionId": session_id}
        for i, cwd in enumerate(cwds)
    ]
    write_transcript(path, lines)
    return path


def test_observed_data_shape_resolves_to_one_project(isolated_db, write_config, write_transcript):
    """One worktree used to show up as `add-wiki-docs`, `api` and `the-ledger`."""
    write_config(isolated_db / "claude.json", {})
    worktree = f"{REPO}/.claude/worktrees/add-wiki-docs"
    for session_id, cwds in {
        "root": [worktree],
        "sub": [worktree, f"{worktree}/api"],
        "out": [worktree, REPO],
    }.items():
        _write_session(isolated_db, write_transcript, worktree, session_id, cwds)
    snapshot.refresh()

    transcripts = claude_transcripts.load_transcripts()
    assert {t.project for t in transcripts} == {"the-ledger"}
    assert {t.worktree for t in transcripts} == {"add-wiki-docs"}
    assert {t.project_folder for t in transcripts} == {paths.sanitize_project_path(REPO)}


def test_delete_project_removes_worktree_sessions_and_leaves_other_projects(
    isolated_db, write_config, write_transcript
):
    write_config(isolated_db / "claude.json", {})
    worktree = f"{REPO}/.claude/worktrees/fix"
    other_worktree = f"{OTHER}/.claude/worktrees/fix"
    own = _write_session(isolated_db, write_transcript, REPO, "own", [REPO])
    inside = _write_session(isolated_db, write_transcript, worktree, "inside", [worktree])
    foreign = _write_session(isolated_db, write_transcript, other_worktree, "foreign", [other_worktree])
    snapshot.refresh()
    history.upsert_history_transcripts(scanner.scan_transcripts({}))

    removed_dirs = claude_transcripts.delete_project_transcripts(REPO)

    assert removed_dirs == 2
    assert not own.parent.exists() and not inside.parent.exists()
    assert foreign.exists()
    assert [t.session_id for t in claude_transcripts.load_transcripts()] == ["foreign"]
    assert [r["session_id"] for r in history.fetch_history_transcripts()] == ["foreign"]


def test_delete_project_keeps_a_folder_that_also_holds_another_projects_session(
    isolated_db, write_config, write_transcript
):
    write_config(isolated_db / "claude.json", {})
    worktree = f"{REPO}/.claude/worktrees/fix"
    inside = _write_session(isolated_db, write_transcript, worktree, "inside", [worktree])
    stray = _write_session(isolated_db, write_transcript, worktree, "stray", [OTHER])
    snapshot.refresh()

    assert [p.name for p in queries.transcript_paths_for_project(REPO)] == ["inside.jsonl"]
    assert queries.transcript_dirs_for_project(REPO) == set()
    assert inside.exists() and stray.exists()


def test_configured_folder_sessions_belong_to_the_repo(isolated_db, write_config, write_transcript):
    settings_store.save_worktree_folders([".trees"])
    write_config(isolated_db / "claude.json", {})
    worktree = f"{REPO}/.trees/fix-nav"
    _write_session(isolated_db, write_transcript, worktree, "inside", [worktree, f"{worktree}/web"])
    snapshot.refresh()

    (transcript,) = claude_transcripts.load_transcripts()
    assert (transcript.project, transcript.worktree) == ("the-ledger", "fix-nav")
    assert transcript.project_folder == paths.sanitize_project_path(REPO)


def test_delete_project_removes_configured_folder_worktree_sessions(isolated_db, write_config, write_transcript):
    settings_store.save_worktree_folders([".trees"])
    write_config(isolated_db / "claude.json", {})
    worktree = f"{REPO}/.trees/fix-nav"
    own = _write_session(isolated_db, write_transcript, REPO, "own", [REPO])
    inside = _write_session(isolated_db, write_transcript, worktree, "inside", [worktree])
    foreign = _write_session(isolated_db, write_transcript, f"{OTHER}/.trees/fix", "foreign", [f"{OTHER}/.trees/fix"])
    snapshot.refresh()
    history.upsert_history_transcripts(scanner.scan_transcripts({}))

    assert claude_transcripts.delete_project_transcripts(REPO) == 2
    assert not own.parent.exists() and not inside.parent.exists()
    assert foreign.exists()
    assert [r["session_id"] for r in history.fetch_history_transcripts()] == ["foreign"]


def test_longer_configured_folder_strips_its_own_suffix(isolated_db):
    folder = paths.sanitize_project_path(f"{REPO}/wt/inner/spike")
    assert paths.repo_folder_of_worktree(folder, "spike", ["wt", "wt/inner"]) == paths.sanitize_project_path(REPO)
