from pathlib import Path

# Project root (two levels up from this file: src/article_generator/constants.py)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Directory paths
CONFIG_DIR = PROJECT_ROOT / "config"
RESULTS_DIR = PROJECT_ROOT / "results"
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"

# Config file names
SETUP_CONFIG_FILE = "setup.json"
RATE_LIMITS_CONFIG_FILE = "rate_limits.json"
MODEL_PRICING_CONFIG_FILE = "model_pricing.json"

# Output file names
ARTICLE_MD_FILE = "article.md"
ARTICLE_TEX_FILE = "article.tex"
ARTICLE_PDF_FILE = "article.pdf"
REFERENCES_BIB_FILE = "references.bib"
COST_REPORT_FILE = "cost_report.json"
FIGURES_DIR = "figures"
GRAPH_FILE_PDF = "graph.pdf"
GRAPH_FILE_PNG = "graph.png"

# LaTeX compilation
LATEX_ENGINE = "lualatex"
LATEX_PASSES = 4
BIBER_EXECUTABLE = "biber"
LATEX_TIMEOUT_SECONDS = 120
BIBER_TIMEOUT_SECONDS = 120

# Graph generation
GRAPH_TIMEOUT_SECONDS = 30
GRAPH_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Bibliography
MIN_REFERENCES = 5
MIN_SEARCHES = 3

# Article quality
MIN_PAGES = 15
MIN_CAPTION_WORDS = 10

# API Gatekeeper
TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503})
PERMANENT_HTTP_CODES = frozenset({400, 401, 403, 404})

# Config schema versions
SETUP_CONFIG_VERSION = "1.00"
RATE_LIMITS_CONFIG_VERSION = "1.01"
MODEL_PRICING_CONFIG_VERSION = "1.00"

# Multi-process IPC
WATCHDOG_POLL_INTERVAL_SECONDS: float = 1.0
IPC_QUEUE_TIMEOUT_SECONDS: float = 5.0
# 2 h per agent: Gemini free tier (15 RPM) can force 60 s waits between calls;
# a complex agent making 30+ LLM calls needs ~30 min of pure backoff headroom.
DEFAULT_AGENT_TIMEOUT_SECONDS: int = 7200

# Per-agent timeouts (seconds) — 2 h each accommodates heavy Gemini free-tier
# rate-limit backoff while still catching true deadlocks via Watchdog.
AGENT_TIMEOUT_SECONDS: dict[str, int] = {
    "researcher": 7200,
    "writer": 7200,
    "editor": 7200,
    "graph_generator": 7200,
    "latex_formatter": 7200,
    "bidi_specialist": 7200,
}

# LLM providers
LLM_PROVIDER_CLAUDE = "claude"
LLM_PROVIDER_GEMINI = "gemini"
LLM_PROVIDERS_SUPPORTED = frozenset({LLM_PROVIDER_CLAUDE, LLM_PROVIDER_GEMINI})
DEFAULT_CLAUDE_MODEL = "anthropic/claude-sonnet-4-6"
DEFAULT_GEMINI_MODEL = "gemini/gemini-2.0-flash"

# LLM tiers
LLM_TIER_FREE = "free"
LLM_TIER_PRO = "pro"
DEFAULT_LLM_TIER = LLM_TIER_FREE
