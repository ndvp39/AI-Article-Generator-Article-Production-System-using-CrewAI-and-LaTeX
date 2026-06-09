from __future__ import annotations

import ast
import logging
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from article_generator.constants import ASSETS_DIR, GRAPH_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Top-level module names the agent's graph code must not import
_DISALLOWED_IMPORTS = frozenset({
    "os", "sys", "subprocess", "socket", "shutil", "pathlib", "io", "builtins",
})

# Built-in names that must not be called directly
_DISALLOWED_CALLS = frozenset({"eval", "exec", "__import__", "open", "compile"})

# String patterns that must not appear anywhere in the code
_DISALLOWED_PATTERNS = ("os.system", "os.popen", "plt.show")


@dataclass
class GraphResult:
    success: bool
    output_path: Path
    file_format: str          # "pdf" or "png"
    file_size_bytes: int
    duration_seconds: float
    stdout: str
    stderr: str


class GraphValidationError(Exception):
    """Raised when graph code fails AST security or quality validation."""


class GraphExecutionError(Exception):
    """Raised when the graph subprocess exits with an error or times out."""


class GraphOutputMissingError(Exception):
    """Raised when execution succeeds but no output file was produced."""


class GraphRunner:
    """Validates and executes agent-generated matplotlib code in an isolated subprocess.

    The Agg backend is forced so the code cannot open a display window.
    The output figure is always saved to ``assets_dir / filename``.
    """

    def __init__(self, assets_dir: Path = ASSETS_DIR) -> None:
        self._assets_dir = assets_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, code: str, filename: str = "graph.png") -> GraphResult:
        """Validate *code*, execute it in a subprocess, and return a GraphResult.

        Raises:
            GraphValidationError: code contains disallowed imports, calls, or patterns,
                                  or is missing required axis labels.
            GraphExecutionError: subprocess exits non-zero or times out.
            GraphOutputMissingError: subprocess succeeds but produces no output file.
        """
        self.validate(code)
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._assets_dir / filename

        start = time.monotonic()
        stdout, stderr = self._execute(code, output_path)
        duration = time.monotonic() - start

        if not output_path.exists():
            raise GraphOutputMissingError(
                f"Graph code ran without error but produced no file at {output_path}"
            )

        file_format = output_path.suffix.lstrip(".").lower()
        file_size = output_path.stat().st_size
        logger.info(
            "GraphRunner: figure saved to %s (%.1fs, %d bytes)",
            output_path, duration, file_size,
        )
        return GraphResult(
            success=True,
            output_path=output_path,
            file_format=file_format,
            file_size_bytes=file_size,
            duration_seconds=duration,
            stdout=stdout,
            stderr=stderr,
        )

    def validate(self, code: str) -> None:
        """Parse *code* with the AST; raise GraphValidationError on dangerous patterns."""
        # 1. Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise GraphValidationError(f"Syntax error in graph code: {exc}") from exc

        # 2. AST walk — disallowed imports and built-in calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    if top_level in _DISALLOWED_IMPORTS:
                        raise GraphValidationError(f"Disallowed import: '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                # `from sys import argv` — module name is in node.module, not alias.name
                if node.module:
                    top_level = node.module.split(".")[0]
                    if top_level in _DISALLOWED_IMPORTS:
                        raise GraphValidationError(f"Disallowed import: 'from {node.module}'")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _DISALLOWED_CALLS:
                    raise GraphValidationError(
                        f"Disallowed function call: '{node.func.id}'"
                    )

        # 3. String-pattern checks (plt.show, os.system, etc.)
        for pattern in _DISALLOWED_PATTERNS:
            if pattern in code:
                raise GraphValidationError(
                    f"Forbidden pattern '{pattern}' in generated code"
                )

        # 4. Require axis labels — catches both ax.set_xlabel() and plt.xlabel()
        if "xlabel(" not in code or "ylabel(" not in code:
            raise GraphValidationError(
                "Generated graph code must include xlabel() and ylabel() for both axes"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(self, code: str, output_path: Path) -> tuple[str, str]:
        """Write wrapped script to a temp file and run it in a subprocess.

        Returns:
            (stdout, stderr) strings from the completed subprocess.
        """
        script = self._build_script(code, output_path)
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(script)
                tmp_path = Path(f.name)

            result = subprocess.run(
                [sys.executable, str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=GRAPH_TIMEOUT_SECONDS,
            )
            if result.returncode != 0:
                raise GraphExecutionError(
                    f"Graph code failed (exit {result.returncode}):\n"
                    f"{result.stderr[:1000]}"
                )
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            raise GraphExecutionError(
                f"Graph code timed out after {GRAPH_TIMEOUT_SECONDS}s"
            ) from exc
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _build_script(code: str, output_path: Path) -> str:
        """Return the complete Python script: Agg preamble + *code* + savefig epilogue."""
        return (
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            f"{code}\n"
            "import matplotlib.pyplot as _plt\n"
            f"_plt.savefig(r'{output_path}', dpi=150, bbox_inches='tight')\n"
            "_plt.close('all')\n"
        )
