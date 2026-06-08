from __future__ import annotations

import json
import logging
from pathlib import Path

from article_generator.constants import RESULTS_DIR

logger = logging.getLogger(__name__)


class FileManager:
    """Handles all file I/O for the article generation pipeline."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir is not None else RESULTS_DIR

    def _resolve(self, path: Path | str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self._base / p

    def save_markdown(self, content: str, path: Path | str) -> Path:
        """Write markdown content to disk. Creates parent directories as needed."""
        dest = self._resolve(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        logger.info("Saved markdown: %s", dest)
        return dest

    def read_markdown(self, path: Path | str) -> str:
        """Read markdown from disk. Raises FileNotFoundError if the file is missing."""
        src = self._resolve(path)
        if not src.exists():
            raise FileNotFoundError(f"Markdown file not found: {src}")
        return src.read_text(encoding="utf-8")

    def save_json(self, data: dict, path: Path | str) -> Path:
        """Serialize dict as indented JSON. Creates parent directories as needed."""
        dest = self._resolve(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Saved JSON: %s", dest)
        return dest

    def read_json(self, path: Path | str) -> dict:
        """Parse JSON from disk. Raises FileNotFoundError if the file is missing."""
        src = self._resolve(path)
        if not src.exists():
            raise FileNotFoundError(f"JSON file not found: {src}")
        return json.loads(src.read_text(encoding="utf-8"))

    def ensure_dir(self, path: Path | str) -> Path:
        """Create directory (and parents) if it does not exist. Returns the path."""
        d = self._resolve(path)
        d.mkdir(parents=True, exist_ok=True)
        return d
