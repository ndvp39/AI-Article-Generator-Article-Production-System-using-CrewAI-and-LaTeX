from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from article_generator.__main__ import _parse_args, _print_summary, main

# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_captures_topic():
    args = _parse_args(["Deep Learning"])
    assert args.topic == "Deep Learning"


def test_parse_args_default_config():
    args = _parse_args(["topic"])
    assert args.config == "config/setup.json"


def test_parse_args_custom_config():
    args = _parse_args(["topic", "--config", "my/config.json"])
    assert args.config == "my/config.json"


def test_parse_args_no_topic_exits():
    with pytest.raises(SystemExit):
        _parse_args([])


def test_parse_args_multi_word_topic():
    args = _parse_args(["Graph Neural Networks in Healthcare"])
    assert "Graph" in args.topic


# ---------------------------------------------------------------------------
# _print_summary
# ---------------------------------------------------------------------------


def test_print_summary_shows_success_flag(capsys):
    result = MagicMock(
        success=True, tex_path="a.tex", bib_path="a.bib",
        pdf_path="a.pdf", agent_outputs=[1, 2],
    )
    _print_summary(result)
    assert "True" in capsys.readouterr().out


def test_print_summary_shows_tex_path(capsys):
    result = MagicMock(
        success=True, tex_path="results/article.tex", bib_path="r.bib",
        pdf_path="r.pdf", agent_outputs=[],
    )
    _print_summary(result)
    assert "results/article.tex" in capsys.readouterr().out


def test_print_summary_shows_agent_count(capsys):
    result = MagicMock(
        success=True, tex_path="", bib_path="", pdf_path="",
        agent_outputs=["a", "b", "c"],
    )
    _print_summary(result)
    assert "3" in capsys.readouterr().out


def test_print_summary_shows_separator(capsys):
    result = MagicMock(
        success=False, tex_path="", bib_path="", pdf_path="", agent_outputs=[],
    )
    _print_summary(result)
    assert "=" * 10 in capsys.readouterr().out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


@patch("article_generator.__main__.load_dotenv")
@patch("article_generator.__main__.ArticleGeneratorSDK")
def test_main_returns_0_on_success(mock_sdk, _mock_dotenv):
    mock_result = MagicMock(
        success=True, tex_path="", bib_path="", pdf_path="", agent_outputs=[],
    )
    mock_sdk.return_value.generate_article.return_value = mock_result
    with patch("article_generator.__main__._print_summary"):
        assert main(["Test Topic"]) == 0


@patch("article_generator.__main__.load_dotenv")
@patch("article_generator.__main__.ArticleGeneratorSDK")
def test_main_returns_1_on_exception(mock_sdk, _mock_dotenv):
    mock_sdk.return_value.generate_article.side_effect = RuntimeError("boom")
    assert main(["Test Topic"]) == 1


@patch("article_generator.__main__.load_dotenv")
@patch("article_generator.__main__.ArticleGeneratorSDK")
def test_main_returns_130_on_keyboard_interrupt(mock_sdk, _mock_dotenv):
    mock_sdk.return_value.generate_article.side_effect = KeyboardInterrupt
    assert main(["Test Topic"]) == 130


@patch("article_generator.__main__.load_dotenv")
@patch("article_generator.__main__.ArticleGeneratorSDK")
def test_main_passes_config_path_to_sdk(mock_sdk, _mock_dotenv):
    mock_result = MagicMock(
        success=True, tex_path="", bib_path="", pdf_path="", agent_outputs=[],
    )
    mock_sdk.return_value.generate_article.return_value = mock_result
    with patch("article_generator.__main__._print_summary"):
        main(["Topic", "--config", "custom/setup.json"])
    mock_sdk.assert_called_once_with(config_path="custom/setup.json")


@patch("article_generator.__main__.load_dotenv")
@patch("article_generator.__main__.ArticleGeneratorSDK")
def test_main_passes_topic_to_generate_article(mock_sdk, _mock_dotenv):
    mock_result = MagicMock(
        success=True, tex_path="", bib_path="", pdf_path="", agent_outputs=[],
    )
    mock_sdk.return_value.generate_article.return_value = mock_result
    with patch("article_generator.__main__._print_summary"):
        main(["Quantum Computing"])
    mock_sdk.return_value.generate_article.assert_called_once_with(topic="Quantum Computing")


@patch("article_generator.__main__.load_dotenv")
@patch("article_generator.__main__.ArticleGeneratorSDK")
def test_main_calls_load_dotenv(mock_sdk, mock_dotenv):
    mock_result = MagicMock(
        success=True, tex_path="", bib_path="", pdf_path="", agent_outputs=[],
    )
    mock_sdk.return_value.generate_article.return_value = mock_result
    with patch("article_generator.__main__._print_summary"):
        main(["Topic"])
    mock_dotenv.assert_called_once()
