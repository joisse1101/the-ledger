"""widget/Install-WidgetShortcut.ps1 and Uninstall-WidgetShortcut.ps1, run for real.

Both take the folders to work in (-DesktopPath/-StartupPath), so every test points them at throwaway
folders: the real Desktop and Startup shortcuts are never read or written. Stdin is closed, so a
script that asked a question would fail instead of waiting.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the shortcut scripts are Windows PowerShell scripts",
)

WIDGET = Path(__file__).resolve().parents[2] / "widget"
SHORTCUT = "Ledger Widget.lnk"


@pytest.fixture
def folders(tmp_path):
    desktop, startup = tmp_path / "Desktop", tmp_path / "Startup"
    desktop.mkdir()
    startup.mkdir()
    return desktop, startup


def _run(script: str, desktop: Path, startup: Path, *switches: str) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(WIDGET / script),
         *switches, "-DesktopPath", str(desktop), "-StartupPath", str(startup)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _target(shortcut: Path) -> str:
    """The launcher a shortcut runs, read back through the shell."""
    script = f"(New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut}').Arguments"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=60, check=False)
    return result.stdout.strip()


def test_install_creates_only_the_shortcuts_asked_for(folders):
    desktop, startup = folders

    _run("Install-WidgetShortcut.ps1", desktop, startup, "-Desktop")

    assert (desktop / SHORTCUT).is_file()
    assert not (startup / SHORTCUT).exists()


def test_install_points_the_shortcut_at_the_silent_launcher(folders):
    desktop, startup = folders

    _run("Install-WidgetShortcut.ps1", desktop, startup, "-Desktop", "-Startup")

    assert _target(desktop / SHORTCUT) == f'"{WIDGET / "Start-Widget.vbs"}"'
    assert _target(startup / SHORTCUT) == f'"{WIDGET / "Start-Widget.vbs"}"'


def test_install_twice_leaves_one_unchanged_shortcut(folders):
    desktop, startup = folders
    _run("Install-WidgetShortcut.ps1", desktop, startup, "-Desktop", "-Startup")
    first_target = _target(desktop / SHORTCUT)

    _run("Install-WidgetShortcut.ps1", desktop, startup, "-Desktop", "-Startup")

    assert sorted(path.name for path in desktop.iterdir()) == [SHORTCUT]
    assert sorted(path.name for path in startup.iterdir()) == [SHORTCUT]
    assert _target(desktop / SHORTCUT) == first_target


def test_uninstall_removes_only_the_startup_shortcut_when_asked(folders):
    desktop, startup = folders
    _run("Install-WidgetShortcut.ps1", desktop, startup, "-Desktop", "-Startup")

    _run("Uninstall-WidgetShortcut.ps1", desktop, startup, "-Startup")

    assert (desktop / SHORTCUT).is_file()
    assert not (startup / SHORTCUT).exists()


def test_uninstall_removes_both_by_default_and_tolerates_missing_ones(folders):
    desktop, startup = folders
    _run("Install-WidgetShortcut.ps1", desktop, startup, "-Desktop")

    _run("Uninstall-WidgetShortcut.ps1", desktop, startup)

    assert not (desktop / SHORTCUT).exists()
