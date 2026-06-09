from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from article_generator.services.graph_runner import (
    GraphExecutionError,
    GraphOutputMissingError,
    GraphResult,
    GraphRunner,
    GraphValidationError,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_CODE = """\
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_xlabel("X axis")
ax.set_ylabel("Y axis")
"""


def _execute_stub_writes_file(code: str, output_path: Path) -> tuple[str, str]:
    """Fake _execute: simulates a successful subprocess by touching the output file."""
    output_path.write_bytes(b"FAKE_PNG_DATA")
    return "stdout_text", ""


# ---------------------------------------------------------------------------
# validate() — syntax errors
# ---------------------------------------------------------------------------


def test_validate_raises_on_syntax_error():
    with pytest.raises(GraphValidationError, match="Syntax error"):
        GraphRunner().validate("def broken(:")


# ---------------------------------------------------------------------------
# validate() — disallowed imports (AST)
# ---------------------------------------------------------------------------


def test_validate_raises_on_import_os():
    with pytest.raises(GraphValidationError, match="Disallowed import"):
        GraphRunner().validate("import os\n" + VALID_CODE)


def test_validate_raises_on_import_subprocess():
    with pytest.raises(GraphValidationError, match="Disallowed import"):
        GraphRunner().validate("import subprocess\n" + VALID_CODE)


def test_validate_raises_on_from_sys_import():
    with pytest.raises(GraphValidationError, match="Disallowed import"):
        GraphRunner().validate("from sys import argv\n" + VALID_CODE)


# ---------------------------------------------------------------------------
# validate() — disallowed built-in calls (AST)
# ---------------------------------------------------------------------------


def test_validate_raises_on_eval():
    with pytest.raises(GraphValidationError, match="Disallowed function call"):
        GraphRunner().validate(VALID_CODE + "\neval('1+1')\n")


def test_validate_raises_on_exec():
    with pytest.raises(GraphValidationError, match="Disallowed function call"):
        GraphRunner().validate(VALID_CODE + "\nexec('x=1')\n")


# ---------------------------------------------------------------------------
# validate() — disallowed string patterns
# ---------------------------------------------------------------------------


def test_validate_raises_on_plt_show():
    with pytest.raises(GraphValidationError, match="plt.show"):
        GraphRunner().validate(VALID_CODE + "\nplt.show()\n")


def test_validate_raises_on_os_system_pattern():
    with pytest.raises(GraphValidationError, match="os.system"):
        GraphRunner().validate(VALID_CODE + "\nos.system('ls')\n")


def test_validate_raises_on_os_popen_pattern():
    with pytest.raises(GraphValidationError, match="os.popen"):
        GraphRunner().validate(VALID_CODE + "\nos.popen('ls')\n")


# ---------------------------------------------------------------------------
# validate() — axis label requirements
# ---------------------------------------------------------------------------


def test_validate_raises_when_xlabel_missing():
    code = "import matplotlib.pyplot as plt\nfig, ax = plt.subplots()\nax.set_ylabel('Y')\n"
    with pytest.raises(GraphValidationError, match="xlabel"):
        GraphRunner().validate(code)


def test_validate_raises_when_ylabel_missing():
    code = "import matplotlib.pyplot as plt\nfig, ax = plt.subplots()\nax.set_xlabel('X')\n"
    with pytest.raises(GraphValidationError, match="ylabel"):
        GraphRunner().validate(code)


# ---------------------------------------------------------------------------
# validate() — valid code passes
# ---------------------------------------------------------------------------


def test_validate_passes_on_valid_code():
    GraphRunner().validate(VALID_CODE)  # must not raise


def test_validate_accepts_plt_xlabel_form():
    """plt.xlabel() is the functional interface — also valid."""
    code = (
        "import matplotlib.pyplot as plt\n"
        "plt.plot([1], [2])\n"
        "plt.xlabel('X')\n"
        "plt.ylabel('Y')\n"
    )
    GraphRunner().validate(code)  # must not raise


def test_validate_accepts_set_xlabel_form():
    """ax.set_xlabel() is the OO interface — also valid."""
    GraphRunner().validate(VALID_CODE)  # must not raise


# ---------------------------------------------------------------------------
# _build_script() — static helper
# ---------------------------------------------------------------------------


def test_build_script_forces_agg_backend(tmp_path):
    script = GraphRunner._build_script("# code", tmp_path / "graph.png")
    assert "matplotlib.use('Agg')" in script


def test_build_script_sets_agg_before_pyplot(tmp_path):
    script = GraphRunner._build_script("# code", tmp_path / "graph.png")
    agg_pos = script.index("matplotlib.use('Agg')")
    pyplot_pos = script.index("import matplotlib.pyplot as _plt")
    assert agg_pos < pyplot_pos


def test_build_script_embeds_user_code(tmp_path):
    script = GraphRunner._build_script("ax.set_title('test')", tmp_path / "graph.png")
    assert "ax.set_title('test')" in script


def test_build_script_includes_savefig(tmp_path):
    out = tmp_path / "graph.png"
    script = GraphRunner._build_script("# code", out)
    assert "_plt.savefig(" in script
    assert str(out) in script


def test_build_script_closes_all_figures(tmp_path):
    script = GraphRunner._build_script("# code", tmp_path / "graph.png")
    assert "_plt.close('all')" in script


# ---------------------------------------------------------------------------
# _execute() — subprocess behaviour
# ---------------------------------------------------------------------------


def test_execute_raises_execution_error_on_nonzero_exit(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    mock_result = MagicMock(returncode=1, stderr="RuntimeError: boom", stdout="")
    with patch("article_generator.services.graph_runner.subprocess.run", return_value=mock_result):
        with pytest.raises(GraphExecutionError, match="exit 1"):
            runner._execute(VALID_CODE, tmp_path / "graph.png")


def test_execute_raises_execution_error_on_timeout(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch(
        "article_generator.services.graph_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="python", timeout=30),
    ):
        with pytest.raises(GraphExecutionError, match="timed out"):
            runner._execute(VALID_CODE, tmp_path / "graph.png")


def test_execute_returns_stdout_stderr_on_success(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    mock_result = MagicMock(returncode=0, stdout="hello", stderr="warn")
    with patch("article_generator.services.graph_runner.subprocess.run", return_value=mock_result):
        stdout, stderr = runner._execute(VALID_CODE, tmp_path / "graph.png")
    assert stdout == "hello"
    assert stderr == "warn"


def test_execute_cleans_up_temp_file_on_success(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    created_temps: list[str] = []

    def capturing_run(cmd, **kwargs):
        created_temps.append(cmd[1])  # temp script path
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("article_generator.services.graph_runner.subprocess.run", side_effect=capturing_run):
        runner._execute(VALID_CODE, tmp_path / "graph.png")

    assert created_temps, "subprocess.run was never called"
    assert not Path(created_temps[0]).exists(), "temp file was not cleaned up"


# ---------------------------------------------------------------------------
# run() — full public API
# ---------------------------------------------------------------------------


def test_run_returns_graph_result_on_success(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        result = runner.run(VALID_CODE, "graph.png")
    assert isinstance(result, GraphResult)
    assert result.success is True


def test_run_result_output_path_in_assets_dir(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        result = runner.run(VALID_CODE, "graph.png")
    assert result.output_path == tmp_path / "graph.png"


def test_run_result_output_file_exists(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        result = runner.run(VALID_CODE, "graph.png")
    assert result.output_path.exists()


def test_run_result_file_format_png(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        result = runner.run(VALID_CODE, "graph.png")
    assert result.file_format == "png"


def test_run_result_file_format_pdf(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)

    def _stub(code, output_path):
        output_path.write_bytes(b"%PDF-fake")
        return "", ""

    with patch.object(runner, "_execute", side_effect=_stub):
        result = runner.run(VALID_CODE, "graph.pdf")
    assert result.file_format == "pdf"


def test_run_result_file_size_matches_written_bytes(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    payload = b"FAKE_DATA_12345"

    def _stub(code, output_path):
        output_path.write_bytes(payload)
        return "", ""

    with patch.object(runner, "_execute", side_effect=_stub):
        result = runner.run(VALID_CODE, "graph.png")
    assert result.file_size_bytes == len(payload)


def test_run_result_duration_is_non_negative(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        result = runner.run(VALID_CODE, "graph.png")
    assert result.duration_seconds >= 0


def test_run_result_captures_stdout_stderr(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)

    def _stub(code, output_path):
        output_path.write_bytes(b"data")
        return "my_stdout", "my_stderr"

    with patch.object(runner, "_execute", side_effect=_stub):
        result = runner.run(VALID_CODE, "graph.png")
    assert result.stdout == "my_stdout"
    assert result.stderr == "my_stderr"


def test_run_default_filename_is_graph_png(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        result = runner.run(VALID_CODE)
    assert result.output_path.name == "graph.png"


def test_run_creates_assets_dir_when_missing(tmp_path):
    assets = tmp_path / "new_assets_dir"
    runner = GraphRunner(assets_dir=assets)
    with patch.object(runner, "_execute", side_effect=_execute_stub_writes_file):
        runner.run(VALID_CODE, "graph.png")
    assert assets.is_dir()


def test_run_raises_validation_error_without_calling_execute(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute") as mock_exec:
        with pytest.raises(GraphValidationError):
            runner.run("def broken(:", "graph.png")
        mock_exec.assert_not_called()


def test_run_raises_output_missing_error_when_no_file_produced(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)

    def _stub(code, output_path):
        return "", ""  # success exit but no file written

    with patch.object(runner, "_execute", side_effect=_stub):
        with pytest.raises(GraphOutputMissingError):
            runner.run(VALID_CODE, "graph.png")


def test_run_propagates_execution_error(tmp_path):
    runner = GraphRunner(assets_dir=tmp_path)
    with patch.object(runner, "_execute", side_effect=GraphExecutionError("timed out")):
        with pytest.raises(GraphExecutionError, match="timed out"):
            runner.run(VALID_CODE, "graph.png")
