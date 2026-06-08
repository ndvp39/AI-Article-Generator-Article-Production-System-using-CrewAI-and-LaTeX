from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv

from article_generator.sdk.sdk import ArticleGeneratorSDK
from article_generator.shared.models import ArticleResult

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="article-generator",
        description="Generate an academic article using a 6-agent CrewAI pipeline.",
    )
    parser.add_argument("topic", help="Research topic for the article")
    parser.add_argument(
        "--config",
        default="config/setup.json",
        metavar="PATH",
        help="Path to setup.json (default: config/setup.json)",
    )
    return parser.parse_args(argv)


def _print_summary(result: ArticleResult) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print("ARTICLE GENERATION COMPLETE")
    print(sep)
    print(f"  Success : {result.success}")
    print(f"  LaTeX   : {result.tex_path}")
    print(f"  BibTeX  : {result.bib_path}")
    print(f"  PDF     : {result.pdf_path}")
    print(f"  Agents  : {len(result.agent_outputs)} task(s) completed")
    print(f"{sep}\n")


def main(argv: list[str] | None = None) -> int:
    """Entry point for both `uv run python src/main.py` and `article-generator` CLI."""
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = _parse_args(argv)

    try:
        sdk = ArticleGeneratorSDK(config_path=args.config)
        result = sdk.generate_article(topic=args.topic)
        _print_summary(result)
        return 0
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
