from __future__ import annotations

# Integration tests for GraphRunner — T-050
#
# Verifies that representative GraphGeneratorAgent code samples execute
# correctly inside a real subprocess and produce image files in assets/.
#
# No API keys required.  Skipped automatically if matplotlib is not installed.
import pytest

from article_generator.constants import GRAPH_TIMEOUT_SECONDS
from article_generator.services.graph_runner import GraphResult, GraphRunner

pytest.importorskip("matplotlib")  # skip whole module if matplotlib absent

# ---------------------------------------------------------------------------
# Representative code samples mirroring GraphGeneratorAgent output
# ---------------------------------------------------------------------------

# Minimal valid plot — simplest possible agent output
_SIMPLE_LINE_PLOT = """\
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([1, 2, 3, 4, 5], [0.90, 0.75, 0.55, 0.35, 0.20], linewidth=2, color="steelblue")
ax.set_xlabel("Epoch", fontsize=12)
ax.set_ylabel("Loss", fontsize=12)
ax.set_title("Training Loss over Epochs", fontsize=13)
ax.grid(True, alpha=0.3)
"""

# Multi-series plot with numpy — typical ML paper graph
_MULTI_SERIES_WITH_NUMPY = """\
import matplotlib.pyplot as plt
import numpy as np

epochs = np.arange(1, 21)
rng = np.random.default_rng(42)
train_loss = np.exp(-0.10 * epochs) + 0.02 * rng.random(20)
val_loss   = np.exp(-0.08 * epochs) + 0.03 * rng.random(20)

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(epochs, train_loss, label="Training Loss",   color="#1f77b4", linewidth=2)
ax.plot(epochs, val_loss,   label="Validation Loss", color="#ff7f0e", linewidth=2, linestyle="--")
ax.set_xlabel("Epoch", fontsize=12)
ax.set_ylabel("Cross-Entropy Loss", fontsize=12)
ax.set_title("Model Convergence over Training", fontsize=13)
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
fig.tight_layout()
"""

# Bar chart — comparison figure typical in evaluation sections
_BAR_CHART = """\
import matplotlib.pyplot as plt

models    = ["Baseline", "CNN", "Transformer", "Proposed"]
accuracy  = [0.72, 0.81, 0.88, 0.92]
colors    = ["#aec7e8", "#1f77b4", "#ffbb78", "#2ca02c"]

fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(models, accuracy, color=colors, edgecolor="black", linewidth=0.7)
ax.set_xlabel("Model", fontsize=12)
ax.set_ylabel("Accuracy", fontsize=12)
ax.set_title("Model Accuracy Comparison", fontsize=13)
ax.set_ylim(0, 1.05)
for bar, val in zip(bars, accuracy):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        val + 0.01,
        f"{val:.2f}",
        ha="center", va="bottom", fontsize=10,
    )
"""

# Agent code that includes its own backend declaration — must not double-fail
_WITH_OWN_AGG_DECLARATION = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(5, 3))
ax.plot([0, 1, 2, 3], [0, 1, 4, 9], marker="o", linewidth=2)
ax.set_xlabel("x")
ax.set_ylabel("y = x²")
ax.set_title("Quadratic Growth")
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def runner(tmp_path):
    return GraphRunner(assets_dir=tmp_path)


# ---------------------------------------------------------------------------
# Core execution — PNG output
# ---------------------------------------------------------------------------


def test_simple_line_plot_produces_png(runner, tmp_path):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert result.success is True
    assert result.output_path == tmp_path / "graph.png"
    assert result.output_path.exists()


def test_simple_line_plot_file_is_non_empty(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert result.file_size_bytes > 0


def test_multi_series_numpy_plot_produces_file(runner):
    result = runner.run(_MULTI_SERIES_WITH_NUMPY, "graph.png")
    assert result.success is True
    assert result.output_path.exists()
    assert result.file_size_bytes > 0


def test_bar_chart_produces_file(runner):
    result = runner.run(_BAR_CHART, "graph.png")
    assert result.success is True
    assert result.output_path.exists()


# ---------------------------------------------------------------------------
# PDF output
# ---------------------------------------------------------------------------


def test_run_produces_pdf_output(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.pdf")
    assert result.success is True
    assert result.output_path.exists()
    assert result.file_format == "pdf"
    assert result.file_size_bytes > 0


def test_pdf_and_png_both_succeed(runner, tmp_path):
    """Verify both supported output formats work in the same session."""
    pdf_result = runner.run(_SIMPLE_LINE_PLOT, "graph.pdf")
    png_result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert pdf_result.success is True
    assert png_result.success is True


# ---------------------------------------------------------------------------
# Agent code with its own Agg declaration
# ---------------------------------------------------------------------------


def test_agent_code_with_own_backend_declaration(runner):
    """Agent may include matplotlib.use('Agg') — the double call must not fail."""
    result = runner.run(_WITH_OWN_AGG_DECLARATION, "graph.png")
    assert result.success is True
    assert result.output_path.exists()


# ---------------------------------------------------------------------------
# GraphResult contract
# ---------------------------------------------------------------------------


def test_result_is_graph_result_instance(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert isinstance(result, GraphResult)


def test_result_file_format_is_png(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert result.file_format == "png"


def test_result_duration_is_positive(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert result.duration_seconds > 0


def test_result_duration_within_timeout(runner):
    result = runner.run(_MULTI_SERIES_WITH_NUMPY, "graph.png")
    assert result.duration_seconds < GRAPH_TIMEOUT_SECONDS


def test_result_stdout_is_string(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert isinstance(result.stdout, str)


def test_result_stderr_is_string(runner):
    result = runner.run(_SIMPLE_LINE_PLOT, "graph.png")
    assert isinstance(result.stderr, str)


# ---------------------------------------------------------------------------
# Output in assets/ directory (T-050 DoD: file saved to assets/)
# ---------------------------------------------------------------------------


def test_output_saved_inside_assets_dir(tmp_path):
    """The T-050 Definition of Done: figure must be in the configured assets dir."""
    assets = tmp_path / "assets"
    result = GraphRunner(assets_dir=assets).run(_MULTI_SERIES_WITH_NUMPY, "graph.png")
    assert result.output_path.parent == assets
    assert result.output_path.exists()
