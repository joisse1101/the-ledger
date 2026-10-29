"""scripts/Ledger-Common.ps1: the shared helper's pure logic, run for real in Windows PowerShell.

Every case works on a throwaway folder or an injected resolver, so the real repo .env, the real
environment's BACKEND_PORT and the machine's installed tools are never consulted.
"""

import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the shared helper is a Windows PowerShell script",
)

HELPER = Path(__file__).resolve().parents[2] / "scripts" / "Ledger-Common.ps1"


def _run_ps(snippet: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Dot-source the helper and run the snippet in a clean port environment."""
    script = f"$ErrorActionPreference = 'Stop'; . '{HELPER}'; {snippet}"
    environment = {k: v for k, v in os.environ.items() if k not in ("BACKEND_PORT", "FRONTEND_PORT", "GATEWAY_PORT")}
    environment.update(env or {})
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        env=environment, capture_output=True, text=True, timeout=60, check=False,
    )


def _ps(snippet: str, env: dict[str, str] | None = None) -> str:
    """Run the snippet, assert it succeeded, return its stdout (stripped)."""
    result = _run_ps(snippet, env)
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
    result = _run_ps("Resolve-LedgerPort -Name 'BACKEND_PORT' -IsFree { $false }")

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


# --- dependency repair -------------------------------------------------------------------------

# Stands in for the real installer: records each step and leaves behind what the real one would.
FAKE_INSTALLER = r"""
$calls = New-Object System.Collections.Generic.List[string]
$installer = {
    param($s)
    $calls.Add("$($s.Component):$($s.Action)")
    switch ($s.Action) {
        'venv' { New-Item -ItemType File -Force "$($s.Directory)\.venv\Scripts\python.exe" | Out-Null }
        'npm' { New-Item -ItemType File -Force "$($s.Directory)\node_modules\pkg\index.js" | Out-Null }
        'electron' { New-Item -ItemType File -Force "$($s.Directory)\node_modules\electron\dist\electron.exe" | Out-Null }
    }
    $true
}
"""
CALLS = '($calls -join ",")'


@pytest.fixture
def repo(tmp_path):
    """A repo whose venv and node_modules folders exist but are empty."""
    (tmp_path / "api" / ".venv").mkdir(parents=True)
    (tmp_path / "api" / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "api" / "requirements-dev.txt").write_text("-r requirements.txt\npytest\n", encoding="utf-8")
    for name in ("web", "widget"):
        (tmp_path / name / "node_modules").mkdir(parents=True)
        (tmp_path / name / "package-lock.json").write_text("{}", encoding="utf-8")
    return tmp_path


def _plan(root: Path) -> str:
    return _ps(f"(Get-DependencyRepairs -RepoRoot '{root}' | ForEach-Object {{ \"$($_.Component):$($_.Action)\" }}) -join ','")


def _repair(root: Path, component: str = "") -> str:
    """Run the repair with the fake installer; return the steps it was asked to perform."""
    only = f"-Component {component}" if component else ""
    return _ps(f"{FAKE_INSTALLER} Invoke-DependencyRepair -RepoRoot '{root}' {only} -Installer $installer 6>$null; {CALLS}")


def test_repair_plans_everything_when_the_folders_exist_but_are_empty(repo):
    assert _plan(repo) == "api:venv,api:pip,web:npm,widget:npm,widget:electron"


def test_repair_rebuilds_empty_folders_then_has_nothing_left_to_do(repo):
    assert _repair(repo) == "api:venv,api:pip,web:npm,widget:npm,widget:electron"
    assert _plan(repo) == ""


def test_repair_installs_nothing_when_everything_is_current(repo):
    _repair(repo)

    assert _repair(repo) == ""


def test_repair_fetches_only_the_electron_binary_when_it_is_missing(repo):
    _repair(repo)
    (repo / "widget" / "node_modules" / "electron" / "dist" / "electron.exe").unlink()

    assert _repair(repo) == "widget:electron"


def test_repair_reinstalls_packages_when_the_lockfile_changed(repo):
    _repair(repo)
    (repo / "web" / "package-lock.json").write_text('{"changed": true}', encoding="utf-8")

    assert _repair(repo) == "web:npm"


def test_repair_reinstalls_requirements_when_they_changed(repo):
    _repair(repo)
    (repo / "api" / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")

    assert _repair(repo) == "api:pip"


def test_repair_only_touches_the_components_asked_for(repo):
    assert _repair(repo, component="widget") == "widget:npm,widget:electron"


def test_repair_stops_with_a_named_error_when_an_install_fails(repo):
    result = _run_ps(f"Invoke-DependencyRepair -RepoRoot '{repo}' -Component web -Installer {{ $false }} 6>$null")

    assert result.returncode != 0
    assert "Installing the web packages (npm ci) failed" in result.stderr + result.stdout


def test_repair_leaves_no_stamp_behind_when_an_install_fails(repo):
    _run_ps(f"Invoke-DependencyRepair -RepoRoot '{repo}' -Component web -Installer {{ $false }} 6>$null")

    assert "web:npm" in _plan(repo)


def test_repair_fails_when_electron_is_still_missing_after_its_step(repo):
    result = _run_ps(f"Invoke-DependencyRepair -RepoRoot '{repo}' -Component widget -Installer {{ $true }} 6>$null")

    assert result.returncode != 0
    assert "Electron binary is missing" in result.stderr + result.stdout


# --- start verification ------------------------------------------------------------------------

def test_wait_until_returns_true_at_once_when_the_condition_holds():
    assert _ps("Wait-Until -Condition { $true } -TimeoutSeconds 0") == "True"


def test_wait_until_returns_true_once_the_condition_turns_true():
    output = _ps("$n = 0; Wait-Until -Condition { $script:n++; $script:n -ge 3 } -TimeoutSeconds 10 -IntervalSeconds 0.05")
    assert output == "True"


def test_wait_until_returns_false_when_the_timeout_passes():
    assert _ps("Wait-Until -Condition { $false } -TimeoutSeconds 1 -IntervalSeconds 0.1") == "False"


def test_http_up_is_true_for_a_server_answering_200():
    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert _ps(f"Test-HttpUp -Url 'http://127.0.0.1:{server.server_port}/'") == "True"
    finally:
        server.shutdown()
        server.server_close()


def test_http_up_is_false_when_nothing_listens():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]

    assert _ps(f"Test-HttpUp -Url 'http://127.0.0.1:{closed_port}/'") == "False"


def test_start_summary_lists_each_piece_and_passes_when_nothing_failed():
    output = _ps(
        "Write-StartSummary -Result @("
        "[PSCustomObject]@{ Name = 'backend'; State = 'running'; Address = 'http://localhost:8501' },"
        "[PSCustomObject]@{ Name = 'widget'; State = 'skipped'; Address = $null }) 6>&1"
    )
    assert output.splitlines() == ["backend   running  http://localhost:8501", "widget    skipped", "True"]


def test_start_summary_fails_when_a_piece_did_not_come_up():
    output = _ps(
        "Write-StartSummary -Result @("
        "[PSCustomObject]@{ Name = 'backend'; State = 'running'; Address = 'http://localhost:8501' },"
        "[PSCustomObject]@{ Name = 'frontend'; State = 'failed'; Address = 'http://localhost:8502' }) 6>&1"
    )
    assert output.splitlines() == ["backend   running  http://localhost:8501", "frontend  failed  http://localhost:8502", "False"]


# --- relay hook staleness ----------------------------------------------------------------------

def _settings_with_relay(tmp_path: Path, port: int | None) -> Path:
    """A throwaway settings.json; with a port, it holds the relay hook installed for that port."""
    hooks: dict = {}
    if port is not None:
        command = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/u/ledgerScripts/Relay-PermissionRequest.ps1" -Port {port}'
        hooks["PermissionRequest"] = [{"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": 1810}]}]
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": hooks}), encoding="utf-8")
    return settings


def _update(settings: Path, backend_port: int, interactive: str, answer: str = "$true", extra: str = "") -> list[str]:
    """Run Update-StaleRelayHook with fakes; lines are what it printed, then what the fakes recorded."""
    output = _ps(
        f"$log = New-Object System.Collections.Generic.List[string]; "
        f"Update-StaleRelayHook -BackendPort {backend_port} -SettingsPath '{settings}' -Interactive {interactive} {extra} "
        f"-Reinstall {{ param($p) $log.Add(\"reinstall:$p\") }} "
        f"-Ask {{ param($q) $log.Add('asked'); {answer} }} 6>&1; "
        f"$log -join ','"
    )
    return output.splitlines()


def test_relay_hook_port_is_read_from_the_installed_command(tmp_path):
    settings = _settings_with_relay(tmp_path, 8511)
    assert _ps(f"Get-RelayHookPort -SettingsPath '{settings}'") == "8511"


def test_relay_hook_port_is_empty_when_the_hook_is_not_installed(tmp_path):
    settings = _settings_with_relay(tmp_path, None)
    assert _ps(f"$null -eq (Get-RelayHookPort -SettingsPath '{settings}')") == "True"


def test_relay_hook_port_is_empty_when_there_is_no_settings_file(tmp_path):
    assert _ps(f"$null -eq (Get-RelayHookPort -SettingsPath '{tmp_path / 'absent.json'}')") == "True"


def test_stale_relay_hook_is_reinstalled_when_the_console_user_agrees(tmp_path):
    lines = _update(_settings_with_relay(tmp_path, 8511), 8520, interactive="$true", answer="$true")

    assert lines[-3:] == ["Reinstalled the relay hook for port 8520.", "reinstalled", "asked,reinstall:8520"]


def test_stale_relay_hook_is_left_alone_when_the_console_user_declines(tmp_path):
    lines = _update(_settings_with_relay(tmp_path, 8511), 8520, interactive="$true", answer="$false")

    assert lines[-2:] == ["declined", "asked"]


def test_stale_relay_hook_is_reinstalled_with_a_notice_when_there_is_no_console(tmp_path):
    lines = _update(_settings_with_relay(tmp_path, 8511), 8520, interactive="$false")

    assert lines[-3:] == ["Reinstalled the relay hook for port 8520.", "reinstalled", "reinstall:8520"]


def test_stale_relay_hook_is_reinstalled_without_asking_when_told_to_assume_yes(tmp_path):
    lines = _update(_settings_with_relay(tmp_path, 8511), 8520, interactive="$true", extra="-Yes")

    assert lines[-2:] == ["reinstalled", "reinstall:8520"]


def test_relay_hook_that_is_not_installed_is_not_mentioned_or_installed(tmp_path):
    assert _update(_settings_with_relay(tmp_path, None), 8520, interactive="$true") == ["current"]


def test_relay_hook_on_the_current_port_is_left_alone_silently(tmp_path):
    assert _update(_settings_with_relay(tmp_path, 8520), 8520, interactive="$true") == ["current"]


# --- install choices ---------------------------------------------------------------------------

def _choice(mode: str, interactive: str, answer: str = "$true") -> list[str]:
    """Resolve-InstallChoice with a fake prompt; returns what it printed, the choice, whether it asked."""
    output = _ps(
        f"$script:asked = $false; Resolve-InstallChoice -Mode {mode} -Question 'Do it?' -Interactive {interactive} "
        f"-Ask {{ param($q) $script:asked = $true; {answer} }} 6>&1; \"asked=$script:asked\""
    )
    return output.splitlines()


def test_install_choice_yes_is_pre_answered_without_asking():
    assert _choice("yes", "$true") == ["True", "asked=False"]


def test_install_choice_no_is_pre_answered_without_asking():
    assert _choice("no", "$true") == ["False", "asked=False"]


def test_install_choice_asks_on_a_console_and_follows_the_answer():
    assert _choice("ask", "$true", answer="$true") == ["True", "asked=True"]
    assert _choice("ask", "$true", answer="$false") == ["False", "asked=True"]


def test_install_choice_ask_without_a_console_is_a_no_with_a_notice():
    lines = _choice("ask", "$false")

    assert lines[0].startswith("No console to ask on, so not installing: Do it?")
    assert lines[1:] == ["False", "asked=False"]
