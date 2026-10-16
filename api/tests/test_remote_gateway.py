"""Remote mode's lifecycle with a fake System: ordering, skipping, failures, cancellation, teardown."""

import pytest

from remote_gateway import RemoteGateway


class FakeSystem:
    """Records every call. `docker_after` / `frontend_after` / `gateway_after` are how many polls
    each takes to come up (None = never); the clock advances one second per sleep."""

    def __init__(self, *, docker=True, installed=True, frontend=True, docker_after=0, frontend_after=0,
                 gateway_after=0, compose_up_ok=True):
        self.docker_running = docker
        self.installed = installed
        self.frontend_running = frontend
        self.docker_after, self.frontend_after, self.gateway_after = docker_after, frontend_after, gateway_after
        self.compose_up_ok = compose_up_ok
        self.gateway_running = False
        self.calls: list[str] = []
        self.now = 0.0
        self.on_sleep = None
        self._polls = {"docker": 0, "frontend": 0, "gateway": 0}

    def _poll(self, name, running, after):
        if running:
            return True
        if after is None:
            return False
        self._polls[name] += 1
        return self._polls[name] > after

    def docker_installed(self):
        return self.installed

    def docker_ready(self):
        if self.docker_running:
            return True
        self.docker_running = self._poll("docker", False, self.docker_after if self.calls.count("start_docker") else None)
        return self.docker_running

    def start_docker_desktop(self):
        self.calls.append("start_docker")

    def frontend_up(self):
        if self.frontend_running:
            return True
        self.frontend_running = self._poll("frontend", False, self.frontend_after if self.calls.count("start_frontend") else None)
        return self.frontend_running

    def start_frontend(self):
        self.calls.append("start_frontend")
        return "frontend-handle"

    def stop_frontend(self, handle):
        self.calls.append(f"stop_frontend:{handle}")
        self.frontend_running = False

    def compose_up(self):
        self.calls.append("compose_up")
        return self.compose_up_ok

    def compose_down(self):
        self.calls.append("compose_down")
        self.gateway_running = False
        return True

    def gateway_container_exists(self):
        return self.gateway_running

    def gateway_up(self):
        if not self.compose_up_ok:
            return False
        self.gateway_running = self._poll("gateway", False, self.gateway_after)
        return self.gateway_running

    def sleep(self, seconds):
        self.now += seconds
        if self.on_sleep:
            self.on_sleep()


class Hooks:
    def __init__(self):
        self.events: list[str] = []
        self.scheduled: list[tuple[float, object]] = []

    def on_ready(self):
        self.events.append("ready")

    def on_off(self):
        self.events.append("off")

    def schedule(self, delay, work):
        self.scheduled.append((delay, work))
        return type("Handle", (), {"cancel": lambda self_: self.events.append("expiry-cancelled")})()


def _gateway(system, hooks=None, **kwargs):
    hooks = hooks or Hooks()
    gateway = RemoteGateway(
        system,
        on_ready=hooks.on_ready,
        on_off=hooks.on_off,
        clock=lambda: system.now,
        spawn=lambda work: work(),
        schedule=hooks.schedule,
        **kwargs,
    )
    return gateway, hooks


def test_starts_off():
    gateway, _ = _gateway(FakeSystem())
    assert gateway.status() == {"state": "off", "step": None, "reason": None}
    assert not gateway.is_ready()


def test_everything_already_running_goes_straight_to_ready():
    system = FakeSystem()
    gateway, hooks = _gateway(system)
    gateway.start()
    assert gateway.status()["state"] == "ready"
    assert gateway.is_ready()
    assert hooks.events == ["ready"]
    assert system.calls == ["compose_up"]  # docker and the frontend were skipped


def test_turning_on_from_nothing_starts_each_step_in_order():
    system = FakeSystem(docker=False, frontend=False, docker_after=2, frontend_after=1, gateway_after=1)
    gateway, _ = _gateway(system)
    gateway.start()
    assert gateway.status()["state"] == "ready"
    assert system.calls == ["start_docker", "start_frontend", "compose_up"]


def test_ready_arms_the_eight_hour_expiry():
    gateway, hooks = _gateway(FakeSystem())
    gateway.start()
    assert [delay for delay, _ in hooks.scheduled] == [8 * 60 * 60.0]


def test_expiry_turns_it_off_and_closes_the_gateway():
    system = FakeSystem()
    gateway, hooks = _gateway(system)
    gateway.start()
    _, expire = hooks.scheduled[0]
    expire()
    assert gateway.status()["state"] == "off"
    assert "compose_down" in system.calls
    assert hooks.events[-1] == "off"


def test_starting_while_ready_does_nothing():
    system = FakeSystem()
    gateway, hooks = _gateway(system)
    gateway.start()
    gateway.start()
    assert system.calls == ["compose_up"]
    assert hooks.events == ["ready"]


def test_docker_not_installed_fails_with_the_reason():
    system = FakeSystem(docker=False, installed=False)
    gateway, hooks = _gateway(system)
    gateway.start()
    assert gateway.status() == {"state": "failed", "step": None, "reason": "Docker Desktop is not installed"}
    assert "ready" not in hooks.events
    assert "compose_up" not in system.calls


def test_docker_that_never_comes_up_times_out():
    system = FakeSystem(docker=False, docker_after=None)
    gateway, _ = _gateway(system, docker_timeout=5)
    gateway.start()
    assert gateway.status()["reason"] == "Docker did not start in time"
    assert system.now >= 5


def test_a_failure_stops_the_frontend_it_started():
    system = FakeSystem(frontend=False, frontend_after=0, compose_up_ok=False)
    gateway, _ = _gateway(system)
    gateway.start()
    assert gateway.status()["state"] == "failed"
    assert system.calls[-2:] == ["compose_down", "stop_frontend:frontend-handle"]


def test_a_gateway_that_never_answers_fails():
    system = FakeSystem(gateway_after=None)
    gateway, _ = _gateway(system, gateway_timeout=3)
    gateway.start()
    assert gateway.status() == {"state": "failed", "step": None, "reason": "The gateway did not answer in time"}


def test_a_failure_fades_back_to_off():
    system = FakeSystem(docker=False, installed=False)
    gateway, _ = _gateway(system)
    gateway.start()
    system.now += 31
    assert gateway.status()["state"] == "off"


def test_failed_can_be_started_again():
    system = FakeSystem(docker=False, installed=False)
    gateway, _ = _gateway(system)
    gateway.start()
    system.installed, system.docker_running = True, True
    gateway.start()
    assert gateway.status()["state"] == "ready"


def test_turning_off_closes_the_gateway_and_the_frontend_it_started():
    system = FakeSystem(frontend=False)
    gateway, hooks = _gateway(system)
    gateway.start()
    gateway.stop()
    assert gateway.status()["state"] == "off"
    assert system.calls[-2:] == ["compose_down", "stop_frontend:frontend-handle"]
    assert hooks.events[-2:] == ["expiry-cancelled", "off"]


def test_turning_off_leaves_a_frontend_that_was_already_running():
    system = FakeSystem(frontend=True)
    gateway, _ = _gateway(system)
    gateway.start()
    gateway.stop()
    assert "compose_down" in system.calls
    assert not any(call.startswith("stop_frontend") for call in system.calls)
    assert system.frontend_running


def test_stop_is_idempotent():
    system = FakeSystem()
    gateway, hooks = _gateway(system)
    gateway.stop()
    gateway.stop()
    assert gateway.status()["state"] == "off"
    assert hooks.events == ["off", "off"]


def test_turning_off_while_starting_cancels_and_tears_down():
    system = FakeSystem(docker=False, docker_after=10)
    gateway, hooks = _gateway(system)
    system.on_sleep = gateway.stop  # the user turns it off during the first wait
    gateway.start()
    assert gateway.status()["state"] == "off"
    assert "compose_up" not in system.calls  # never went on to the later steps
    assert "ready" not in hooks.events
    assert "compose_down" in system.calls


def test_a_cancel_during_the_last_step_does_not_become_ready():
    system = FakeSystem(gateway_after=5)
    gateway, hooks = _gateway(system)
    system.on_sleep = gateway.stop
    gateway.start()
    assert gateway.status()["state"] == "off"
    assert "ready" not in hooks.events
    assert system.calls[-1] == "compose_down"


def test_unexpected_errors_become_a_failed_state(caplog):
    class Boom(FakeSystem):
        def compose_up(self):
            raise OSError("pipe closed")

    gateway, _ = _gateway(Boom())
    gateway.start()
    status = gateway.status()
    assert status["state"] == "failed"
    assert "backend log" in status["reason"]
    assert "pipe closed" in caplog.text


def test_leftover_gateway_is_stopped_at_startup():
    system = FakeSystem()
    system.gateway_running = True
    gateway, _ = _gateway(system)
    gateway.stop_leftovers()
    assert system.calls == ["compose_down"]


def test_nothing_to_stop_at_startup_when_docker_is_down_or_no_container():
    down = FakeSystem(docker=False)
    down.gateway_running = True
    _gateway(down)[0].stop_leftovers()
    assert down.calls == []  # never starts Docker just to clean up

    idle = FakeSystem()
    _gateway(idle)[0].stop_leftovers()
    assert idle.calls == []


def test_startup_cleanup_leaves_a_running_frontend_alone():
    system = FakeSystem(frontend=True)
    system.gateway_running = True
    _gateway(system)[0].stop_leftovers()
    assert system.frontend_running and not any(c.startswith("stop_frontend") for c in system.calls)
