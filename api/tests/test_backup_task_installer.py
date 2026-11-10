"""hooks/ledgerScripts/Install-HistoryBackupTask.ps1: which Python the scheduled task runs.

The task runs with no console (pythonw.exe) so nothing flashes at 2 pm, and falls back to python.exe
with a warning when pythonw.exe is missing. Each run registers a real task under a unique throwaway
name pointing at a fake Scripts folder, then removes it; the task never runs.
"""

import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the installer is a Windows PowerShell script that registers a Windows scheduled task",
)

INSTALLER = Path(__file__).resolve().parents[2] / "hooks" / "ledgerScripts" / "Install-HistoryBackupTask.ps1"


@pytest.fixture
def task_name():
    name = f"Ledger Test Backup {uuid.uuid4().hex[:8]}"
    yield name
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         f"Unregister-ScheduledTask -TaskName '{name}' -Confirm:$false -ErrorAction SilentlyContinue"],
        capture_output=True, timeout=60, check=False,
    )


def _install(task_name: str, scripts_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(INSTALLER),
         "-TaskName", task_name, "-ScriptsDir", str(scripts_dir)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120, check=False,
    )


def _task_executable(task_name: str) -> str:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         f"(Get-ScheduledTask -TaskName '{task_name}').Actions[0].Execute"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    return result.stdout.strip()


def _scripts_dir(tmp_path: Path, *names: str) -> Path:
    folder = tmp_path / "Scripts"
    folder.mkdir()
    for name in names:
        (folder / name).write_bytes(b"")
    return folder


def test_the_task_runs_pythonw_when_it_exists(tmp_path, task_name):
    scripts = _scripts_dir(tmp_path, "python.exe", "pythonw.exe")

    result = _install(task_name, scripts)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _task_executable(task_name) == str(scripts / "pythonw.exe")
    assert "pythonw.exe not found" not in result.stdout + result.stderr


def test_the_task_falls_back_to_python_with_a_warning_when_pythonw_is_missing(tmp_path, task_name):
    scripts = _scripts_dir(tmp_path, "python.exe")

    result = _install(task_name, scripts)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _task_executable(task_name) == str(scripts / "python.exe")
    assert "pythonw.exe not found" in result.stdout + result.stderr
