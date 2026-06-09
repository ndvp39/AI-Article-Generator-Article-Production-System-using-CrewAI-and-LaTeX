from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.tools.code_interpreter_tool import LocalCodeInterpreterTool

_BASE = "article_generator.services.tools.code_interpreter_tool"


@pytest.fixture()
def tool() -> LocalCodeInterpreterTool:
    return LocalCodeInterpreterTool()


def _make_proc(stdout="", stderr="", returncode=0):
    p = MagicMock()
    p.stdout = stdout
    p.stderr = stderr
    p.returncode = returncode
    return p


# ---------------------------------------------------------------------------
# _run — success path
# ---------------------------------------------------------------------------


def test_run_returns_exit_code_zero(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc(returncode=0)):
        result = tool._run("print('hi')")
    assert "EXIT CODE: 0" in result


def test_run_includes_stdout_when_present(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc(stdout="hello\n")):
        result = tool._run("print('hello')")
    assert "STDOUT:" in result
    assert "hello" in result


def test_run_includes_stderr_when_present(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc(stderr="warning\n")):
        result = tool._run("import warnings")
    assert "STDERR:" in result
    assert "warning" in result


def test_run_omits_stdout_section_when_empty(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc(stdout="")):
        result = tool._run("x = 1")
    assert "STDOUT:" not in result


def test_run_omits_stderr_section_when_empty(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc(stderr="")):
        result = tool._run("x = 1")
    assert "STDERR:" not in result


def test_run_reports_files_produced_when_figures_written(tool, tmp_path):
    """Verify the FILES PRODUCED line when figures/ dir has content."""
    class _FakeTmpDir:
        def __init__(self):
            self._d = tmp_path
        def __enter__(self):
            return str(self._d)
        def __exit__(self, *a):
            pass

    def _fake_run(*a, **kw):
        (tmp_path / "figures" / "graph.pdf").write_bytes(b"%PDF")
        return _make_proc()

    with patch(f"{_BASE}.tempfile.TemporaryDirectory", return_value=_FakeTmpDir()):
        with patch(f"{_BASE}.subprocess.run", side_effect=_fake_run):
            result = tool._run("plt.savefig('figures/graph.pdf')")

    assert "FILES PRODUCED:" in result
    assert "graph.pdf" in result


def test_run_reports_no_files_when_figures_empty(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc()):
        result = tool._run("x = 1")
    assert "FILES PRODUCED: none" in result


def test_run_nonzero_exit_code_included(tool):
    with patch(f"{_BASE}.subprocess.run", return_value=_make_proc(returncode=1, stderr="error")):
        result = tool._run("raise ValueError('oops')")
    assert "EXIT CODE: 1" in result


# ---------------------------------------------------------------------------
# _run — timeout path
# ---------------------------------------------------------------------------


def test_run_returns_timeout_message_on_timeout(tool):
    with patch(
        f"{_BASE}.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="python", timeout=30),
    ):
        result = tool._run("import time; time.sleep(999)")
    assert "TIMEOUT" in result


# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------


def test_tool_has_name(tool):
    assert tool.name != ""


def test_tool_has_description(tool):
    assert tool.description != ""
