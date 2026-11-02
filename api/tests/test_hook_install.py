"""hooks/Install-ClaudeHooks.ps1 and Uninstall-ClaudeHooks.ps1 -IncludeSessionControl, run for real.

Both scripts resolve everything from $env:USERPROFILE, so each test points USERPROFILE at a throwaway
folder: the real ~/.claude/settings.json is never read or written. Only the `-SkipToastHooks` paths
are exercised, because the toast install also writes the machine's real HKCU claudecode:// handler.

Guards the promises of the relay hook's install story: it goes in as one PermissionRequest entry with
a timeout above the script's own wait, replaces the earlier PreToolUse relay without touching anything
else, is idempotent, and comes out again leaving the toast hooks alone. The same goes for the chime
hooks (-IncludeChimes): one Stop and one Notification entry, never a protocol handler.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the hook installer is a Windows PowerShell script",
)

HOOKS = Path(__file__).resolve().parents[2] / "hooks"
RELAY = "Relay-PermissionRequest.ps1"
LEGACY = "Relay-PreToolUse.ps1"

TOAST_HOOKS = {
    "Notification": [{"matcher": "", "hooks": [{"type": "command", "command": 'powershell.exe -File "x\\Send-ClaudeToast.ps1" -Title "Claude Code Alert"'}]}],
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": 'powershell.exe -File "x\\Send-ClaudeToast.ps1" -Title "Claude Code Done"'}]}],
}
UNRELATED_PRE_TOOL_USE = {"matcher": "Bash", "hooks": [{"type": "command", "command": "python my-own-linter.py"}]}


@pytest.fixture
def home(tmp_path):
    (tmp_path / ".claude").mkdir()
    return tmp_path


def _run(script: str, home: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HOOKS / script), *args],
        env={**os.environ, "USERPROFILE": str(home)},
        capture_output=True, text=True, timeout=120, check=False,
    )


def _install(home: Path, *extra: str):
    result = _run("Install-ClaudeHooks.ps1", home, "-IncludeSessionControl", "-SkipToastHooks", "-BackendPort", "8511", *extra)
    assert result.returncode == 0, result.stdout + result.stderr


def _uninstall(home: Path):
    result = _run("Uninstall-ClaudeHooks.ps1", home, "-IncludeSessionControl", "-SkipToastHooks")
    assert result.returncode == 0, result.stdout + result.stderr


def _settings(home: Path) -> dict:
    return json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))


def _seed(home: Path, hooks: dict) -> None:
    (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": hooks, "model": "keep-me"}), encoding="utf-8")


def _seed_legacy_script(home: Path) -> Path:
    scripts = home / ".claude" / "hooks" / "ledgerScripts"
    scripts.mkdir(parents=True)
    legacy = scripts / LEGACY
    legacy.write_text("# old relay", encoding="utf-8")
    return legacy


LEGACY_ENTRY = {"matcher": "Bash|Edit", "hooks": [{"type": "command", "command": f'powershell.exe -File "x\\ledgerScripts\\{LEGACY}"', "timeout": 60}]}


def test_install_adds_one_permission_request_entry_with_a_timeout_above_the_scripts_wait(home):
    _seed(home, TOAST_HOOKS)

    _install(home)

    settings = _settings(home)
    entries = settings["hooks"]["PermissionRequest"]
    assert len(entries) == 1
    assert entries[0]["matcher"] == ""  # every dialog; the event only fires when one will show
    hook = entries[0]["hooks"][0]
    assert RELAY in hook["command"] and "-Port 8511" in hook["command"]
    # The script waits 1805s; Claude Code must not kill it before that.
    assert hook["timeout"] > 1805
    assert (home / ".claude" / "hooks" / "ledgerScripts" / RELAY).is_file()
    assert settings["hooks"]["Notification"] == TOAST_HOOKS["Notification"]
    assert settings["hooks"]["Stop"] == TOAST_HOOKS["Stop"]
    assert settings["model"] == "keep-me"


def test_install_works_on_a_machine_with_no_settings_file(home):
    _install(home)

    assert len(_settings(home)["hooks"]["PermissionRequest"]) == 1


def test_install_replaces_the_legacy_pre_tool_use_relay_and_keeps_other_pre_tool_use_hooks(home):
    _seed(home, {**TOAST_HOOKS, "PreToolUse": [LEGACY_ENTRY, UNRELATED_PRE_TOOL_USE]})
    legacy_script = _seed_legacy_script(home)

    _install(home)

    settings = _settings(home)
    assert settings["hooks"]["PreToolUse"] == [UNRELATED_PRE_TOOL_USE]
    assert LEGACY not in json.dumps(settings)
    assert not legacy_script.exists()
    assert len(settings["hooks"]["PermissionRequest"]) == 1


def test_install_drops_pre_tool_use_entirely_when_only_the_legacy_relay_was_in_it(home):
    _seed(home, {"PreToolUse": [LEGACY_ENTRY]})

    _install(home)

    assert "PreToolUse" not in _settings(home)["hooks"]


def test_installing_twice_does_not_duplicate_the_entry_and_picks_up_a_new_port(home):
    _install(home)
    result = _run("Install-ClaudeHooks.ps1", home, "-IncludeSessionControl", "-SkipToastHooks", "-BackendPort", "8522")
    assert result.returncode == 0, result.stdout + result.stderr

    entries = _settings(home)["hooks"]["PermissionRequest"]
    assert len(entries) == 1
    assert "-Port 8522" in entries[0]["hooks"][0]["command"]


def test_install_leaves_another_permission_request_hook_alone(home):
    other = {"matcher": "", "hooks": [{"type": "command", "command": "python my-own-policy.py"}]}
    _seed(home, {"PermissionRequest": [other]})

    _install(home)

    entries = _settings(home)["hooks"]["PermissionRequest"]
    assert entries[0] == other
    assert len(entries) == 2


def test_uninstall_removes_the_relay_and_its_folder_but_not_the_toast_hooks(home):
    _seed(home, TOAST_HOOKS)
    _install(home)

    _uninstall(home)

    settings = _settings(home)
    assert RELAY not in json.dumps(settings)
    assert not settings["hooks"].get("PermissionRequest")
    assert settings["hooks"]["Notification"] == TOAST_HOOKS["Notification"]
    assert settings["hooks"]["Stop"] == TOAST_HOOKS["Stop"]
    assert settings["model"] == "keep-me"
    assert not (home / ".claude" / "hooks" / "ledgerScripts").exists()


def test_uninstall_keeps_a_users_own_permission_request_hook(home):
    other = {"matcher": "", "hooks": [{"type": "command", "command": "python my-own-policy.py"}]}
    _seed(home, {"PermissionRequest": [other]})
    _install(home)

    _uninstall(home)

    assert _settings(home)["hooks"]["PermissionRequest"] == [other]


def test_uninstall_also_cleans_up_a_machine_that_only_has_the_legacy_relay(home):
    _seed(home, {**TOAST_HOOKS, "PreToolUse": [LEGACY_ENTRY, UNRELATED_PRE_TOOL_USE]})
    _seed_legacy_script(home)

    _uninstall(home)

    settings = _settings(home)
    assert settings["hooks"]["PreToolUse"] == [UNRELATED_PRE_TOOL_USE]
    assert settings["hooks"]["Notification"] == TOAST_HOOKS["Notification"]
    assert not (home / ".claude" / "hooks" / "ledgerScripts" / LEGACY).exists()


def test_uninstall_with_nothing_installed_is_harmless(home):
    _seed(home, TOAST_HOOKS)

    _uninstall(home)

    assert _settings(home)["hooks"]["Notification"] == TOAST_HOOKS["Notification"]


# --- chime hooks (-IncludeChimes) -------------------------------------------------------------

CHIME = "Play-ClaudeChime.ps1"
CHIME_DIR_PARTS = (".claude", "hooks", "chimeScripts")
USERS_OWN_STOP = {"matcher": "", "hooks": [{"type": "command", "command": "python my-own-stop.py"}]}


def _chime_dir(home: Path) -> Path:
    return home.joinpath(*CHIME_DIR_PARTS)


def _install_chimes(home: Path, *extra: str) -> subprocess.CompletedProcess:
    result = _run("Install-ClaudeHooks.ps1", home, "-IncludeChimes", "-SkipToastHooks", *extra)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _uninstall_chimes(home: Path) -> subprocess.CompletedProcess:
    result = _run("Uninstall-ClaudeHooks.ps1", home, "-IncludeChimes", "-SkipToastHooks")
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _chime_entries(settings: dict, event: str) -> list[dict]:
    return [e for e in settings["hooks"].get(event, []) if any(CHIME in h["command"] for h in e["hooks"])]


def _protocol_handler_present() -> bool:
    # Read-only look at the real registry: the chimes-only install must leave it exactly as it was.
    result = subprocess.run(
        ["reg", "query", r"HKCU\Software\Classes\claudecode"], capture_output=True, text=True, check=False,
    )
    return result.returncode == 0


def test_chimes_only_install_adds_one_stop_and_one_notification_entry_and_copies_the_script(home):
    handler_before = _protocol_handler_present()

    result = _install_chimes(home)

    settings = _settings(home)
    stop = _chime_entries(settings, "Stop")
    notification = _chime_entries(settings, "Notification")
    assert len(stop) == 1 and len(notification) == 1
    assert stop[0]["matcher"] == "" and notification[0]["matcher"] == ""
    script = _chime_dir(home) / CHIME
    assert script.is_file()
    assert f'-File "{script}" -Kind done' in stop[0]["hooks"][0]["command"]
    assert f'-File "{script}" -Kind needs-input' in notification[0]["hooks"][0]["command"]
    # No toast: no toast script, no protocol handler written or changed.
    assert not (home / ".claude" / "hooks" / "Send-ClaudeToast.ps1").exists()
    assert "protocol handler" not in result.stdout
    assert _protocol_handler_present() == handler_before


def test_chimes_install_sits_next_to_existing_toast_and_own_hooks(home):
    _seed(home, {**TOAST_HOOKS, "Stop": TOAST_HOOKS["Stop"] + [USERS_OWN_STOP]})

    _install_chimes(home)

    settings = _settings(home)
    assert settings["hooks"]["Stop"][:2] == TOAST_HOOKS["Stop"] + [USERS_OWN_STOP]
    assert len(settings["hooks"]["Stop"]) == 3
    assert settings["hooks"]["Notification"][0] == TOAST_HOOKS["Notification"][0]
    assert len(settings["hooks"]["Notification"]) == 2
    assert settings["model"] == "keep-me"


def test_installing_chimes_twice_does_not_duplicate_and_updates_the_path(home):
    _install_chimes(home)
    stale = _settings(home)
    for event in ("Stop", "Notification"):
        entry = _chime_entries(stale, event)[0]
        entry["hooks"][0]["command"] = entry["hooks"][0]["command"].replace("chimeScripts", "oldFolder")
    (home / ".claude" / "settings.json").write_text(json.dumps(stale), encoding="utf-8")

    _install_chimes(home)

    settings = _settings(home)
    for event in ("Stop", "Notification"):
        entries = _chime_entries(settings, event)
        assert len(entries) == 1
        assert "oldFolder" not in entries[0]["hooks"][0]["command"]
        assert str(_chime_dir(home) / CHIME) in entries[0]["hooks"][0]["command"]


def test_skip_toast_hooks_alone_still_installs_nothing(home):
    result = _run("Install-ClaudeHooks.ps1", home, "-SkipToastHooks")

    assert result.returncode == 0
    assert "Nothing to install" in result.stdout
    assert not (home / ".claude" / "settings.json").exists()


def test_chimes_uninstall_removes_only_chime_entries_and_folder_with_state(home):
    _seed(home, {**TOAST_HOOKS, "Stop": TOAST_HOOKS["Stop"] + [USERS_OWN_STOP]})
    _install_chimes(home)
    state = _chime_dir(home) / "state"
    state.mkdir()
    (state / "afk.flag").write_text("2999-01-01T00:00:00Z", encoding="utf-8")
    (state / "done.stamp").write_text("2026-01-01T00:00:00Z", encoding="utf-8")

    _uninstall_chimes(home)

    settings = _settings(home)
    assert CHIME not in json.dumps(settings)
    assert settings["hooks"]["Stop"] == TOAST_HOOKS["Stop"] + [USERS_OWN_STOP]
    assert settings["hooks"]["Notification"] == TOAST_HOOKS["Notification"]
    assert settings["model"] == "keep-me"
    assert not _chime_dir(home).exists()


def test_chimes_uninstall_drops_an_event_key_that_only_held_the_chime(home):
    _install_chimes(home)

    _uninstall_chimes(home)

    hooks = _settings(home)["hooks"]
    assert "Stop" not in hooks and "Notification" not in hooks


def test_chimes_uninstall_leaves_the_relay_hook_alone(home):
    _install(home)
    _install_chimes(home)

    _uninstall_chimes(home)

    assert len(_settings(home)["hooks"]["PermissionRequest"]) == 1
    assert (home / ".claude" / "hooks" / "ledgerScripts" / RELAY).is_file()


def test_chimes_uninstall_with_nothing_installed_is_harmless(home):
    _seed(home, TOAST_HOOKS)

    _uninstall_chimes(home)

    settings = _settings(home)
    assert settings["hooks"]["Notification"] == TOAST_HOOKS["Notification"]
    assert settings["hooks"]["Stop"] == TOAST_HOOKS["Stop"]


def test_chimes_uninstall_with_no_settings_file_is_harmless(home):
    _uninstall_chimes(home)

    assert not (home / ".claude" / "settings.json").exists()
