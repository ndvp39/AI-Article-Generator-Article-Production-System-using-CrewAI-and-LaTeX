# AI Article Generator
### MSC Course — AI Agents — HW3

**Course:** AI Agents — MSC Course  
**Lecturer:** Dr. Yoram Segal  
**Version:** 1.13 — Hebrew Content Mandate + Graph Copy Fix + Graph in PDF  

---

## Overview

**AI Article Generator** is a multi-agent pipeline that autonomously researches a topic, writes a professional academic article (~15 pages), and compiles it into a polished LaTeX PDF — complete with cover sheet, table of contents, bibliography, figures, formulas, and Hebrew-English bidirectional text.

The pipeline uses **6 specialized AI agents**, each running as an **isolated OS process**, communicating exclusively through typed IPC message queues. A **GatekeeperRouter** validates and routes every inter-agent message. A **Watchdog** monitors process health and enforces per-agent timeouts.

| Agent | Role | Tools | Process |
|-------|------|-------|---------|
| ResearcherAgent | Live internet research | SerperDevTool | `multiprocessing.Process` |
| WriterAgent | Full article in structured Markdown | — | `multiprocessing.Process` |
| EditorAgent | Accuracy and clarity review | — | `multiprocessing.Process` |
| GraphGeneratorAgent | Generates matplotlib graph code | LocalCodeInterpreterTool | `multiprocessing.Process` |
| LaTeXFormatterAgent | Converts Markdown to `.tex` | FileWriterTool | `multiprocessing.Process` |
| BiDiSpecialistAgent | Hebrew–English BiDi validation | FileReadTool, FileWriterTool | `multiprocessing.Process` |

**Output:** `results/article.pdf` — a fully compiled academic PDF.

## Sample Output

📄 **[Download the generated article PDF](results/article.pdf)** — Multi-Agent Systems and Autonomous AI, compiled by the 6-agent pipeline (15 pages, XeLaTeX, Hebrew main language).

---

## Architecture

```
CLI (src/main.py)
    └── ArticleGeneratorSDK
            └── CrewService
                    └── ProcessOrchestrator
                            │
                            ├── [in_q_0] ──► AgentProcess: Researcher  ──► [out_q_0]
                            │                                                    │
                            │              GatekeeperRouter (validates + routes) │
                            │                                                    ▼
                            ├── [in_q_1] ──► AgentProcess: Writer      ──► [out_q_1]
                            │                                                    │
                            │              GatekeeperRouter                     ▼
                            │                                                    │
                            ├── [in_q_2] ──► AgentProcess: Editor      ──► [out_q_2]
                            │                     ...
                            ├── [in_q_3] ──► AgentProcess: GraphGen    ──► [out_q_3]
                            ├── [in_q_4] ──► AgentProcess: LaTeX       ──► [out_q_4]
                            └── [in_q_5] ──► AgentProcess: BiDi        ──► [out_q_5]
                                                                              │
                                                                         ArticleResult
                            ┌─────────────────────────────────────────────────┘
                            Watchdog (daemon thread — monitors all 6 PIDs, enforces timeouts)
```

### Key Components

| Component | Location | Responsibility |
|-----------|----------|---------------|
| `ProcessOrchestrator` | `services/process_orchestrator.py` | Spawns all agent processes, owns all queues, drives pipeline start/finish |
| `AgentProcessRunner` | `shared/process_runner.py` | Wraps one CrewAI agent in a `multiprocessing.Process`; agent initialised *inside* the subprocess |
| `GatekeeperRouter` | `services/gatekeeper_router.py` | Daemon thread; validates `AgentMessage` schema; routes output → next input queue |
| `Watchdog` | `services/watchdog.py` | Daemon thread; polls `is_alive()`; terminates timed-out processes; raises `AgentTimeoutError` |
| `build_llm` / `_inject_retry` | `shared/llm_factory.py` | Returns a provider-specific LLM; injects exponential-backoff retry wrapper and trailing-assistant-message guard directly onto `llm.call` |
| `AgentMessage` / `AgentStatus` | `shared/ipc_models.py` | Typed dataclasses for all IPC communication |
| `CrewService` | `services/crew_service.py` | Thin wrapper — delegates to `ProcessOrchestrator` |
| `ArticleGeneratorSDK` | `sdk/sdk.py` | Single public entry point; delegates everything to services |

### IPC Message Flow

Every message between agents is an `AgentMessage` instance placed on a `multiprocessing.Queue`:

```python
@dataclass
class AgentMessage:
    sender: str        # e.g. "Senior Academic Researcher"
    recipient: str     # e.g. "Academic Article Writer"
    content: str       # agent output text
    topic: str         # original article topic
    message_id: str    # UUID — unique per message
    timestamp: float   # time.time()
    message_type: str  # "input" | "output" | "error"
```

The `GatekeeperRouter` intercepts every message, validates the schema, and raises `GatekeeperValidationError` if:
- `content` is empty
- `sender`/`recipient` pair is not a valid adjacent pipeline step
- `message_type` is not a recognised value

### Watchdog Behaviour

The `Watchdog` polls every `WATCHDOG_POLL_INTERVAL_SECONDS` (default: 1 s):

- **Unexpected crash** — `process.is_alive()` returns `False` before the agent finishes: records `AgentStatus(status="error")`, pipeline fails fast.
- **Timeout exceeded** — agent runs longer than `AGENT_TIMEOUT_SECONDS[role]` (default **7200 s / 2 h**): calls `process.terminate()`, records `AgentStatus(status="timeout")`, raises `AgentTimeoutError`.
- **Healthy** — all processes alive and within timeout: `Watchdog.all_healthy()` returns `True`.

The 2-hour limit accommodates Gemini free-tier rate limiting: at 15 RPM, an agent making 30+ LLM calls may wait ~30 minutes in backoff sleep alone.

### Retry Architecture

`build_llm()` injects a retry wrapper directly onto `llm.call` inside each agent subprocess:

- **Backoff:** 60 s → 120 s → 240 s → 300 s (cap) on every `429 RESOURCE_EXHAUSTED`.
- **Max retries:** 20 per individual LLM call — prevents infinite loops when the daily quota is genuinely exhausted.
- **Trailing-message guard:** if the messages list ends with `role=assistant` (a crewai internal mechanism that some providers reject), it is silently converted to `role=user` before the API call.

---

## Requirements

### System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | ≥ 3.10 | Required for modern type hints and `match` statements |
| uv | ≥ 0.4 | Package manager — `pip` is NOT used |
| MiKTeX | ≥ 24.x | LaTeX distribution (Windows) |
| XeLaTeX | included with MiKTeX | Required for `bidi` + Hebrew + Unicode support |
| biber | included with MiKTeX | Bibliography processor |
| Arial font | system font (Windows) | Hebrew font via `fontspec` |

> `multiprocessing` is part of the Python standard library — no extra installation needed.

### API Keys Required

| Variable | Where to Get | When Required |
|----------|-------------|---------------|
| `ACTIVE_LLM` | — set to `claude` or `gemini` | Always |
| `LLM_API_KEY` | [Anthropic Console](https://console.anthropic.com) | When `ACTIVE_LLM=claude` |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | When `ACTIVE_LLM=gemini` |
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) | Always — used by ResearcherAgent |

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
uv --version
```

### 3. Install Python Dependencies

```powershell
uv sync
```

### 4. Install MiKTeX

1. Download from [miktex.org/download](https://miktex.org/download)
2. Run installer — choose "Install for all users"
3. Open **MiKTeX Console** → Check for updates
4. Install Hebrew font: MiKTeX Console → Packages → search `frankruhlclm` → Install

Verify:
```powershell
xelatex --version
biber --version
```

### 5. Configure API Keys

```powershell
Copy-Item .env-example .env
```

Edit `.env`:
```
# LLM provider: "gemini" (default, free) or "claude" (requires paid credits)
ACTIVE_LLM=gemini

# Google Gemini — free tier: 15 RPM, 1 500 RPD
# Get key at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Anthropic Claude (only needed when ACTIVE_LLM=claude)
LLM_API_KEY=your_anthropic_api_key_here

# Serper — always required
SERPER_API_KEY=your_serper_api_key_here
```

> **Gemini free tier:** The pipeline uses 15-RPM-aware exponential backoff (60 s → 300 s cap, max 20 retries). Expect a full pipeline run to take **15–45 minutes** depending on rate limiting.

> **Security:** `.env` is listed in `.gitignore`. Never commit it.

---

## Configuration

### `config/setup.json` — Main Application Config

```json
{
  "setup": {
    "version": "1.00",
    "article": {
      "target_pages": 15,
      "language": "hebrew",
      "bidi_language": "english",
      "citation_style": "numeric"
    },
    "agents": {
      "claude_model": "anthropic/claude-sonnet-4-6",
      "gemini_model": "gemini/gemini-2.5-flash",
      "temperature": 0.7,
      "max_tokens": 32000
    },
    "latex": {
      "engine": "xelatex",
      "passes": 4,
      "output_dir": "results"
    },
    "cost": {
      "budget_alert_usd": 1.00
    }
  }
}
```

### `config/rate_limits.json` — API Rate Limits

Controls per-service rate limits, retry policy, and queue depth for the `ApiGatekeeper`.

### `config/model_pricing.json` — LLM Cost Pricing

Used by `CostTracker` to compute USD costs and cross-model comparisons.

### Switching LLM Provider

```
# Gemini (default — free tier available)
ACTIVE_LLM=gemini
GEMINI_API_KEY=your_gemini_key

# Claude (requires paid credits)
ACTIVE_LLM=claude
LLM_API_KEY=your_anthropic_key
```

Default models: `gemini/gemini-2.5-flash` / `anthropic/claude-sonnet-4-6` (set in `constants.py`, overridable in `setup.json`).

> **Note:** The `anthropic/` prefix in the Claude model ID is required — without it, the CrewAI LLM factory misidentifies the provider as OpenAI.

---

## Usage

### Basic Usage

```powershell
uv run python src/main.py "Deep Learning in Medical Image Analysis"
```

### Command-Line Options

```
usage: article-generator [-h] [--config PATH] topic

positional arguments:
  topic          Research topic for the article

options:
  -h, --help     show this help message and exit
  --config PATH  Path to setup.json (default: config/setup.json)
```

### Examples

```powershell
# Standard run
uv run python src/main.py "Transformer Architecture in NLP"

# Custom config file
uv run python src/main.py "Graph Neural Networks" --config my_config/setup.json

# Using the installed entry point
uv run article-generator "Reinforcement Learning in Robotics"
```

### Using the SDK Directly

```python
from article_generator.sdk.sdk import ArticleGeneratorSDK

sdk = ArticleGeneratorSDK(config_path="config/setup.json")
result = sdk.generate_article(topic="Federated Learning in Healthcare")

print(f"Success:  {result.success}")
print(f"LaTeX:    {result.tex_path}")
print(f"PDF:      {result.pdf_path}")
print(f"Agents:   {len(result.agent_outputs)} tasks completed")
```

---

## Output Files

```
results/
├── article.md               ← Markdown output from agent pipeline
├── article.tex              ← Generated LaTeX source
├── references.bib           ← Generated bibliography
├── article.pdf              ← Final compiled PDF (primary output)
├── article.log              ← XeLaTeX compilation log
├── cost_report_<timestamp>.json  ← Token usage and USD cost breakdown (one per run)
└── figures/
    ├── diagram.pdf          ← Architecture diagram (image artifact)
    └── graph.pdf            ← Programmatically generated matplotlib graph
```

> The compiled `results/` outputs (PDF, `.tex`, figures, cost report) are committed to the repo as a reference sample of a full pipeline run.

---

## Project Structure

```
HW3/
├── src/
│   ├── main.py                              ← CLI entry point wrapper
│   └── article_generator/
│       ├── __main__.py                      ← CLI logic (argparse, dotenv, summary)
│       ├── constants.py                     ← Immutable project constants
│       ├── sdk/
│       │   └── sdk.py                       ← ArticleGeneratorSDK (public entry point)
│       ├── services/
│       │   ├── agents/                      ← 6 CrewAI agent definitions
│       │   │   ├── researcher.py
│       │   │   ├── writer.py
│       │   │   ├── editor.py
│       │   │   ├── graph_generator.py
│       │   │   ├── latex_formatter.py
│       │   │   └── bidi_specialist.py
│       │   ├── tasks/
│       │   │   └── task_definitions.py      ← CrewAI Task objects + context chain
│       │   ├── tools/
│       │   │   ├── search_tools.py          ← SerperDevTool factory + isolation check
│       │   │   └── code_interpreter_tool.py ← LocalCodeInterpreterTool (subprocess)
│       │   ├── crew_service.py              ← Delegates to ProcessOrchestrator
│       │   ├── process_orchestrator.py      ← Spawns agents, owns queues, drives pipeline
│       │   ├── gatekeeper_router.py         ← IPC message validation + routing (thread)
│       │   ├── watchdog.py                  ← Process health monitor + timeout (thread)
│       │   ├── file_manager.py              ← File I/O (read/write Markdown, JSON)
│       │   ├── latex_compiler.py            ← LaTeX generation + 4-pass compile
│       │   └── cost_tracker.py              ← Token & USD cost analysis
│       └── shared/
│           ├── ipc_models.py                ← AgentMessage + AgentStatus dataclasses
│           ├── process_runner.py            ← AgentProcessRunner (one agent per Process)
│           ├── config.py                    ← ConfigManager
│           ├── gatekeeper.py                ← ApiGatekeeper (rate limit + queue + retry)
│           ├── llm_factory.py               ← build_llm() — Claude / Gemini toggle
│           ├── models.py                    ← AgentOutput, ArticleResult dataclasses
│           └── version.py
├── tests/
│   ├── unit/
│   │   ├── test_agents/                     ← Agent builder tests (mocked)
│   │   ├── test_services/                   ← Service tests (mocked)
│   │   │   ├── test_crew_service.py
│   │   │   ├── test_process_orchestrator.py
│   │   │   ├── test_gatekeeper_router.py
│   │   │   ├── test_watchdog.py
│   │   │   └── test_file_manager.py
│   │   ├── test_shared/
│   │   │   ├── test_ipc_models.py
│   │   │   └── test_process_runner.py
│   │   ├── test_sdk/
│   │   │   └── test_sdk.py
│   │   └── test_tools/
│   └── integration/
│       ├── test_researcher_search.py        ← Live Serper search (skipped if no key)
│       ├── test_full_pipeline.py            ← Full generate_article() (skipped if no keys)
│       ├── test_process_isolation.py        ← Verifies distinct PIDs per agent
│       └── test_ipc_pipeline.py             ← IPC round-trip with real queues + mock agents
├── config/
│   ├── setup.json
│   ├── rate_limits.json
│   └── model_pricing.json
├── docs/
│   ├── PRD.md
│   ├── PLAN.md
│   └── TODO.md
├── skills/                                  ← Per-agent SKILL.md files
├── data/
├── results/                                 ← Generated output (committed as sample)
├── assets/
├── .env-example
├── pyproject.toml
└── uv.lock
```

---

## Running Tests

### Unit Tests (no API keys required)

```powershell
uv run pytest tests/unit/ -v
```

### Process-Specific Unit Tests

```powershell
# Test process isolation, IPC, Gatekeeper, Watchdog — all mocked
uv run pytest tests/unit/test_services/test_watchdog.py -v
uv run pytest tests/unit/test_services/test_gatekeeper_router.py -v
uv run pytest tests/unit/test_shared/test_process_runner.py -v
```

### Integration Tests (API keys required — auto-skipped if absent)

```powershell
uv run pytest tests/integration/ -v --no-cov
```

### Full Suite with Coverage

```powershell
uv run pytest tests/ --cov=src --cov-report=term-missing
```

Target: **≥ 85% coverage**, **zero ruff violations**.

### Linting

```powershell
uv run ruff check src/ tests/
```

---

## Evaluation Criteria Checklist

| Criterion | How to Verify |
|-----------|--------------|
| Each agent runs in an isolated OS process | Run `test_process_isolation.py`; confirm 6 distinct PIDs |
| IPC messages validated by GatekeeperRouter | Run `test_gatekeeper_router.py`; malformed messages raise error |
| Watchdog terminates timed-out agents | Run `test_watchdog.py`; hung process terminated within timeout |
| All links and citations clickable in PDF | Open `results/article.pdf`; click each citation and TOC entry |
| BiDi text direction correct | Hebrew text reads right-to-left without corruption |
| No table overflows page margins | All tables visible within page bounds |
| All formulas compiled as LaTeX math | No formula appears as plain text (`sigma`, `integral`, etc.) |
| Graph embedded in PDF | `results/figures/graph.pdf` present; visible figure in article body |

---

## Troubleshooting

### `429 RESOURCE_EXHAUSTED` / agent runs very slowly
Gemini free tier enforces 15 RPM. The retry wrapper backs off 60 s → 300 s automatically (up to 20 retries per call). If you consistently hit this, either wait and retry later, or upgrade to a Gemini API key with billing enabled.

### `anthropic.BadRequestError: Your credit balance is too low`
Anthropic billing issue when `ACTIVE_LLM=claude`. Add credits at [console.anthropic.com](https://console.anthropic.com) → Plans & Billing, or switch to `ACTIVE_LLM=gemini`.

### `SERPER_API_KEY environment variable not set`
Ensure `.env` exists at the project root and contains `SERPER_API_KEY=...`. Run from the project root directory.

### `AgentTimeoutError: ResearcherAgent exceeded timeout`
The researcher agent took longer than `AGENT_TIMEOUT_SECONDS["Senior Academic Researcher"]`. Increase the timeout in `constants.py` or check your network/API key.

### `GatekeeperValidationError: empty content from WriterAgent`
The writer produced no output — usually an LLM API error. Check `LLM_API_KEY`/`GEMINI_API_KEY` and your API quota.

### Agent process died unexpectedly (`status="error"`)
Check the console for the traceback from inside the subprocess. Common causes: missing API key inside the subprocess environment, serialisation error, out-of-memory.

### `xelatex: command not found`
MiKTeX is not in PATH. Open a new terminal after installation, or add MiKTeX `bin/` to your PATH.

### `Package fontspec Error: The font "Times New Roman" cannot be found`
Required fonts are not installed. On Windows, Times New Roman, Arial, and Courier New ship with Microsoft Office and are normally present. If missing, install the [Microsoft Core Fonts](https://corefonts.sourceforge.net/) package.

### PDF is fewer than 15 pages
Increase `article.target_pages` in `config/setup.json` or adjust agent prompts in `services/tasks/task_definitions.py`.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `crewai` | Multi-agent orchestration framework |
| `crewai-tools` | SerperDevTool, FileWriterTool, FileReadTool |
| `anthropic` | Anthropic API client (used by crewai's native Anthropic provider) |
| `google-generativeai` | Gemini API client (used by crewai's native Gemini provider) |
| `matplotlib` | Programmatic graph generation |
| `python-dotenv` | Load `.env` into environment |
| `multiprocessing` | OS-level process isolation *(stdlib — no install needed)* |

> **No LiteLLM required.** CrewAI's native providers (`AnthropicNativeLLM`, `GeminiNativeLLM`) are used directly. LiteLLM is not installed and `is_litellm=True` must not be passed.

Dev dependencies: `pytest`, `pytest-cov`, `ruff`.

---

## License

Academic coursework — MSC AI Agents Course, HW3. Not licensed for commercial use.

---

## Author

Student — MSC AI Agents Course, HW3  
Lecturer: Dr. Yoram Segal
