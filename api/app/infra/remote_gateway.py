"""Remote mode's lifecycle: bring up whatever other devices need to connect, and take it down again.

Turning Remote mode on runs three steps in order, each skipped when already satisfied: the container
runtime (Docker Desktop), the web interface (the gateway proxies `/` to it), and the gateway
container. The state is `off`, `starting` (with the current step), `ready` (the gateway answered)
or `failed` (with a reason). Turning it off, or the 8 hour timer, stops the gateway and the web
interface only if this module started it; Docker Desktop is never stopped.

All process control goes through the `System` protocol (see remote_system.py for the real one), so
this module is pure state and ordering and its tests use fakes. Nothing here touches disk.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional, Protocol

log = logging.getLogger("ledger.remote")

REMOTE_MODE_TTL_SECONDS = 8 * 60 * 60.0
DOCKER_TIMEOUT_SECONDS = 120.0
FRONTEND_TIMEOUT_SECONDS = 60.0
GATEWAY_TIMEOUT_SECONDS = 60.0
POLL_SECONDS = 1.0
# A failure stays visible this long, then the state reads as off again.
FAILED_VISIBLE_SECONDS = 30.0

OFF = "off"
STARTING = "starting"
READY = "ready"
FAILED = "failed"

STEP_DOCKER = "docker"
STEP_FRONTEND = "frontend"
STEP_GATEWAY = "gateway"


class RemoteStartError(Exception):
    """A step could not be completed; the message is the reason shown to the user."""


class System(Protocol):
    """The side effects the lifecycle needs. A frontend handle is opaque to this module."""

    def docker_installed(self) -> bool: ...
    def docker_ready(self) -> bool: ...
    def start_docker_desktop(self) -> None: ...
    def frontend_up(self) -> bool: ...
    def start_frontend(self) -> Any: ...
    def stop_frontend(self, handle: Any) -> None: ...
    def compose_up(self) -> bool: ...
    def compose_down(self) -> bool: ...
    def gateway_container_exists(self) -> bool: ...
    def gateway_up(self) -> bool: ...
    def sleep(self, seconds: float) -> None: ...


def _spawn_thread(work: Callable[[], None]) -> None:
    threading.Thread(target=work, name="remote-mode", daemon=True).start()


class _TimerHandle:
    def __init__(self, timer: threading.Timer) -> None:
        self._timer = timer

    def cancel(self) -> None:
        self._timer.cancel()


def _schedule(delay: float, work: Callable[[], None]) -> _TimerHandle:
    timer = threading.Timer(delay, work)
    timer.daemon = True
    timer.start()
    return _TimerHandle(timer)


class RemoteGateway:
    def __init__(
        self,
        system: System,
        *,
        on_start: Callable[[], None],
        on_ready: Callable[[], None],
        on_off: Callable[[], None],
        ttl: float = REMOTE_MODE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        spawn: Callable[[Callable[[], None]], None] = _spawn_thread,
        schedule: Callable[[float, Callable[[], None]], Any] = _schedule,
        docker_timeout: float = DOCKER_TIMEOUT_SECONDS,
        frontend_timeout: float = FRONTEND_TIMEOUT_SECONDS,
        gateway_timeout: float = GATEWAY_TIMEOUT_SECONDS,
    ) -> None:
        self._system = system
        self._on_start = on_start
        self._on_ready = on_ready
        self._on_off = on_off
        self._ttl = ttl
        self._clock = clock
        self._spawn = spawn
        self._schedule = schedule
        self._docker_timeout = docker_timeout
        self._frontend_timeout = frontend_timeout
        self._gateway_timeout = gateway_timeout

        self._lock = threading.Lock()
        self._state = OFF
        self._step: Optional[str] = None
        self._reason: Optional[str] = None
        self._failed_at = 0.0
        self._generation = 0  # bumped by every start/stop so a superseded worker stands down
        self._cancel = threading.Event()
        self._frontend: Any = None  # set only when this module started the web interface
        self._expiry: Any = None

    # ------------------------------------------------------------ reading

    def status(self) -> dict[str, Optional[str]]:
        """`{state, step, reason}` for the API. A failure fades back to `off` after a while."""
        with self._lock:
            if self._state == FAILED and self._clock() - self._failed_at > FAILED_VISIBLE_SECONDS:
                self._state, self._reason = OFF, None
            return {"state": self._state, "step": self._step, "reason": self._reason}

    def is_ready(self) -> bool:
        with self._lock:
            return self._state == READY

    # ------------------------------------------------------------ turning on and off

    def start(self) -> None:
        """Begin bringing everything up in the background. A no-op while starting or ready.

        `on_start` runs under the lock on the way in; `on_off` also runs under it on every way out
        (`stop()` and a failed start), so a callback must not call back into this object."""
        with self._lock:
            if self._state in (STARTING, READY):
                return
            self._generation += 1
            generation = self._generation
            self._cancel = threading.Event()
            cancel = self._cancel
            self._state, self._step, self._reason = STARTING, STEP_DOCKER, None
            self._on_start()
        self._spawn(lambda: self._run(generation, cancel))

    def stop(self) -> None:
        """Turn Remote mode off now: cancel a start in progress and tear down. Idempotent."""
        with self._lock:
            self._generation += 1
            self._cancel.set()
            self._state, self._step, self._reason = OFF, None, None
            expiry, self._expiry = self._expiry, None
            self._on_off()  # before the teardown, which can wait on Docker: revoke first
        if expiry is not None:
            expiry.cancel()
        self._teardown()

    def stop_leftovers(self) -> None:
        """At backend startup: Remote mode is off, so close a gateway an earlier backend left up.
        Never starts Docker for this, and leaves a running web interface alone."""
        if self._system.docker_ready() and self._system.gateway_container_exists():
            self._system.compose_down()

    # ------------------------------------------------------------ the worker

    def _run(self, generation: int, cancel: threading.Event) -> None:
        steps = (
            (STEP_DOCKER, self._ensure_docker),
            (STEP_FRONTEND, self._ensure_frontend),
            (STEP_GATEWAY, self._ensure_gateway),
        )
        try:
            for name, ensure in steps:
                if not self._set_step(generation, name):
                    return
                ensure(cancel)
            self._become_ready(generation)
        except RemoteStartError as err:
            self._fail(generation, str(err))
        except Exception:
            log.exception("remote mode failed unexpectedly")
            self._fail(generation, "Remote mode failed unexpectedly; see the backend log")

    def _set_step(self, generation: int, step: str) -> bool:
        """Record the step, or tear down and report False if this run was superseded."""
        with self._lock:
            if generation == self._generation:
                self._step = step
                return True
        self._teardown()
        return False

    def _become_ready(self, generation: int) -> None:
        with self._lock:
            if generation != self._generation:
                superseded = True
            else:
                superseded = False
                self._state, self._step = READY, None
                self._expiry = self._schedule(self._ttl, self.stop)
        if superseded:
            self._teardown()
            return
        self._on_ready()

    def _fail(self, generation: int, reason: str) -> None:
        self._teardown()
        with self._lock:
            if generation == self._generation:
                self._state, self._step, self._reason = FAILED, None, reason
                self._failed_at = self._clock()
                self._on_off()

    # ------------------------------------------------------------ steps

    def _ensure_docker(self, cancel: threading.Event) -> None:
        if self._system.docker_ready():
            return
        if not self._system.docker_installed():
            raise RemoteStartError("Docker Desktop is not installed")
        self._system.start_docker_desktop()
        self._wait_until(self._system.docker_ready, self._docker_timeout, cancel, "Docker did not start in time")

    def _ensure_frontend(self, cancel: threading.Event) -> None:
        if self._system.frontend_up():
            return
        handle = self._system.start_frontend()
        with self._lock:
            self._frontend = handle
        self._wait_until(self._system.frontend_up, self._frontend_timeout, cancel, "The web interface did not start in time")

    def _ensure_gateway(self, cancel: threading.Event) -> None:
        if not self._system.compose_up():
            raise RemoteStartError("The gateway container failed to start")
        self._wait_until(self._system.gateway_up, self._gateway_timeout, cancel, "The gateway did not answer in time")

    def _wait_until(self, check: Callable[[], bool], timeout: float, cancel: threading.Event, failure: str) -> None:
        deadline = self._clock() + timeout
        while not check():
            if cancel.is_set():
                return  # the caller notices the supersession at the next step boundary
            if self._clock() >= deadline:
                raise RemoteStartError(failure)
            self._system.sleep(POLL_SECONDS)

    # ------------------------------------------------------------ teardown

    def _teardown(self) -> None:
        """Stop the gateway, and the web interface only if this module started it. Idempotent."""
        with self._lock:
            handle, self._frontend = self._frontend, None
        if not self._system.compose_down():
            log.warning("docker compose down for the gateway did not succeed")
        if handle is not None:
            self._system.stop_frontend(handle)
