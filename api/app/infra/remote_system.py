"""The real process control behind remote_gateway.RemoteGateway: Docker, the gateway compose
project, and the web interface's `vite preview`. Windows-first, like the rest of the launch
tooling; every external call goes through the injected `run` / `popen`, so tests use fakes."""

from __future__ import annotations

import http.client
import os
import re
import shutil
import socket
import ssl
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from app.infra.remote_gateway import RemoteStartError

DEFAULT_GATEWAY_PORT = 8080  # matches gateway/docker-compose.yml and .env.example
DOCKER_INFO_TIMEOUT_SECONDS = 15
COMPOSE_UP_TIMEOUT_SECONDS = 600  # the first run builds the image
COMPOSE_TIMEOUT_SECONDS = 120
BUILD_TIMEOUT_SECONDS = 600
PORT_PROBE_TIMEOUT_SECONDS = 1.0
GATEWAY_PROBE_TIMEOUT_SECONDS = 3.0
# No console window for anything this backend launches on the user's behalf.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def gateway_port(repo_root: Path, environ: Mapping[str, str] = os.environ) -> int:
    """The gateway's port with the launch scripts' precedence: the root .env, then GATEWAY_PORT."""
    try:
        text = (repo_root / ".env").read_text(encoding="utf-8")
    except OSError:
        text = ""
    match = re.search(r"^\s*GATEWAY_PORT\s*=\s*(\d+)\s*$", text, re.MULTILINE)
    if match:
        return int(match.group(1))
    value = environ.get("GATEWAY_PORT", "").strip()
    return int(value) if value.isdigit() else DEFAULT_GATEWAY_PORT


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=PORT_PROBE_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


class RealSystem:
    def __init__(
        self,
        *,
        repo_root: Path,
        backend_port: int,
        frontend_port: int,
        gateway_port: int,
        run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        popen: Callable[..., Any] = subprocess.Popen,
        probe_gateway: Optional[Callable[[], bool]] = None,
        environ: Mapping[str, str] = os.environ,
    ) -> None:
        self._gateway_dir = repo_root / "gateway"
        self._web_dir = repo_root / "web"
        self._backend_port = backend_port
        self._frontend_port = frontend_port
        self._gateway_port = gateway_port
        self._run = run
        self._popen = popen
        self._probe_gateway = probe_gateway or self._https_probe
        self._environ = environ

    # ------------------------------------------------------------ Docker

    def _docker_desktop_exe(self) -> Path:
        program_files = self._environ.get("ProgramFiles", r"C:\Program Files")
        return Path(program_files) / "Docker" / "Docker" / "Docker Desktop.exe"

    def docker_installed(self) -> bool:
        return shutil.which("docker") is not None and self._docker_desktop_exe().exists()

    def docker_ready(self) -> bool:
        try:
            result = self._run(
                ["docker", "info"],
                capture_output=True,
                timeout=DOCKER_INFO_TIMEOUT_SECONDS,
                creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def start_docker_desktop(self) -> None:
        self._popen([str(self._docker_desktop_exe())], creationflags=NO_WINDOW, close_fds=True)

    # ------------------------------------------------------------ the web interface

    def frontend_up(self) -> bool:
        return _port_open(self._frontend_port)

    def start_frontend(self) -> Any:
        env = {**self._environ, "BACKEND_PORT": str(self._backend_port)}
        if not (self._web_dir / "dist").exists():
            built = self._run(
                "npm run build",
                cwd=self._web_dir,
                env=env,
                shell=True,
                capture_output=True,
                timeout=BUILD_TIMEOUT_SECONDS,
                creationflags=NO_WINDOW,
            )
            if built.returncode != 0:
                raise RemoteStartError("Building the web interface failed")
        return self._popen(
            f"npm run preview -- --port {self._frontend_port}",
            cwd=self._web_dir,
            env=env,
            shell=True,
            creationflags=NO_WINDOW,
        )

    def stop_frontend(self, handle: Any) -> None:
        # npm is a .cmd shim that spawns node, so kill the whole tree, not just the shell.
        self._run(["taskkill", "/PID", str(handle.pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)

    # ------------------------------------------------------------ the gateway container

    def _compose_env(self) -> dict[str, str]:
        return {
            **self._environ,
            "GATEWAY_PORT": str(self._gateway_port),
            "BACKEND_PORT": str(self._backend_port),
            "FRONTEND_PORT": str(self._frontend_port),
        }

    def _compose(self, *args: str, timeout: int) -> subprocess.CompletedProcess:
        return self._run(
            ["docker", "compose", *args],
            cwd=self._gateway_dir,
            env=self._compose_env(),
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=NO_WINDOW,
        )

    def compose_up(self) -> bool:
        try:
            return self._compose("up", "-d", "--build", timeout=COMPOSE_UP_TIMEOUT_SECONDS).returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def compose_down(self) -> bool:
        if not self.docker_ready():
            return True  # no runtime means no container to stop
        try:
            return self._compose("down", timeout=COMPOSE_TIMEOUT_SECONDS).returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def gateway_container_exists(self) -> bool:
        try:
            result = self._compose("ps", "-q", timeout=COMPOSE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return False
        return result.returncode == 0 and bool(result.stdout.strip())

    def gateway_up(self) -> bool:
        return self._probe_gateway()

    def _https_probe(self) -> bool:
        """The gateway answers over TLS and can reach the backend behind it (anything but a 5xx;
        an unauthenticated 401 is the expected answer). The certificate is self-signed, so it is
        not verified - this only checks the local container."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection = http.client.HTTPSConnection(
            "127.0.0.1", self._gateway_port, timeout=GATEWAY_PROBE_TIMEOUT_SECONDS, context=context
        )
        try:
            connection.request("GET", "/api/meta")
            return connection.getresponse().status < 500
        except (OSError, http.client.HTTPException):
            return False
        finally:
            connection.close()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
