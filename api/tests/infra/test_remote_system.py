"""The real System with a fake `run` / `popen`: the commands it issues, not Docker itself."""

import subprocess
from pathlib import Path

import pytest

from app.infra.remote_gateway import RemoteStartError
from app.infra.remote_system import RealSystem, gateway_port


class Recorder:
    def __init__(self, returncode=0, stdout="", raises=None):
        self.calls: list[tuple[object, dict]] = []
        self.returncode, self.stdout, self.raises = returncode, stdout, raises

    def run(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.raises:
            raise self.raises
        return subprocess.CompletedProcess(command, self.returncode, stdout=self.stdout, stderr="")

    def popen(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return type("Proc", (), {"pid": 4242})()


def _system(tmp_path, recorder=None, **kwargs):
    recorder = recorder or Recorder()
    system = RealSystem(
        repo_root=tmp_path,
        backend_port=8501,
        frontend_port=4173,
        gateway_port=8080,
        run=recorder.run,
        popen=recorder.popen,
        environ={"ProgramFiles": str(tmp_path / "pf")},
        **kwargs,
    )
    return system, recorder


# ------------------------------------------------ gateway_port


def test_gateway_port_prefers_the_root_env_file(tmp_path):
    (tmp_path / ".env").write_text("BACKEND_PORT=1\nGATEWAY_PORT=9090\n", encoding="utf-8")
    assert gateway_port(tmp_path, {"GATEWAY_PORT": "7000"}) == 9090


def test_gateway_port_falls_back_to_the_environment_then_the_default(tmp_path):
    assert gateway_port(tmp_path, {"GATEWAY_PORT": "7000"}) == 7000
    assert gateway_port(tmp_path, {}) == 8080


# ------------------------------------------------ docker


def test_docker_ready_follows_docker_info(tmp_path):
    assert _system(tmp_path, Recorder(returncode=0))[0].docker_ready()
    assert not _system(tmp_path, Recorder(returncode=1))[0].docker_ready()


def test_docker_ready_is_false_when_docker_is_missing_or_hangs(tmp_path):
    assert not _system(tmp_path, Recorder(raises=FileNotFoundError()))[0].docker_ready()
    assert not _system(tmp_path, Recorder(raises=subprocess.TimeoutExpired("docker", 15)))[0].docker_ready()


def test_docker_not_installed_without_the_desktop_exe(tmp_path):
    assert not _system(tmp_path)[0].docker_installed()


def test_start_docker_desktop_launches_the_exe(tmp_path):
    system, recorder = _system(tmp_path)
    system.start_docker_desktop()
    assert recorder.calls[0][0][0].endswith("Docker Desktop.exe")


# ------------------------------------------------ compose


def test_compose_up_runs_in_the_gateway_dir_with_the_ports(tmp_path):
    system, recorder = _system(tmp_path)
    assert system.compose_up()
    command, kwargs = recorder.calls[0]
    assert command == ["docker", "compose", "up", "-d", "--build"]
    assert kwargs["cwd"] == tmp_path / "gateway"
    assert kwargs["env"]["GATEWAY_PORT"] == "8080"
    assert kwargs["env"]["BACKEND_PORT"] == "8501"
    assert kwargs["env"]["FRONTEND_PORT"] == "4173"


def test_compose_up_reports_failure(tmp_path):
    assert not _system(tmp_path, Recorder(returncode=1))[0].compose_up()


def test_compose_down_does_nothing_when_docker_is_not_running(tmp_path):
    system, recorder = _system(tmp_path, Recorder(returncode=1))  # `docker info` fails
    assert system.compose_down()
    assert [c[0][1] for c in recorder.calls] == ["info"]  # never reached `compose down`


def test_compose_down_runs_when_docker_is_up(tmp_path):
    system, recorder = _system(tmp_path)
    assert system.compose_down()
    assert recorder.calls[-1][0] == ["docker", "compose", "down"]


def test_container_exists_when_compose_ps_lists_one(tmp_path):
    assert _system(tmp_path, Recorder(stdout="abc123\n"))[0].gateway_container_exists()
    assert not _system(tmp_path, Recorder(stdout="\n"))[0].gateway_container_exists()


# ------------------------------------------------ the web interface


def test_start_frontend_builds_first_when_there_is_no_build(tmp_path):
    system, recorder = _system(tmp_path)
    handle = system.start_frontend()
    assert recorder.calls[0][0] == "npm run build"
    assert recorder.calls[1][0] == "npm run preview -- --port 4173"
    assert recorder.calls[1][1]["env"]["BACKEND_PORT"] == "8501"
    assert handle.pid == 4242


def test_start_frontend_skips_the_build_when_dist_exists(tmp_path):
    (tmp_path / "web" / "dist").mkdir(parents=True)
    system, recorder = _system(tmp_path)
    system.start_frontend()
    assert [c[0] for c in recorder.calls] == ["npm run preview -- --port 4173"]


def test_start_frontend_fails_with_a_reason_when_the_build_fails(tmp_path):
    system, _ = _system(tmp_path, Recorder(returncode=1))
    with pytest.raises(RemoteStartError, match="Building the web interface failed"):
        system.start_frontend()


def test_stop_frontend_kills_the_whole_process_tree(tmp_path):
    system, recorder = _system(tmp_path)
    system.stop_frontend(type("Proc", (), {"pid": 4242})())
    assert recorder.calls[0][0] == ["taskkill", "/PID", "4242", "/T", "/F"]


# ------------------------------------------------ gateway probe


def test_gateway_up_uses_the_injected_probe(tmp_path):
    system, _ = _system(tmp_path, probe_gateway=lambda: True)
    assert system.gateway_up()


def test_the_real_probe_is_false_when_nothing_listens(tmp_path):
    system = RealSystem(repo_root=tmp_path, backend_port=1, frontend_port=1, gateway_port=1)
    assert not system.gateway_up()
