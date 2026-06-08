# AI Article Generator
### MSC Course — AI Agents — HW3

**Course:** AI Agents — MSC Course  
**Lecturer:** Dr. Yoram Segal  
**Version:** 1.00  

---

## Overview

**AI Article Generator** is a CrewAI multi-agent pipeline that autonomously researches a topic, writes a professional academic article (~15 pages), and compiles it into a polished LaTeX PDF — complete with cover sheet, table of contents, bibliography, figures, formulas, and Hebrew-English bidirectional text.

The pipeline uses **6 specialized AI agents** working in sequence:

| Agent | Role | Tools |
|-------|------|-------|
| ResearcherAgent | Live internet research via Google Search | SerperDevTool |
| WriterAgent | Writes the full article in structured Markdown | None |
| EditorAgent | Reviews and improves accuracy and clarity | None |
| GraphGeneratorAgent | Generates topic-relevant matplotlib graph code | None |
| LaTeXFormatterAgent | Converts Markdown to complete `.tex` document | None |
| BiDiSpecialistAgent | Validates and fixes Hebrew–English BiDi | None |

**Output:** `results/article.pdf` — a fully compiled academic PDF.

---

## Requirements

### System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | ≥ 3.10 | Required for `match` statements and modern type hints |
| uv | ≥ 0.4 | Package manager — `pip` is NOT used |
| MiKTeX | ≥ 24.x | LaTeX distribution for Windows |
| LuaLaTeX | included with MiKTeX | Required for BiDi + Unicode support |
| biber | included with MiKTeX | Bibliography processor |
| FrankRuhlCLM font | MiKTeX Package Manager | Hebrew font for BiDi support |

### API Keys Required

| Key | Where to Get | When Required |
|-----|-------------|---------------|
| `ACTIVE_LLM` | — (set to `claude` or `gemini`) | Always — controls LLM provider |
| `LLM_API_KEY` | [Anthropic Console](https://console.anthropic.com) | When `ACTIVE_LLM=claude` |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | When `ACTIVE_LLM=gemini` |
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) | Always — Google Search for Researcher agent |

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd HW3
```

### 2. Install uv

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify:
```powershell
uv --version
```

### 3. Install Python Dependencies

```powershell
uv sync
```

This reads `pyproject.toml` and installs all dependencies into a managed virtual environment. No `pip install` is needed or permitted.

### 4. Install MiKTeX

1. Download MiKTeX from [miktex.org/download](https://miktex.org/download)
2. Run the installer; choose "Install for all users" for system-wide access
3. After install, open **MiKTeX Console** and run **"Check for updates"**
4. Install the Hebrew font: open MiKTeX Console → Packages → search `frankruhlclm` → Install

Verify LuaLaTeX and biber are available:
```powershell
lualatex --version
biber --version
```

### 5. Configure API Keys

Copy the example environment file:
```powershell
Copy-Item .env-example .env
```

Edit `.env` and fill in your keys:
```
# Choose your LLM provider: "claude" or "gemini"
ACTIVE_LLM=claude

# Anthropic Claude (required when ACTIVE_LLM=claude)
LLM_API_KEY=your_anthropic_api_key_here

# Google Gemini (required when ACTIVE_LLM=gemini)
GEMINI_API_KEY=your_gemini_api_key_here

# Serper — always required
SERPER_API_KEY=your_serper_api_key_here
```

> **Security:** Never commit `.env` to version control. It is listed in `.gitignore`.

---

## Configuration

All runtime configuration lives in the `config/` directory. Edit these files to customize the pipeline behavior without touching source code.

### `config/setup.json` — Main Application Config

```json
{
  "setup": {
    "version": "1.00",
    "article": {
      "target_pages": 15,
      "language": "english",
      "bidi_language": "hebrew",
      "citation_style": "numeric"
    },
    "agents": {
      "model": "claude-sonnet-3-7",
      "temperature": 0.7,
      "max_tokens": 8192
    },
    "latex": {
      "engine": "lualatex",
      "passes": 4,
      "output_dir": "results"
    }
  }
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `article.target_pages` | Target article length in pages | `15` |
| `article.language` | Primary article language | `"english"` |
| `agents.model` | LLM model for all agents | `"claude-sonnet-3-7"` |
| `agents.temperature` | LLM sampling temperature | `0.7` |
| `latex.engine` | LaTeX engine (`lualatex` or `xelatex`) | `"lualatex"` |

### `config/rate_limits.json` — API Rate Limits

Controls the API Gatekeeper's rate limiting, queue depth, and retry behavior. Separate profiles for the LLM API and the Serper search API.

Key settings:
```json
{
  "rate_limits": {
    "services": {
      "default": { "requests_per_minute": 30, "max_retries": 3 },
      "serper":  { "requests_per_minute": 10, "max_retries": 2 }
    }
  }
}
```

### `config/model_pricing.json` — LLM Cost Pricing

Used by the `CostTracker` to calculate USD costs and produce cross-model comparisons. Update when providers change their pricing.

```json
{
  "model_pricing": {
    "models": {
      "claude-sonnet-3-7": { "input_price_per_mtok": 3.00, "output_price_per_mtok": 15.00 },
      "gpt-4o-mini":       { "input_price_per_mtok": 0.15, "output_price_per_mtok": 0.60  }
    }
  }
}
```

---

## Usage

### Basic Usage

Generate an article on any topic:

```powershell
uv run python src/main.py --topic "Deep Learning in Medical Image Analysis"
```

The pipeline runs all 6 agents sequentially, compiles the LaTeX PDF, and prints a summary on completion.

### Command-Line Options

```
usage: main.py [-h] --topic TOPIC [--output-dir OUTPUT_DIR] [--model MODEL]
               [--budget BUDGET] [--no-bidi] [--verbose]

options:
  --topic TOPIC           Article topic (required)
  --output-dir DIR        Output directory (default: results/)
  --model MODEL           Override LLM model from config
  --budget BUDGET         Cost budget alert threshold in USD (e.g. 0.50)
  --no-bidi               Skip BiDi Hebrew chapter (for testing)
  --verbose               Enable verbose logging
```

### Examples

```powershell
# Standard run
uv run python src/main.py --topic "Transformer Architecture in NLP"

# With budget alert at $0.50
uv run python src/main.py --topic "Reinforcement Learning" --budget 0.50

# Verbose output for debugging
uv run python src/main.py --topic "Graph Neural Networks" --verbose

# Override model
uv run python src/main.py --topic "Computer Vision" --model claude-haiku-3-5
```

### Using the SDK Directly

```python
from article_generator.sdk.sdk import ArticleGeneratorSDK
from article_generator.shared.config import ConfigManager

config_manager = ConfigManager("config/")
sdk = ArticleGeneratorSDK(config_manager)

result = sdk.generate("Federated Learning: Privacy-Preserving Machine Learning")

print(f"PDF saved to: {result.pdf_path}")
print(f"Total cost:   ${result.cost_report.run_summary.total_cost_usd:.4f}")
print(f"Pages:        {result.page_count}")

# Cross-model cost comparison
comparison = sdk.compare_model_costs()
for entry in comparison.alternatives:
    marker = " ← actual" if entry.is_actual else ""
    print(f"  {entry.model:30s}  ${entry.cost_usd:.4f}{marker}")
```

---

## Output Files

After a successful run, the following files are written to `results/`:

```
results/
├── article.pdf              ← final compiled PDF (primary output)
├── article.tex              ← generated LaTeX source
├── references.bib           ← generated bibliography file
├── article.aux              ← LaTeX auxiliary (auto-generated)
├── article.bbl              ← bibliography output (auto-generated)
├── article.log              ← full LuaLaTeX compilation log
├── cost_report.json         ← token usage and USD cost breakdown
└── figures/
    └── graph.pdf            ← programmatically generated graph
```

### `cost_report.json` Structure

```json
{
  "run_summary": {
    "total_calls": 24,
    "total_input_tokens": 48200,
    "total_output_tokens": 12300,
    "total_cost_usd": 0.329100,
    "most_expensive_agent": "WriterAgent"
  },
  "per_agent": { ... },
  "model_comparison": {
    "cheapest_model": "gpt-4o-mini",
    "alternatives": [ ... ]
  }
}
```

---

## Project Structure

```
HW3/
├── src/
│   └── article_generator/
│       ├── sdk/
│       │   └── sdk.py                    ← ArticleGeneratorSDK (entry point)
│       ├── services/
│       │   ├── agents/                   ← 6 CrewAI agent definitions
│       │   ├── tasks/                    ← CrewAI task definitions
│       │   ├── tools/
│       │   │   └── search_tools.py       ← SerperDevTool factory
│       │   ├── crew_service.py           ← CrewAI crew assembly
│       │   ├── latex_compiler.py         ← LaTeX generation + 4-pass compile
│       │   ├── graph_runner.py           ← Subprocess graph execution
│       │   ├── cost_tracker.py           ← Token & cost analysis
│       │   └── file_manager.py           ← File I/O
│       ├── shared/
│       │   ├── config.py                 ← ConfigManager
│       │   ├── gatekeeper.py             ← ApiGatekeeper (rate limit + queue)
│       │   ├── bidi_helpers.py           ← BiDi LaTeX utilities
│       │   └── version.py
│       ├── constants.py
│       └── __init__.py
├── tests/
│   ├── unit/                             ← Unit tests (mocked APIs)
│   └── integration/                      ← Integration tests (real compilation)
├── config/
│   ├── setup.json
│   ├── rate_limits.json
│   └── model_pricing.json
├── docs/
│   ├── PRD.md
│   ├── PLAN.md
│   ├── TODO.md
│   ├── PRD_crewai_agents.md
│   ├── PRD_latex_pipeline.md
│   ├── PRD_api_gatekeeper.md
│   ├── PRD_bibliography.md
│   ├── PRD_bidi.md
│   ├── PRD_graph_generation.md
│   ├── PRD_cost_tracker.md
│   ├── PRD_research_tools.md
│   └── prompts_book.md
├── data/                                 ← Static assets (cover image, etc.)
├── results/                              ← Generated output (gitignored)
├── assets/                               ← Article figures
├── .env-example                          ← API key template (commit this)
├── .env                                  ← Real API keys (DO NOT commit)
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Running Tests

### Unit Tests

Unit tests use mocked API calls — no real API keys required:

```powershell
uv run pytest tests/unit/ -v
```

### Integration Tests

Integration tests require MiKTeX and compile real LaTeX:

```powershell
uv run pytest tests/integration/ -v
```

### Full Test Suite with Coverage

```powershell
uv run pytest tests/ --cov=src --cov-report=term-missing
```

Target: **≥ 85% coverage** across all source modules.

### Linting

```powershell
uv run ruff check src/ tests/
```

Target: **zero violations**.

---

## Evaluation Criteria Checklist

Per Project.md §5, the following criteria are verified before submission:

| Criterion | How to Verify |
|-----------|--------------|
| All links and citations clickable in PDF | Open `results/article.pdf`; click each `[N]` citation and TOC entry |
| BiDi text direction correct throughout | Open PDF; Hebrew chapter text reads right-to-left without corruption |
| No table overflows page margins | Inspect all tables in PDF; no content cut at page edge |
| All formulas compiled as LaTeX math | Inspect PDF; no formula appears as plain text (`sigma`, `integral`, etc.) |

---

## Architecture Overview

The system follows a **layered SDK architecture**:

```
CLI (main.py)
    └── ArticleGeneratorSDK
            ├── CrewService          ← orchestrates 6 agents via CrewAI
            │     ├── ResearcherAgent  [SerperDevTool]
            │     ├── WriterAgent      []
            │     ├── EditorAgent      []
            │     ├── GraphGeneratorAgent []
            │     ├── LaTeXFormatterAgent []
            │     └── BiDiSpecialistAgent []
            ├── LaTeXCompiler        ← 4-pass lualatex + biber
            ├── GraphRunner          ← subprocess graph execution
            ├── CostTracker          ← token & USD cost analysis
            └── ApiGatekeeper        ← rate limiting, queue, retry, logging
                    └── [all external API calls pass through here]
```

All external API calls (LLM + Serper) are routed through `ApiGatekeeper`, which enforces rate limits, queues on overflow, retries on transient failures, and logs every call as a `CallRecord` for cost analysis.

For full architecture details, see `docs/PLAN.md`.

---

## Configuration Guide

### Switching LLM Provider

The system supports **Claude** (Anthropic) and **Gemini** (Google) via a single `.env` toggle:

```
# Use Claude (default)
ACTIVE_LLM=claude
LLM_API_KEY=your_anthropic_key

# Use Gemini
ACTIVE_LLM=gemini
GEMINI_API_KEY=your_gemini_key
```

Default models are defined in `src/article_generator/constants.py`:
- Claude: `claude-sonnet-4-6`
- Gemini: `gemini/gemini-2.0-flash`

The active models can also be adjusted in `config/setup.json` under `agents.claude_model` and `agents.gemini_model`.

### Adjusting Rate Limits

If you hit API rate limit errors, lower the limits in `config/rate_limits.json`:
```json
"default": { "requests_per_minute": 10 }
```

### Setting a Cost Budget Alert

In `config/setup.json`:
```json
"cost": { "budget_alert_usd": 0.25 }
```

Or at runtime:
```powershell
uv run python src/main.py --topic "..." --budget 0.25
```

A warning is printed if the run exceeds the budget. The run is not stopped — the alert is informational.

### Selecting LaTeX Engine

Both LuaLaTeX and XeLaTeX are supported. LuaLaTeX is the default:
```json
"latex": { "engine": "lualatex" }
```

To use XeLaTeX:
```json
"latex": { "engine": "xelatex" }
```

> `pdflatex` is NOT supported — it cannot handle Hebrew BiDi text.

---

## Troubleshooting

### `SERPER_API_KEY environment variable not set`
Ensure `.env` exists and contains `SERPER_API_KEY=your_key`. Run `uv run python src/main.py` from the project root so `.env` is loaded.

### `lualatex: command not found`
MiKTeX is not in your PATH. Open a new PowerShell window after MiKTeX installation, or add MiKTeX's `bin` directory to your PATH manually.

### `FontNotFoundError: Hebrew font 'FrankRuhlCLM' not found`
Open MiKTeX Console → Packages → search `frankruhlclm` → Install. Then retry.

### `biber: command not found`
In MiKTeX Console, check that biber is installed: Packages → search `biber` → Install.

### Compilation fails at Pass 2 (biber)
Check `results/article.log` for citation key errors. Common causes:
- A `\cite{key}` in `.tex` with no matching entry in `references.bib`
- Duplicate citation keys in `references.bib`

### PDF is fewer than 15 pages
The LLM may have generated a shorter article. Increase `article.target_pages` in `config/setup.json` and re-run, or adjust agent prompts in `src/article_generator/services/tasks/task_definitions.py`.

### High API cost
Switch to a cheaper model: `--model claude-haiku-3-5`. The `cost_report.json` shows the cross-model comparison so you can see how much you would save.

---

## Dependencies

Core dependencies (managed by `uv` via `pyproject.toml`):

| Package | Purpose |
|---------|---------|
| `crewai` | Multi-agent orchestration framework |
| `crewai-tools` | SerperDevTool and other built-in tools |
| `anthropic` | Anthropic LLM API client |
| `matplotlib` | Programmatic graph generation |
| `python-dotenv` | Load `.env` file into environment |

Development dependencies:

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |
| `ruff` | Linting and formatting |

---

## License

This project is submitted as academic coursework for the MSC AI Agents course. Not licensed for commercial use.

---

## Author

Student — MSC AI Agents Course, HW3  
Lecturer: Dr. Yoram Segal
