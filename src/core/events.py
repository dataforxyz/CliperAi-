from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .models import JobState


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class CoreEvent:
    job_id: str
    video_id: str | None = None
    ts: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


@dataclass(frozen=True)
class LogEvent(CoreEvent):
    level: LogLevel = LogLevel.INFO
    message: str = ""


@dataclass(frozen=True)
class ProgressEvent(CoreEvent):
    current: int = 0
    total: int = 0
    label: str = ""


@dataclass(frozen=True)
class StateEvent(CoreEvent):
    updates: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JobStatusEvent(CoreEvent):
    state: JobState = JobState.PENDING
    error: str | None = None
