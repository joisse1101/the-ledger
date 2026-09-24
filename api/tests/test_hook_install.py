"""hooks/Install-ClaudeHooks.ps1 and Uninstall-ClaudeHooks.ps1 -IncludeSessionControl, run for real.

Both scripts resolve everything from $env:USERPROFILE, so each test points USERPROFILE at a throwaway
folder: the real ~/.claude/settings.json is never read or written. Only the `-SkipToastHooks` paths
are exercised, because the toast install also writes the machine's real HKCU claudecode:// handler.

Guards the promises of the relay hook's install story: it goes in as one PermissionRequest entry with
a timeout above the script's own wait, replaces the earlier PreToolUse relay without touching anything
else, is idempotent, and comes out again leaving the toast hooks alone.
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
