from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


def _new_message_id() -> str:
    return str(uuid.uuid4())


def _now() -> float:
    return time.time()


@dataclass
class AgentMessage:
    """Typed IPC message passed between agent processes via multiprocessing.Queue."""

    sender: str
    recipient: str
    content: str
    topic: str
    message_id: str = field(default_factory=_new_message_id)
    timestamp: float = field(default_factory=_now)
    message_type: str = "output"  # "input" | "output" | "error"


@dataclass
class AgentStatus:
    """Snapshot of an agent process's health, produced and updated by Watchdog."""

    agent_name: str
    pid: int | None
    status: str  # "running" | "done" | "error" | "timeout"
    started_at: float
    finished_at: float | None = None
