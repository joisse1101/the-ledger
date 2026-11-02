"""hooks/chimeScripts/Play-ClaudeChime.ps1, run for real in -DryRun mode.

Every run gets a throwaway state folder (-StateDir) and a fake idle clock (-IdleSeconds), so the
machine's real input idle time, state folder and sound scheme are never touched and no sound plays.
The one non-dry run points -PlayerPath at a program that does not exist.

Guards the promises of the chime hook: it is silent only while the user is present, the AFK flag
forces sound until it expires, alerts arriving together make one sound without ever hiding a
needs-input alert, and nothing ever reaches Claude Code.
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the chime hook is a Windows PowerShell script",
)

SCRIPT = Path(__file__).resolve().parents[2] / "hooks" / "chimeScripts" / "Play-ClaudeChime.ps1"
PAYLOAD = json.dumps({"cwd": "C:\\repo", "session_id": "mock-session"})
AWAY_SECONDS = 300


@pytest.fixture
def state(tmp_path) -> Path:
    return tmp_path / "state"


def _run(kind: str, state: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
         "-Kind", kind, "-StateDir", str(state), *args],
        input=PAYLOAD, capture_output=True, text=True, timeout=60, check=False,
    )


def _decide(kind: str, state: Path, idle_seconds: int = 400) -> str:
    result = _run(kind, state, "-DryRun", "-IdleSeconds", str(idle_seconds))
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


def _write_flag(state: Path, text: str) -> None:
    state.mkdir(parents=True, exist_ok=True)
    (state / "afk.flag").write_text(text, encoding="ascii")


def _utc_in(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_dry_run_plays_when_the_user_has_been_idle_for_400_seconds(state):
    assert _decide("done", state, 400) == "play"


def test_real_run_prints_nothing_and_exits_0_when_the_user_is_present(state):
    result = _run("done", state, "-IdleSeconds", "5")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_unknown_kind_prints_nothing_and_exits_0(state):
    result = _run("bogus", state, "-DryRun", "-IdleSeconds", "400")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_skips_at_299_seconds_idle(state):
    assert _decide("done", state, AWAY_SECONDS - 1) == "skip-present"


def test_plays_at_300_seconds_idle(state):
    assert _decide("done", state, AWAY_SECONDS) == "play"


def test_plays_when_idle_time_cannot_be_read(state):
    assert _decide("done", state, -1) == "play"


def test_plays_for_an_active_user_when_the_afk_flag_expires_in_the_future(state):
    _write_flag(state, _utc_in(600))
    assert _decide("done", state, 5) == "play"


@pytest.mark.parametrize("content", [_utc_in(-60), "not a time", ""])
def test_skips_for_an_active_user_when_the_afk_flag_is_past_or_garbled(state, content):
    _write_flag(state, content)
    assert _decide("done", state, 5) == "skip-present"


def test_skips_for_an_active_user_when_there_is_no_afk_flag(state):
    assert _decide("done", state, 5) == "skip-present"


def test_three_finishes_at_once_play_once(state):
    # Started together because one PowerShell start-up can take over 2 seconds; this also exercises the mutex.
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
               "-Kind", "done", "-StateDir", str(state), "-DryRun", "-IdleSeconds", "400"]
    runs = [subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) for _ in range(3)]
    outputs = [run.communicate(PAYLOAD, timeout=60)[0].strip() for run in runs]
    assert sorted(outputs) == ["play", "skip-merged", "skip-merged"]


def test_needs_input_after_a_finish_still_plays(state):
    assert [_decide("done", state), _decide("needs-input", state)] == ["play", "play"]


def test_finish_after_needs_input_is_merged(state):
    assert [_decide("needs-input", state), _decide("done", state)] == ["play", "skip-merged"]


def test_repeated_needs_input_alerts_play_once(state):
    assert [_decide("needs-input", state), _decide("needs-input", state)] == ["play", "skip-merged"]


@pytest.mark.parametrize("kind", ["done", "needs-input"])
def test_plays_again_when_the_last_sound_is_older_than_5_seconds(state, kind):
    state.mkdir()
    # The script writes its own stamps as UTC with a trailing Z ('o' format), so write the same shape.
    old = (datetime.now(timezone.utc) - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    (state / "done.stamp").write_text(old, encoding="ascii")
    (state / "needs-input.stamp").write_text(old, encoding="ascii")
    assert _decide(kind, state) == "play"


def test_done_and_needs_input_use_two_different_system_sounds():
    table = re.search(r"\$SoundByKind = @\{(.*?)\}", SCRIPT.read_text(encoding="utf-8"))
    sounds = dict(re.findall(r"'([\w-]+)'\s*=\s*'(\w+)'", table.group(1)))
    assert sounds == {"done": "Asterisk", "needs-input": "Hand"}


def test_a_present_user_writes_no_state(state):
    assert _decide("done", state, 5) == "skip-present"
    assert not state.exists()


def test_a_broken_state_folder_and_a_broken_sound_call_still_print_nothing_and_exit_0(tmp_path):
    state_is_a_file = tmp_path / "state"
    state_is_a_file.write_text("not a folder", encoding="ascii")
    result = _run("done", state_is_a_file, "-IdleSeconds", "400", "-PlayerPath", str(tmp_path / "no-such-player.exe"))
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_a_broken_state_folder_still_plays(tmp_path):
    state_is_a_file = tmp_path / "state"
    state_is_a_file.write_text("not a folder", encoding="ascii")
    assert _decide("done", state_is_a_file) == "play"
