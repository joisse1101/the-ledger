"""scripts/Ledger-Common.ps1: the shared helper's pure logic, run for real in Windows PowerShell.

Every case works on a throwaway folder or an injected resolver, so the real repo .env, the real
environment's BACKEND_PORT and the machine's installed tools are never consulted.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the shared helper is a Windows PowerShell script",
)

HELPER = Path(__file__).resolve().parents[2] / "scripts" / "Ledger-Common.ps1"


def _ps(snippet: str, env: dict[str, str] | None = None) -> str:
    """Dot-source the helper, run the snippet, return its stdout (stripped)."""
    script = f"$ErrorActionPreference = 'Stop'; . '{HELPER}'; {snippet}"
    environment = {k: v for k, v in os.environ.items() if k not in ("BACKEND_PORT", "FRONTEND_PORT", "GATEWAY_PORT")}
    environment.update(env or {})
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        env=environment, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def test_read_env_file_skips_comments_and_blank_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\n\nBACKEND_PORT=8511\n  FRONTEND_PORT = 8512 \n#GATEWAY_PORT=1\n", encoding="utf-8")

    output = _ps(f"$v = Read-EnvFile '{env_file}'; \"$($v.Count) $($v['BACKEND_PORT']) $($v['FRONTEND_PORT'])\"")

    assert output == "2 8511 8512"


def test_read_env_file_returns_nothing_when_file_is_missing(tmp_path):
    assert _ps(f"(Read-EnvFile '{tmp_path / 'absent.env'}').Count") == "0"


def test_resolve_port_prefers_explicit_over_env_file_and_environment():
    output = _ps(
        "Resolve-Port -Explicit 9000 -Name 'BACKEND_PORT' -Default 8501 -EnvFileValues @{ BACKEND_PORT = '8511' }",
        env={"BACKEND_PORT": "8522"},
    )
    assert output == "9000"


def test_resolve_port_prefers_env_file_over_environment():
    output = _ps(
        "Resolve-Port -Name 'BACKEND_PORT' -Default 8501 -EnvFileValues @{ BACKEND_PORT = '8511' }",
        env={"BACKEND_PORT": "8522"},
    )
    assert output == "8511"


def test_resolve_port_prefers_environment_over_default():
    assert _ps("Resolve-Port -Name 'BACKEND_PORT' -Default 8501", env={"BACKEND_PORT": "8522"}) == "8522"


def test_resolve_port_falls_back_to_default():
    assert _ps("Resolve-Port -Name 'BACKEND_PORT' -Default 8501") == "8501"


def test_missing_prerequisites_reports_absent_tool_with_its_download_page():
    output = _ps("Get-MissingPrerequisites -Resolver { param($c) $c -ne 'node' } | ForEach-Object { \"$($_.Name) $($_.Url)\" }")
    assert output == "Node https://nodejs.org/en/download"


def test_missing_prerequisites_ignores_docker_without_remote():
    assert _ps("@(Get-MissingPrerequisites -Resolver { $false }).Name -join ','") == "Python,Node"


def test_missing_prerequisites_includes_docker_with_remote():
    assert _ps("@(Get-MissingPrerequisites -Remote -Resolver { $false }).Name -join ','") == "Python,Node,Docker"


def test_missing_prerequisites_is_empty_when_everything_is_present():
    assert _ps("@(Get-MissingPrerequisites -Remote -Resolver { $true }).Count") == "0"


def test_files_stamp_changes_when_a_file_changes(tmp_path):
    lock = tmp_path / "package-lock.json"
    lock.write_text("one", encoding="utf-8")
    before = _ps(f"Get-FilesStamp '{lock}'")
    lock.write_text("two", encoding="utf-8")

    after = _ps(f"Get-FilesStamp '{lock}'")

    assert before != after


def test_files_stamp_is_stable_for_unchanged_files(tmp_path):
    lock = tmp_path / "package-lock.json"
    lock.write_text("one", encoding="utf-8")
    assert _ps(f"Get-FilesStamp '{lock}'") == _ps(f"Get-FilesStamp '{lock}'")


def test_stamp_matches_only_the_value_written(tmp_path):
    stamp = tmp_path / ".stamp"

    output = _ps(
        f"$a = Test-Stamp '{stamp}' 'abc'; Write-Stamp '{stamp}' 'abc'; "
        f"$b = Test-Stamp '{stamp}' 'abc'; $c = Test-Stamp '{stamp}' 'xyz'; \"$a $b $c\""
    )

    assert output == "False True False"
