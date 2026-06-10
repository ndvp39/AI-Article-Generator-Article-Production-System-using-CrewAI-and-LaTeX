"""Helpers for writing and reading per-call cost records from agent subprocesses."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from article_generator.constants import RESULTS_DIR
from article_generator.shared.gatekeeper_models import CallRecord

logger = logging.getLogger(__name__)

AGENT_COSTS_DIR: Path = RESULTS_DIR / "agent_costs"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


def append_cost_record(agent_name: str, model: str, input_tokens: int, output_tokens: int) -> None:
    """Append one call record to results/agent_costs/<agent_name>.jsonl."""
    try:
        AGENT_COSTS_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "agent_name": agent_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "timestamp": time.time(),
        }
        path = AGENT_COSTS_DIR / f"{agent_name}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.debug("append_cost_record failed: %s", exc)


def load_subprocess_records() -> list[CallRecord]:
    """Read per-call token records written by agent subprocesses."""
    records: list[CallRecord] = []
    if not AGENT_COSTS_DIR.exists():
        return records
    for jsonl_path in AGENT_COSTS_DIR.glob("*.jsonl"):
        try:
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                records.append(CallRecord(
                    call_id=f"subprocess-{len(records)}",
                    agent_name=data.get("agent_name", ""),
                    model=data.get("model", ""),
                    input_tokens=int(data.get("input_tokens", 0)),
                    output_tokens=int(data.get("output_tokens", 0)),
                    timestamp=str(data.get("timestamp", "")),
                    duration_seconds=0.0,
                    success=True,
                ))
        except Exception as exc:  # noqa: BLE001
            logger.warning("load_subprocess_records: failed to parse %s: %s", jsonl_path, exc)
    return records
