from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from article_generator.constants import GRAPH_TIMEOUT_SECONDS


class _CodeInput(BaseModel):
    code: str = Field(description="Self-contained Python code to execute and verify")


class LocalCodeInterpreterTool(BaseTool):
    """Execute Python code locally via subprocess for agent self-verification.

    Runs code in a temporary directory with a pre-created figures/ subfolder
    so matplotlib savefig calls succeed. Returns stdout, stderr, exit code,
    and any files written under figures/.
    """

    name: str = "Local Python Code Interpreter"
    description: str = (
        "Execute Python code in a sandboxed temporary directory. "
        "A figures/ subdirectory is pre-created so plt.savefig() calls work. "
        "Returns stdout, stderr, exit code, and files produced. "
        "Use this to verify graph code before finalising it."
    )
    args_schema: type[BaseModel] = _CodeInput
    timeout: int = GRAPH_TIMEOUT_SECONDS

    def _run(self, code: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            (work / "figures").mkdir()
            script = work / "script.py"
            script.write_text(code, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [sys.executable, str(script)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=str(work),
                )
            except subprocess.TimeoutExpired:
                return f"TIMEOUT: execution exceeded {self.timeout}s limit"

            parts: list[str] = []
            if proc.stdout.strip():
                parts.append(f"STDOUT:\n{proc.stdout.strip()}")
            if proc.stderr.strip():
                parts.append(f"STDERR:\n{proc.stderr.strip()}")

            parts.append(f"EXIT CODE: {proc.returncode}")

            produced = list((work / "figures").iterdir())
            if produced:
                names = ", ".join(f.name for f in produced)
                parts.append(f"FILES PRODUCED: figures/{names}")
            else:
                parts.append("FILES PRODUCED: none")

            return "\n".join(parts)
