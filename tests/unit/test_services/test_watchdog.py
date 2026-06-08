from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from article_generator.services.watchdog import AgentTimeoutError, Watchdog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner(
    name: str,
    *,
    alive: bool = True,
    pid: int | None = 1000,
    exitcode: int | None = None,
    timeout: int = 300,
) -> MagicMock:
    r = MagicMock(name=f"runner-{name}")
    r.agent_name = name
    r.pid = pid
    r.is_alive.return_value = alive
    r.exitcode = exitcode
    r.timeout = timeout
    return r


def _make_watchdog(runners, poll_interval: float = 0.05) -> Watchdog:
    return Watchdog(runners=runners, poll_interval=poll_interval)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def test_start_registers_all_runners():
    runners = [_runner("researcher"), _runner("writer")]
    wd = _make_watchdog(runners)
    wd.start()
    wd.stop()
    assert wd.get_status("researcher").agent_name == "researcher"
    assert wd.get_status("writer").agent_name == "writer"


def test_start_sets_initial_status_running():
    r = _runner("researcher")
    wd = _make_watchdog([r])
    wd.start()
    wd.stop()
    assert wd.get_status("researcher").status == "running"


def test_last_error_initially_none():
    wd = _make_watchdog([_runner("researcher")])
    wd.start()
    wd.stop()
    assert wd.last_error is None


def test_all_healthy_true_when_all_running():
    runners = [_runner("researcher"), _runner("writer")]
    wd = _make_watchdog(runners)
    wd.start()
    wd.stop()
    assert wd.all_healthy() is True


def test_get_status_raises_key_error_for_unknown_agent():
    wd = _make_watchdog([_runner("researcher")])
    wd.start()
    wd.stop()
    with pytest.raises(KeyError):
        wd.get_status("nonexistent")


# ---------------------------------------------------------------------------
# Normal exit (exitcode == 0) → status "done"
# ---------------------------------------------------------------------------

def test_process_normal_exit_sets_status_done():
    r = _runner("researcher", alive=False, exitcode=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("researcher").status == "done"


def test_process_normal_exit_sets_finished_at():
    r = _runner("researcher", alive=False, exitcode=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("researcher").finished_at is not None


def test_process_normal_exit_leaves_all_healthy():
    r = _runner("researcher", alive=False, exitcode=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.all_healthy() is True


def test_process_normal_exit_leaves_last_error_none():
    r = _runner("researcher", alive=False, exitcode=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.last_error is None


# ---------------------------------------------------------------------------
# Crash (exitcode != 0) → status "error"
# ---------------------------------------------------------------------------

def test_crashed_process_sets_status_error():
    r = _runner("writer", alive=False, exitcode=1)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("writer").status == "error"


def test_crashed_process_sets_finished_at():
    r = _runner("writer", alive=False, exitcode=1)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("writer").finished_at is not None


def test_crashed_process_makes_all_healthy_false():
    r = _runner("writer", alive=False, exitcode=1)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.all_healthy() is False


def test_crashed_process_does_not_set_last_error():
    # crash → "error" status, but AgentTimeoutError is only for timeouts
    r = _runner("writer", alive=False, exitcode=1)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.last_error is None


@pytest.mark.parametrize("code", [-1, -9, 2, 127])
def test_non_zero_exit_codes_all_set_error(code: int):
    r = _runner("editor", alive=False, exitcode=code)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("editor").status == "error"


# ---------------------------------------------------------------------------
# Timeout → terminate + status "timeout" + AgentTimeoutError stored
# ---------------------------------------------------------------------------

def test_timeout_terminates_process():
    r = _runner("researcher", alive=True, timeout=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    r.terminate.assert_called()


def test_timeout_sets_status_timeout():
    r = _runner("researcher", alive=True, timeout=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("researcher").status == "timeout"


def test_timeout_sets_finished_at():
    r = _runner("researcher", alive=True, timeout=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("researcher").finished_at is not None


def test_timeout_stores_agent_timeout_error():
    r = _runner("researcher", alive=True, timeout=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert isinstance(wd.last_error, AgentTimeoutError)


def test_timeout_error_message_contains_agent_name():
    r = _runner("graph_generator", alive=True, timeout=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert "graph_generator" in str(wd.last_error)


def test_timeout_makes_all_healthy_false():
    r = _runner("researcher", alive=True, timeout=0)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.all_healthy() is False


# ---------------------------------------------------------------------------
# all_healthy — mixed states
# ---------------------------------------------------------------------------

def test_all_healthy_false_when_one_of_many_crashes():
    runners = [
        _runner("researcher", alive=False, exitcode=0),   # done
        _runner("writer",     alive=False, exitcode=1),   # error
        _runner("editor",     alive=True,  timeout=999),  # still running
    ]
    wd = _make_watchdog(runners)
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.all_healthy() is False


def test_all_healthy_true_when_all_done():
    runners = [
        _runner("researcher", alive=False, exitcode=0),
        _runner("writer",     alive=False, exitcode=0),
    ]
    wd = _make_watchdog(runners)
    wd.start()
    time.sleep(0.15)
    wd.stop()
    assert wd.all_healthy() is True


# ---------------------------------------------------------------------------
# pid backfill — process starts after Watchdog
# ---------------------------------------------------------------------------

def test_pid_backfilled_when_process_starts_after_watchdog():
    r = _runner("researcher", pid=None)   # not yet spawned
    wd = _make_watchdog([r])
    wd.start()
    # Simulate process starting mid-flight
    r.pid = 5678
    time.sleep(0.15)
    wd.stop()
    assert wd.get_status("researcher").pid == 5678


def test_unstarted_process_stays_running_status():
    r = _runner("researcher", pid=None, alive=False, exitcode=None)
    wd = _make_watchdog([r])
    wd.start()
    time.sleep(0.15)
    wd.stop()
    # pid is None → skip check → status stays "running"
    assert wd.get_status("researcher").status == "running"
