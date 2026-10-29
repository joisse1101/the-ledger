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


def _resolve(saved: str = "@{}", free: str = "$true", reuse: str = "$false", extra: str = "") -> str:
    """Resolve BACKEND_PORT with an injected notion of which ports are free; return 'port source'."""
    return _ps(
        f"$r = Resolve-LedgerPort -Name 'BACKEND_PORT' -SavedPorts {saved} "
        f"-IsFree {{ param($p) {free} }} -ReuseWhen {{ param($p) {reuse} }} {extra}; \"$($r.Port) $($r.Source)\""
    )


def test_resolve_ledger_port_scans_from_the_start_of_the_range_on_first_run():
    assert _resolve() == "8501 scanned"


def test_resolve_ledger_port_skips_busy_ports_while_scanning():
    assert _resolve(free="$p -ge 8503") == "8503 scanned"


def test_resolve_ledger_port_reuses_the_saved_port_when_it_is_free():
    assert _resolve(saved="@{ BACKEND_PORT = 8520 }") == "8520 saved"


def test_resolve_ledger_port_repicks_when_another_program_holds_the_saved_port():
    assert _resolve(saved="@{ BACKEND_PORT = 8520 }", free="$p -ne 8520") == "8501 scanned"


def test_resolve_ledger_port_reuses_a_busy_saved_port_held_by_this_app():
    assert _resolve(saved="@{ BACKEND_PORT = 8520 }", free="$p -ne 8520", reuse="$p -eq 8520") == "8520 saved"


def test_resolve_ledger_port_prefers_explicit_then_env_file_over_saved():
    saved = "@{ BACKEND_PORT = 8520 }"
    assert _resolve(saved=saved, extra="-Explicit 9000 -EnvFileValues @{ BACKEND_PORT = '8511' }") == "9000 parameter"
    assert _resolve(saved=saved, extra="-EnvFileValues @{ BACKEND_PORT = '8511' }") == "8511 env"


def test_resolve_ledger_port_does_not_hand_out_an_excluded_port():
    assert _resolve(extra="-Exclude 8501,8502") == "8503 scanned"


def test_resolve_ledger_port_fails_when_the_range_is_full():
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         f". '{HELPER}'; Resolve-LedgerPort -Name 'BACKEND_PORT' -IsFree {{ $false }}"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode != 0
    assert "No free port left in 8501-8599" in result.stderr + result.stdout


def test_saved_ports_round_trip_and_keep_other_services(tmp_path):
    ports_file = tmp_path / "ports.json"

    output = _ps(
        f"Save-Port -Name 'BACKEND_PORT' -Port 8510 -Path '{ports_file}'; "
        f"Save-Port -Name 'FRONTEND_PORT' -Port 8511 -Path '{ports_file}'; "
        f"$s = Get-SavedPorts -Path '{ports_file}'; \"$($s['BACKEND_PORT']) $($s['FRONTEND_PORT'])\""
    )

    assert output == "8510 8511"


def test_saved_ports_are_empty_before_the_first_run(tmp_path):
    assert _ps(f"(Get-SavedPorts -Path '{tmp_path / 'none.json'}').Count") == "0"


def test_port_free_is_false_while_a_listener_holds_it():
    output = _ps(
        "$l = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0); $l.Start(); "
        "$port = $l.LocalEndpoint.Port; $busy = Test-PortFree -Port $port; $l.Stop(); "
        "$freed = Test-PortFree -Port $port; \"$busy $freed\""
    )
    assert output == "False True"


def test_prerequisite_check_names_the_missing_tool_and_returns_false():
    output = _ps("Test-Prerequisites -Resolver { param($c) $c -ne 'node' } 6>&1")
    assert output.splitlines() == ["Node is not installed. Download it from https://nodejs.org/en/download", "False"]


def test_prerequisite_check_passes_silently_when_everything_is_present():
    assert _ps("Test-Prerequisites -Resolver { $true } 6>&1") == "True"


def test_prerequisite_check_ignores_missing_docker_without_remote():
    assert _ps("Test-Prerequisites -Resolver { param($c) $c -ne 'docker' } 6>&1") == "True"


def test_prerequisite_check_names_docker_with_remote():
    output = _ps("Test-Prerequisites -Remote -Resolver { param($c) $c -ne 'docker' } 6>&1")
    assert output.splitlines() == ["Docker is not installed. Download it from https://www.docker.com/products/docker-desktop/", "False"]
