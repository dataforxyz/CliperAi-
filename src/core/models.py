from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class JobStep(str, Enum):
    DOWNLOAD = "download"
    TRANSCRIBE = "transcribe"
    GENERATE_CLIPS = "generate_clips"
    EXPORT_CLIPS = "export_clips"
    EXPORT_SHORTS = "export_shorts"


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class VideoRef:
    video_id: str
    filename: str
    path: str
    content_type: str = "tutorial"
    preset: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobSpec:
    job_id: str
    video_ids: list[str]
    steps: list[JobStep]
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "video_ids": list(self.video_ids),
            "steps": [s.value for s in self.steps],
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobSpec:
        return cls(
            job_id=str(data["job_id"]),
            video_ids=[str(v) for v in (data.get("video_ids") or [])],
            steps=[JobStep(s) for s in (data.get("steps") or [])],
            settings=dict(data.get("settings") or {}),
        )


@dataclass
class JobStatus:
    state: JobState = JobState.PENDING
    progress_current: int = 0
    progress_total: int = 0
    label: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def mark_started(self) -> None:
        self.state = JobState.RUNNING
        self.started_at = datetime.now().isoformat(timespec="seconds")

    def mark_finished_ok(self) -> None:
        self.state = JobState.SUCCEEDED
        self.finished_at = datetime.now().isoformat(timespec="seconds")

    def mark_failed(self, error: str) -> None:
        self.state = JobState.FAILED
        self.error = error
        self.finished_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "progress_current": self.progress_current,
            "progress_total": self.progress_total,
            "label": self.label,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobStatus:
        return cls(
            state=JobState(data.get("state") or JobState.PENDING.value),
            progress_current=int(data.get("progress_current") or 0),
            progress_total=int(data.get("progress_total") or 0),
            label=str(data.get("label") or ""),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            error=data.get("error"),
        )
