"""Install-Ledger.ps1, run for real against a sandbox.

Everything it touches is redirected: USERPROFILE is a throwaway folder (so the real settings.json is
never read or written), the shortcuts go to throwaway folders, and the backup task has a unique name
that is removed afterwards. The toast hooks are never accepted here, because they also write the real
claudecode:// protocol handler under HKCU. Stdin is closed, so a question that was asked instead of
pre-answered would show up as a skip, never a hang.
"""

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "Install-Ledger.ps1"
SHORTCUT = "Ledger Widget.lnk"
BACKEND_PORT = "8511"

pytestmark = pytest.mark.skipif(
    sys.platform != "win32"
    or shutil.which("powershell.exe") is None
    or not (ROOT / "api" / ".venv" / "Scripts" / "python.exe").is_file(),
    reason="the installer is a Windows PowerShell script and the backup task needs the api venv",
)

NOTHING = ("-Shortcut", "no", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "no")


class Sandbox:
    def __init__(self, base: Path):
        self.home = base / "home"
        self.desktop = base / "Desktop"
        self.startup = base / "Startup"
        self.task_name = f"Ledger Test Backup {uuid.uuid4().hex[:8]}"
        for folder in (self.home / ".claude", self.desktop, self.startup):
            folder.mkdir(parents=True)

    def run(self, *switches: str, port: str = BACKEND_PORT) -> str:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(INSTALLER),
             "-DesktopPath", str(self.desktop), "-StartupPath", str(self.startup),
             "-TaskName", self.task_name, "-BackendPort", port, *switches],
            env={**os.environ, "USERPROFILE": str(self.home)},
            # With a throwaway USERPROFILE, PowerShell's module cache falls back to a path relative to the
            # working directory; run in the sandbox so nothing lands in the repo.
            cwd=self.home.parent, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    def task_count(self) -> int:
        script = f"@(Get-ScheduledTask -TaskName '{self.task_name}' -ErrorAction SilentlyContinue).Count"
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=60, check=False)
        return int(result.stdout.strip())

    def remove_task(self) -> None:
        script = f"Unregister-ScheduledTask -TaskName '{self.task_name}' -Confirm:$false -ErrorAction SilentlyContinue"
        subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, timeout=60, check=False)

    @property
    def settings_path(self) -> Path:
        return self.home / ".claude" / "settings.json"

    def relay_entries(self) -> list:
        return json.loads(self.settings_path.read_text(encoding="utf-8-sig"))["hooks"]["PermissionRequest"]


@pytest.fixture
def sandbox(tmp_path):
    box = Sandbox(tmp_path)
    yield box
    box.remove_task()


def test_declining_everything_installs_nothing(sandbox):
    output = sandbox.run(*NOTHING)

    assert list(sandbox.desktop.iterdir()) == []
    assert list(sandbox.startup.iterdir()) == []
    assert not sandbox.settings_path.exists()
    assert sandbox.task_count() == 0
    assert output.count("skipped") == 5


def test_accepting_some_extras_installs_only_those(sandbox):
    sandbox.run("-Shortcut", "yes", "-Autostart", "no", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "yes")

    assert (sandbox.desktop / SHORTCUT).is_file()
    assert list(sandbox.startup.iterdir()) == []
    assert not sandbox.settings_path.exists()
    assert sandbox.task_count() == 1


def test_each_extra_is_explained_before_it_is_offered(sandbox):
    output = sandbox.run("-Shortcut", "yes", "-Autostart", "no", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "no")

    assert output.count("What it does:") == 5
    assert output.count("What it changes:") == 5
    assert output.count("If you decline:") == 5
    toast = output[output.index("== Toast hooks"):output.index("== Relay hook")]
    assert "registers the claudecode:// protocol handler" in toast
    assert "settings.json" in toast
    # The explanation comes first; the toast install itself never started.
    assert "Installing: toast hooks" not in output


def test_autostart_is_not_offered_when_the_shortcut_is_declined(sandbox):
    output = sandbox.run("-Shortcut", "no", "-Autostart", "yes", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "no")

    assert "Start the widget at sign-in" not in output
    assert list(sandbox.startup.iterdir()) == []


def test_autostart_adds_the_sign_in_shortcut_beside_the_desktop_one(sandbox):
    sandbox.run("-Shortcut", "yes", "-Autostart", "yes", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "no")

    assert (sandbox.desktop / SHORTCUT).is_file()
    assert (sandbox.startup / SHORTCUT).is_file()


def test_relay_hook_goes_into_settings_with_the_chosen_port(sandbox):
    sandbox.run("-Shortcut", "no", "-ToastHooks", "no", "-RelayHook", "yes", "-BackupTask", "no")

    entries = sandbox.relay_entries()
    assert len(entries) == 1
    assert f"-Port {BACKEND_PORT}" in entries[0]["hooks"][0]["command"]


def test_without_a_console_extras_that_were_not_pre_answered_are_skipped(sandbox):
    output = sandbox.run()

    assert list(sandbox.desktop.iterdir()) == []
    assert not sandbox.settings_path.exists()
    assert sandbox.task_count() == 0
    assert "No console to ask on" in output


def test_yes_accepts_every_extra_that_was_not_pre_answered(sandbox):
    sandbox.run("-Yes", "-ToastHooks", "no")

    assert (sandbox.desktop / SHORTCUT).is_file()
    assert (sandbox.startup / SHORTCUT).is_file()
    assert len(sandbox.relay_entries()) == 1
    assert sandbox.task_count() == 1


def test_a_second_run_duplicates_no_shortcut_hook_entry_or_task(sandbox):
    accept = ("-Yes", "-ToastHooks", "no")
    sandbox.run(*accept)
    first_settings = sandbox.settings_path.read_text(encoding="utf-8-sig")

    sandbox.run(*accept)

    assert [path.name for path in sandbox.desktop.iterdir()] == [SHORTCUT]
    assert [path.name for path in sandbox.startup.iterdir()] == [SHORTCUT]
    assert len(sandbox.relay_entries()) == 1
    assert sandbox.settings_path.read_text(encoding="utf-8-sig") == first_settings
    assert sandbox.task_count() == 1


def test_a_relay_hook_that_is_not_installed_is_offered_a_first_install(sandbox):
    output = sandbox.run(*NOTHING)

    assert "== Relay hook" in output
    assert "== Relay hook (already installed)" not in output


def test_an_installed_relay_hook_is_offered_a_reinstall_that_updates_its_port(sandbox):
    sandbox.run("-Shortcut", "no", "-ToastHooks", "no", "-RelayHook", "yes", "-BackupTask", "no", port="8511")

    output = sandbox.run("-Shortcut", "no", "-ToastHooks", "no", "-RelayHook", "yes", "-BackupTask", "no", port="8522")

    assert "== Relay hook (already installed)" in output
    assert "installed for backend port 8511" in output
    assert "relay hook           reinstalled" in output
    entries = sandbox.relay_entries()
    assert len(entries) == 1
    assert "-Port 8522" in entries[0]["hooks"][0]["command"]


def test_declining_the_reinstall_leaves_the_installed_hook_alone(sandbox):
    sandbox.run("-Shortcut", "no", "-ToastHooks", "no", "-RelayHook", "yes", "-BackupTask", "no", port="8511")
    before = sandbox.settings_path.read_text(encoding="utf-8-sig")

    sandbox.run(*NOTHING, port="8522")

    assert sandbox.settings_path.read_text(encoding="utf-8-sig") == before


def test_accepting_the_shortcut_prepares_the_backend_and_widget_dependencies(sandbox):
    output = sandbox.run("-Shortcut", "yes", "-Autostart", "no", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "no")

    assert "Checking dependencies (api, widget)" in output


def test_accepting_only_the_backup_task_prepares_just_the_backend(sandbox):
    output = sandbox.run("-Shortcut", "no", "-ToastHooks", "no", "-RelayHook", "no", "-BackupTask", "yes")

    assert "Checking dependencies (api)" in output


def test_declining_everything_checks_no_dependencies(sandbox):
    assert "Checking dependencies" not in sandbox.run(*NOTHING)
