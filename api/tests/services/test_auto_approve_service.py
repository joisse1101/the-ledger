"""Switching auto-approve for a live session, without HTTP."""

import pytest

from app import deps
from app.domain.live_snapshot import LiveSnapshot
from app.domain.pending_decisions import PendingDecisions
from app.services import auto_approve_service
from app.services.errors import NotFound


class FakeSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.cwd = "/h/alpha"
        self.pid = 7


@pytest.fixture
def store(monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(deps, "decisions", store)
    monkeypatch.setattr(deps, "live", LiveSnapshot(load_sessions=lambda: [FakeSession("s1")]))
    return store


def test_turning_it_on_approves_the_prompts_already_pending(store):
    store.register("s1", "Edit", {})
    store.register("s1", "AskUserQuestion", {"questions": []})

    assert auto_approve_service.set_enabled("s1", True) == {"auto_approve": True}

    assert [p["tool_name"] for p in store.for_session("s1")] == ["AskUserQuestion"]
    assert store.last_auto_approved("s1")["tool_name"] == "Edit"


def test_turning_it_off(store):
    auto_approve_service.set_enabled("s1", True)
    assert auto_approve_service.set_enabled("s1", False) == {"auto_approve": False}
    assert store.auto_approve_enabled("s1") is False


def test_turning_it_on_twice_is_harmless(store):
    store.register("s1", "Edit", {})
    auto_approve_service.set_enabled("s1", True)
    assert auto_approve_service.set_enabled("s1", True) == {"auto_approve": True}


def test_a_session_that_is_not_live_is_refused(store):
    with pytest.raises(NotFound):
        auto_approve_service.set_enabled("gone", True)
    assert store.auto_approve_enabled("gone") is False
