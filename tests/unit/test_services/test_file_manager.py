from __future__ import annotations

import json

import pytest

from article_generator.services.file_manager import FileManager

# ---------------------------------------------------------------------------
# save_markdown / read_markdown
# ---------------------------------------------------------------------------

def test_save_markdown_writes_content(tmp_path):
    FileManager(base_dir=tmp_path).save_markdown("# Hello", "article.md")
    assert (tmp_path / "article.md").read_text(encoding="utf-8") == "# Hello"


def test_save_markdown_returns_resolved_path(tmp_path):
    result = FileManager(base_dir=tmp_path).save_markdown("content", "article.md")
    assert result == tmp_path / "article.md"


def test_save_markdown_creates_parent_directories(tmp_path):
    FileManager(base_dir=tmp_path).save_markdown("data", "sub/nested/article.md")
    assert (tmp_path / "sub" / "nested" / "article.md").exists()


def test_read_markdown_returns_content(tmp_path):
    (tmp_path / "article.md").write_text("# Hello World", encoding="utf-8")
    assert FileManager(base_dir=tmp_path).read_markdown("article.md") == "# Hello World"


def test_read_markdown_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Markdown file not found"):
        FileManager(base_dir=tmp_path).read_markdown("missing.md")


# ---------------------------------------------------------------------------
# save_json / read_json
# ---------------------------------------------------------------------------

def test_save_json_writes_valid_json(tmp_path):
    FileManager(base_dir=tmp_path).save_json({"key": "value", "num": 42}, "report.json")
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert data == {"key": "value", "num": 42}


def test_save_json_returns_resolved_path(tmp_path):
    result = FileManager(base_dir=tmp_path).save_json({}, "out.json")
    assert result == tmp_path / "out.json"


def test_save_json_creates_parent_directories(tmp_path):
    FileManager(base_dir=tmp_path).save_json({"x": 1}, "reports/cost.json")
    assert (tmp_path / "reports" / "cost.json").exists()


def test_read_json_returns_dict(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert FileManager(base_dir=tmp_path).read_json("data.json") == {"a": 1}


def test_read_json_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        FileManager(base_dir=tmp_path).read_json("missing.json")


# ---------------------------------------------------------------------------
# ensure_dir
# ---------------------------------------------------------------------------

def test_ensure_dir_creates_directory(tmp_path):
    FileManager(base_dir=tmp_path).ensure_dir("figures")
    assert (tmp_path / "figures").is_dir()


def test_ensure_dir_returns_path(tmp_path):
    result = FileManager(base_dir=tmp_path).ensure_dir("figures")
    assert result == tmp_path / "figures"


def test_ensure_dir_is_idempotent(tmp_path):
    fm = FileManager(base_dir=tmp_path)
    fm.ensure_dir("figures")
    fm.ensure_dir("figures")  # second call must not raise
    assert (tmp_path / "figures").is_dir()


# ---------------------------------------------------------------------------
# _resolve
# ---------------------------------------------------------------------------

def test_resolve_relative_uses_base_dir(tmp_path):
    assert FileManager(base_dir=tmp_path)._resolve("article.md") == tmp_path / "article.md"


def test_resolve_absolute_path_bypasses_base_dir(tmp_path):
    abs_path = tmp_path / "other" / "file.md"
    assert FileManager(base_dir=tmp_path)._resolve(abs_path) == abs_path
