"""The settings file: round-trip, one key never erasing another, and falling back when it is missing or broken."""

import json

import pytest

from app.repositories import settings_store


def test_missing_file_means_no_folders(isolated_settings):
    assert settings_store.load_worktree_folders() == ()


def test_round_trip(isolated_settings):
    settings_store.save_worktree_folders([".trees", "tools/wt"])
    assert settings_store.load_worktree_folders() == (".trees", "tools/wt")
    assert json.loads(isolated_settings.read_text(encoding="utf-8")) == {"worktree_folders": [".trees", "tools/wt"]}
    assert not isolated_settings.with_name("settings.json.tmp").exists()


def test_saving_again_replaces_the_list(isolated_settings):
    settings_store.save_worktree_folders([".trees"])
    settings_store.load_worktree_folders()
    settings_store.save_worktree_folders([])
    assert settings_store.load_worktree_folders() == ()


def test_corrupt_json_means_no_folders(isolated_settings):
    isolated_settings.write_text("{not json", encoding="utf-8")
    assert settings_store.load_worktree_folders() == ()


def test_wrong_shape_means_no_folders(isolated_settings):
    isolated_settings.write_text(json.dumps(["a"]), encoding="utf-8")
    assert settings_store.load_worktree_folders() == ()
    isolated_settings.write_text(json.dumps({"worktree_folders": "a"}), encoding="utf-8")
    assert settings_store.load_worktree_folders() == ()


def test_hand_edited_entries_are_normalised_and_bad_ones_skipped(isolated_settings):
    isolated_settings.write_text(
        json.dumps({"worktree_folders": ["tools\\wt\\", "../x", 3, ".trees", ".trees/"]}), encoding="utf-8"
    )
    assert settings_store.load_worktree_folders() == ("tools/wt", ".trees")


def test_default_path_is_under_api_ledger(monkeypatch):
    monkeypatch.delenv("LEDGER_SETTINGS_PATH")
    path = settings_store.settings_path()
    assert path.parts[-3:] == ("api", ".ledger", "settings.json")


def test_max_projects_defaults_to_five_when_the_file_is_missing(isolated_settings):
    assert settings_store.load_max_projects() == 5


def test_max_projects_round_trip(isolated_settings):
    settings_store.save_max_projects(3)
    assert settings_store.load_max_projects() == 3


def test_saving_folders_keeps_max_projects_and_the_other_way_round(isolated_settings):
    settings_store.save_max_projects(3)
    settings_store.save_worktree_folders([".trees"])
    assert settings_store.load_max_projects() == 3
    assert settings_store.load_worktree_folders() == (".trees",)

    settings_store.save_max_projects(7)
    assert settings_store.load_worktree_folders() == (".trees",)
    assert settings_store.load_max_projects() == 7


def test_unknown_keys_survive_a_save(isolated_settings):
    isolated_settings.write_text(json.dumps({"future_key": {"a": 1}}), encoding="utf-8")
    settings_store.save_max_projects(3)
    assert json.loads(isolated_settings.read_text(encoding="utf-8")) == {
        "future_key": {"a": 1}, "widget_max_projects": 3
    }


@pytest.mark.parametrize("stored", [0, 11, 2.5, True, "3", None, [3]])
def test_an_invalid_stored_max_projects_reads_as_the_default(isolated_settings, stored):
    isolated_settings.write_text(json.dumps({"widget_max_projects": stored}), encoding="utf-8")
    assert settings_store.load_max_projects() == 5


def test_afk_minutes_defaults_to_thirty_when_the_file_is_missing(isolated_settings):
    assert settings_store.load_afk_minutes() == 30


def test_afk_minutes_round_trip(isolated_settings):
    settings_store.save_afk_minutes(10)
    assert settings_store.load_afk_minutes() == 10


def test_afk_minutes_survive_a_restart(isolated_settings, monkeypatch):
    settings_store.save_afk_minutes(10)
    # A restart is a new process: nothing cached, only the file.
    monkeypatch.setattr(settings_store, "_cache", None)
    assert settings_store.load_afk_minutes() == 10


def test_saving_afk_minutes_keeps_folders_and_max_projects_and_the_other_way_round(isolated_settings):
    settings_store.save_afk_minutes(10)
    settings_store.save_max_projects(3)
    settings_store.save_worktree_folders([".trees"])
    assert settings_store.load_afk_minutes() == 10
    assert settings_store.load_max_projects() == 3

    settings_store.save_afk_minutes(60)
    assert settings_store.load_max_projects() == 3
    assert settings_store.load_worktree_folders() == (".trees",)
    assert settings_store.load_afk_minutes() == 60


@pytest.mark.parametrize("stored", [0, 241, 7.5, True, "30", None, [30]])
def test_an_invalid_stored_afk_minutes_reads_as_the_default(isolated_settings, stored):
    isolated_settings.write_text(json.dumps({"widget_afk_minutes": stored}), encoding="utf-8")
    assert settings_store.load_afk_minutes() == 30


def test_break_minutes_defaults_to_sixty_when_the_file_is_missing(isolated_settings):
    assert settings_store.load_break_minutes() == 60


def test_break_minutes_round_trip(isolated_settings):
    settings_store.save_break_minutes(45)
    assert settings_store.load_break_minutes() == 45


def test_break_minutes_survive_a_restart(isolated_settings, monkeypatch):
    settings_store.save_break_minutes(45)
    monkeypatch.setattr(settings_store, "_cache", None)
    assert settings_store.load_break_minutes() == 45


def test_saving_break_minutes_keeps_the_other_settings_and_the_other_way_round(isolated_settings):
    settings_store.save_break_minutes(45)
    settings_store.save_afk_minutes(10)
    settings_store.save_max_projects(3)
    settings_store.save_worktree_folders([".trees"])
    assert settings_store.load_break_minutes() == 45

    settings_store.save_break_minutes(90)
    assert settings_store.load_afk_minutes() == 10
    assert settings_store.load_max_projects() == 3
    assert settings_store.load_worktree_folders() == (".trees",)
    assert settings_store.load_break_minutes() == 90


@pytest.mark.parametrize("stored", [0, 241, 7.5, True, "60", None, [60]])
def test_an_invalid_stored_break_minutes_reads_as_the_default(isolated_settings, stored):
    isolated_settings.write_text(json.dumps({"widget_break_minutes": stored}), encoding="utf-8")
    assert settings_store.load_break_minutes() == 60
