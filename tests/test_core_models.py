# -*- coding: utf-8 -*-
"""
Comprehensive pytest tests for src/core/models.py.

Tests cover:
- JobStep enum values
- JobState enum values
- VideoRef dataclass initialization and defaults
- JobSpec initialization, to_dict(), and from_dict() serialization
- JobStatus initialization, state transition methods, and serialization
- Edge cases like invalid enum values
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from src.core.models import JobSpec, JobState, JobStatus, JobStep, VideoRef


# ============================================================================
# TEST CLASS: JobStep Enum
# ============================================================================


class TestJobStep:
    """Tests for JobStep enum values and behavior."""

    def test_jobstep_download_value(self):
        """JobStep.DOWNLOAD has value 'download'."""
        assert JobStep.DOWNLOAD.value == "download"

    def test_jobstep_transcribe_value(self):
        """JobStep.TRANSCRIBE has value 'transcribe'."""
        assert JobStep.TRANSCRIBE.value == "transcribe"

    def test_jobstep_generate_clips_value(self):
        """JobStep.GENERATE_CLIPS has value 'generate_clips'."""
        assert JobStep.GENERATE_CLIPS.value == "generate_clips"

    def test_jobstep_export_clips_value(self):
        """JobStep.EXPORT_CLIPS has value 'export_clips'."""
        assert JobStep.EXPORT_CLIPS.value == "export_clips"

    def test_jobstep_export_shorts_value(self):
        """JobStep.EXPORT_SHORTS has value 'export_shorts'."""
        assert JobStep.EXPORT_SHORTS.value == "export_shorts"

    def test_jobstep_is_str_enum(self):
        """JobStep inherits from str, so values can be used as strings."""
        assert isinstance(JobStep.DOWNLOAD, str)
        assert JobStep.DOWNLOAD == "download"

    def test_jobstep_all_values(self):
        """JobStep has exactly 5 members."""
        assert len(JobStep) == 5
        members = {m.value for m in JobStep}
        assert members == {
            "download",
            "transcribe",
            "generate_clips",
            "export_clips",
            "export_shorts",
        }

    def test_jobstep_from_value(self):
        """JobStep can be instantiated from string value."""
        assert JobStep("download") == JobStep.DOWNLOAD
        assert JobStep("transcribe") == JobStep.TRANSCRIBE
        assert JobStep("generate_clips") == JobStep.GENERATE_CLIPS
        assert JobStep("export_clips") == JobStep.EXPORT_CLIPS
        assert JobStep("export_shorts") == JobStep.EXPORT_SHORTS

    def test_jobstep_invalid_value_raises(self):
        """JobStep raises ValueError for invalid value."""
        with pytest.raises(ValueError, match="'invalid' is not a valid JobStep"):
            JobStep("invalid")


# ============================================================================
# TEST CLASS: JobState Enum
# ============================================================================


class TestJobState:
    """Tests for JobState enum values and behavior."""

    def test_jobstate_pending_value(self):
        """JobState.PENDING has value 'pending'."""
        assert JobState.PENDING.value == "pending"

    def test_jobstate_running_value(self):
        """JobState.RUNNING has value 'running'."""
        assert JobState.RUNNING.value == "running"

    def test_jobstate_succeeded_value(self):
        """JobState.SUCCEEDED has value 'succeeded'."""
        assert JobState.SUCCEEDED.value == "succeeded"

    def test_jobstate_failed_value(self):
        """JobState.FAILED has value 'failed'."""
        assert JobState.FAILED.value == "failed"

    def test_jobstate_canceled_value(self):
        """JobState.CANCELED has value 'canceled'."""
        assert JobState.CANCELED.value == "canceled"

    def test_jobstate_is_str_enum(self):
        """JobState inherits from str, so values can be used as strings."""
        assert isinstance(JobState.PENDING, str)
        assert JobState.PENDING == "pending"

    def test_jobstate_all_values(self):
        """JobState has exactly 5 members."""
        assert len(JobState) == 5
        members = {m.value for m in JobState}
        assert members == {"pending", "running", "succeeded", "failed", "canceled"}

    def test_jobstate_from_value(self):
        """JobState can be instantiated from string value."""
        assert JobState("pending") == JobState.PENDING
        assert JobState("running") == JobState.RUNNING
        assert JobState("succeeded") == JobState.SUCCEEDED
        assert JobState("failed") == JobState.FAILED
        assert JobState("canceled") == JobState.CANCELED

    def test_jobstate_invalid_value_raises(self):
        """JobState raises ValueError for invalid value."""
        with pytest.raises(ValueError, match="'invalid' is not a valid JobState"):
            JobState("invalid")


# ============================================================================
# TEST CLASS: VideoRef
# ============================================================================


class TestVideoRef:
    """Tests for VideoRef dataclass initialization and attributes."""

    def test_videoref_required_fields(self):
        """VideoRef requires video_id, filename, and path."""
        ref = VideoRef(video_id="vid-123", filename="video.mp4", path="/videos/video.mp4")
        assert ref.video_id == "vid-123"
        assert ref.filename == "video.mp4"
        assert ref.path == "/videos/video.mp4"

    def test_videoref_content_type_defaults_to_tutorial(self):
        """VideoRef content_type defaults to 'tutorial'."""
        ref = VideoRef(video_id="vid-123", filename="video.mp4", path="/videos/video.mp4")
        assert ref.content_type == "tutorial"

    def test_videoref_content_type_can_be_set(self):
        """VideoRef content_type can be explicitly set."""
        ref = VideoRef(
            video_id="vid-123",
            filename="video.mp4",
            path="/videos/video.mp4",
            content_type="interview",
        )
        assert ref.content_type == "interview"

    def test_videoref_preset_defaults_to_empty_dict(self):
        """VideoRef preset defaults to empty dict."""
        ref = VideoRef(video_id="vid-123", filename="video.mp4", path="/videos/video.mp4")
        assert ref.preset == {}

    def test_videoref_preset_can_be_set(self):
        """VideoRef preset can be explicitly set."""
        preset = {"resolution": "1080p", "framerate": 30}
        ref = VideoRef(
            video_id="vid-123",
            filename="video.mp4",
            path="/videos/video.mp4",
            preset=preset,
        )
        assert ref.preset == preset

    def test_videoref_is_frozen(self):
        """VideoRef is a frozen dataclass (immutable)."""
        ref = VideoRef(video_id="vid-123", filename="video.mp4", path="/videos/video.mp4")
        with pytest.raises(FrozenInstanceError):
            ref.video_id = "new-id"

    def test_videoref_preset_default_is_independent(self):
        """Each VideoRef gets its own independent preset dict."""
        ref1 = VideoRef(video_id="vid-1", filename="a.mp4", path="/a.mp4")
        ref2 = VideoRef(video_id="vid-2", filename="b.mp4", path="/b.mp4")
        assert ref1.preset is not ref2.preset


# ============================================================================
# TEST CLASS: JobSpec
# ============================================================================


class TestJobSpec:
    """Tests for JobSpec dataclass initialization and serialization."""

    def test_jobspec_required_fields(self):
        """JobSpec requires job_id, video_ids, and steps."""
        spec = JobSpec(
            job_id="job-123",
            video_ids=["vid-1", "vid-2"],
            steps=[JobStep.TRANSCRIBE, JobStep.GENERATE_CLIPS],
        )
        assert spec.job_id == "job-123"
        assert spec.video_ids == ["vid-1", "vid-2"]
        assert spec.steps == [JobStep.TRANSCRIBE, JobStep.GENERATE_CLIPS]

    def test_jobspec_settings_defaults_to_empty_dict(self):
        """JobSpec settings defaults to empty dict."""
        spec = JobSpec(job_id="job-123", video_ids=["vid-1"], steps=[JobStep.TRANSCRIBE])
        assert spec.settings == {}

    def test_jobspec_settings_can_be_set(self):
        """JobSpec settings can be explicitly set."""
        settings = {"skip_done": True, "output_format": "mp4"}
        spec = JobSpec(
            job_id="job-123",
            video_ids=["vid-1"],
            steps=[JobStep.TRANSCRIBE],
            settings=settings,
        )
        assert spec.settings == settings

    def test_jobspec_is_mutable(self):
        """JobSpec is a regular dataclass (mutable)."""
        spec = JobSpec(job_id="job-123", video_ids=["vid-1"], steps=[JobStep.TRANSCRIBE])
        spec.job_id = "new-id"
        assert spec.job_id == "new-id"

    def test_jobspec_to_dict(self):
        """JobSpec.to_dict() returns correct dictionary representation."""
        spec = JobSpec(
            job_id="job-123",
            video_ids=["vid-1", "vid-2"],
            steps=[JobStep.TRANSCRIBE, JobStep.EXPORT_CLIPS],
            settings={"skip_done": True},
        )
        result = spec.to_dict()

        assert result["job_id"] == "job-123"
        assert result["video_ids"] == ["vid-1", "vid-2"]
        assert result["steps"] == ["transcribe", "export_clips"]
        assert result["settings"] == {"skip_done": True}

    def test_jobspec_to_dict_steps_are_values(self):
        """JobSpec.to_dict() converts JobStep enums to string values."""
        spec = JobSpec(
            job_id="job-123",
            video_ids=["vid-1"],
            steps=[JobStep.DOWNLOAD, JobStep.TRANSCRIBE],
        )
        result = spec.to_dict()
        assert all(isinstance(s, str) for s in result["steps"])
        assert result["steps"] == ["download", "transcribe"]

    def test_jobspec_from_dict(self):
        """JobSpec.from_dict() creates JobSpec from dictionary."""
        data = {
            "job_id": "job-123",
            "video_ids": ["vid-1", "vid-2"],
            "steps": ["transcribe", "generate_clips"],
            "settings": {"output_format": "mp4"},
        }
        spec = JobSpec.from_dict(data)

        assert spec.job_id == "job-123"
        assert spec.video_ids == ["vid-1", "vid-2"]
        assert spec.steps == [JobStep.TRANSCRIBE, JobStep.GENERATE_CLIPS]
        assert spec.settings == {"output_format": "mp4"}

    def test_jobspec_from_dict_handles_missing_optional_fields(self):
        """JobSpec.from_dict() handles missing optional fields."""
        data = {"job_id": "job-123"}
        spec = JobSpec.from_dict(data)

        assert spec.job_id == "job-123"
        assert spec.video_ids == []
        assert spec.steps == []
        assert spec.settings == {}

    def test_jobspec_serialization_roundtrip(self):
        """JobSpec survives to_dict() -> from_dict() roundtrip."""
        original = JobSpec(
            job_id="job-123",
            video_ids=["vid-1", "vid-2"],
            steps=[JobStep.TRANSCRIBE, JobStep.GENERATE_CLIPS, JobStep.EXPORT_SHORTS],
            settings={"skip_done": True, "quality": "high"},
        )
        data = original.to_dict()
        restored = JobSpec.from_dict(data)

        assert restored.job_id == original.job_id
        assert restored.video_ids == original.video_ids
        assert restored.steps == original.steps
        assert restored.settings == original.settings

    def test_jobspec_from_dict_converts_job_id_to_string(self):
        """JobSpec.from_dict() converts job_id to string."""
        data = {"job_id": 123, "video_ids": [], "steps": [], "settings": {}}
        spec = JobSpec.from_dict(data)
        assert spec.job_id == "123"
        assert isinstance(spec.job_id, str)

    def test_jobspec_from_dict_converts_video_ids_to_strings(self):
        """JobSpec.from_dict() converts video_ids elements to strings."""
        data = {"job_id": "job-123", "video_ids": [1, 2, 3], "steps": [], "settings": {}}
        spec = JobSpec.from_dict(data)
        assert spec.video_ids == ["1", "2", "3"]
        assert all(isinstance(v, str) for v in spec.video_ids)


# ============================================================================
# TEST CLASS: JobStatus
# ============================================================================


class TestJobStatus:
    """Tests for JobStatus dataclass initialization and state transitions."""

    def test_jobstatus_default_values(self):
        """JobStatus has correct default values."""
        status = JobStatus()
        assert status.state == JobState.PENDING
        assert status.progress_current == 0
        assert status.progress_total == 0
        assert status.label == ""
        assert status.started_at is None
        assert status.finished_at is None
        assert status.error is None

    def test_jobstatus_can_set_all_fields(self):
        """JobStatus can have all fields explicitly set."""
        status = JobStatus(
            state=JobState.RUNNING,
            progress_current=5,
            progress_total=10,
            label="Processing",
            started_at="2024-01-01T12:00:00",
            finished_at="2024-01-01T12:30:00",
            error="Some error",
        )
        assert status.state == JobState.RUNNING
        assert status.progress_current == 5
        assert status.progress_total == 10
        assert status.label == "Processing"
        assert status.started_at == "2024-01-01T12:00:00"
        assert status.finished_at == "2024-01-01T12:30:00"
        assert status.error == "Some error"

    def test_jobstatus_is_mutable(self):
        """JobStatus is a regular dataclass (mutable)."""
        status = JobStatus()
        status.state = JobState.RUNNING
        assert status.state == JobState.RUNNING

    def test_jobstatus_mark_started(self):
        """mark_started() sets state to RUNNING and records started_at."""
        status = JobStatus()
        assert status.state == JobState.PENDING
        assert status.started_at is None

        status.mark_started()

        assert status.state == JobState.RUNNING
        assert status.started_at is not None
        # ISO format pattern
        assert "T" in status.started_at

    def test_jobstatus_mark_finished_ok(self):
        """mark_finished_ok() sets state to SUCCEEDED and records finished_at."""
        status = JobStatus()
        status.mark_started()

        status.mark_finished_ok()

        assert status.state == JobState.SUCCEEDED
        assert status.finished_at is not None
        assert status.error is None

    def test_jobstatus_mark_failed(self):
        """mark_failed() sets state to FAILED, records error and finished_at."""
        status = JobStatus()
        status.mark_started()

        status.mark_failed("Transcription failed")

        assert status.state == JobState.FAILED
        assert status.error == "Transcription failed"
        assert status.finished_at is not None

    def test_jobstatus_state_transition_pending_to_running(self):
        """JobStatus can transition from PENDING to RUNNING."""
        status = JobStatus()
        assert status.state == JobState.PENDING
        status.mark_started()
        assert status.state == JobState.RUNNING

    def test_jobstatus_state_transition_running_to_succeeded(self):
        """JobStatus can transition from RUNNING to SUCCEEDED."""
        status = JobStatus()
        status.mark_started()
        assert status.state == JobState.RUNNING
        status.mark_finished_ok()
        assert status.state == JobState.SUCCEEDED

    def test_jobstatus_state_transition_running_to_failed(self):
        """JobStatus can transition from RUNNING to FAILED."""
        status = JobStatus()
        status.mark_started()
        assert status.state == JobState.RUNNING
        status.mark_failed("Error occurred")
        assert status.state == JobState.FAILED

    def test_jobstatus_to_dict(self):
        """JobStatus.to_dict() returns correct dictionary representation."""
        status = JobStatus(
            state=JobState.RUNNING,
            progress_current=3,
            progress_total=10,
            label="Exporting",
            started_at="2024-01-01T12:00:00",
            finished_at=None,
            error=None,
        )
        result = status.to_dict()

        assert result["state"] == "running"
        assert result["progress_current"] == 3
        assert result["progress_total"] == 10
        assert result["label"] == "Exporting"
        assert result["started_at"] == "2024-01-01T12:00:00"
        assert result["finished_at"] is None
        assert result["error"] is None

    def test_jobstatus_to_dict_state_is_value(self):
        """JobStatus.to_dict() converts JobState enum to string value."""
        status = JobStatus(state=JobState.FAILED)
        result = status.to_dict()
        assert result["state"] == "failed"
        assert isinstance(result["state"], str)

    def test_jobstatus_from_dict(self):
        """JobStatus.from_dict() creates JobStatus from dictionary."""
        data = {
            "state": "succeeded",
            "progress_current": 10,
            "progress_total": 10,
            "label": "Done",
            "started_at": "2024-01-01T12:00:00",
            "finished_at": "2024-01-01T12:30:00",
            "error": None,
        }
        status = JobStatus.from_dict(data)

        assert status.state == JobState.SUCCEEDED
        assert status.progress_current == 10
        assert status.progress_total == 10
        assert status.label == "Done"
        assert status.started_at == "2024-01-01T12:00:00"
        assert status.finished_at == "2024-01-01T12:30:00"
        assert status.error is None

    def test_jobstatus_from_dict_handles_missing_fields(self):
        """JobStatus.from_dict() handles missing fields with defaults."""
        data = {}
        status = JobStatus.from_dict(data)

        assert status.state == JobState.PENDING
        assert status.progress_current == 0
        assert status.progress_total == 0
        assert status.label == ""
        assert status.started_at is None
        assert status.finished_at is None
        assert status.error is None

    def test_jobstatus_from_dict_handles_none_state(self):
        """JobStatus.from_dict() handles None state by defaulting to PENDING."""
        data = {"state": None}
        status = JobStatus.from_dict(data)
        assert status.state == JobState.PENDING

    def test_jobstatus_serialization_roundtrip(self):
        """JobStatus survives to_dict() -> from_dict() roundtrip."""
        original = JobStatus(
            state=JobState.FAILED,
            progress_current=5,
            progress_total=10,
            label="Processing video 3",
            started_at="2024-01-01T12:00:00",
            finished_at="2024-01-01T12:15:00",
            error="Out of memory",
        )
        data = original.to_dict()
        restored = JobStatus.from_dict(data)

        assert restored.state == original.state
        assert restored.progress_current == original.progress_current
        assert restored.progress_total == original.progress_total
        assert restored.label == original.label
        assert restored.started_at == original.started_at
        assert restored.finished_at == original.finished_at
        assert restored.error == original.error

    def test_jobstatus_from_dict_with_error(self):
        """JobStatus.from_dict() correctly restores error field."""
        data = {
            "state": "failed",
            "error": "Connection timeout",
        }
        status = JobStatus.from_dict(data)
        assert status.state == JobState.FAILED
        assert status.error == "Connection timeout"


# ============================================================================
# TEST CLASS: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_jobstep_invalid_value_error_message(self):
        """JobStep provides clear error message for invalid value."""
        with pytest.raises(ValueError) as exc_info:
            JobStep("not_a_step")
        assert "not_a_step" in str(exc_info.value)

    def test_jobstate_invalid_value_error_message(self):
        """JobState provides clear error message for invalid value."""
        with pytest.raises(ValueError) as exc_info:
            JobState("not_a_state")
        assert "not_a_state" in str(exc_info.value)

    def test_jobspec_from_dict_invalid_step_raises(self):
        """JobSpec.from_dict() raises ValueError for invalid step."""
        data = {
            "job_id": "job-123",
            "video_ids": ["vid-1"],
            "steps": ["invalid_step"],
            "settings": {},
        }
        with pytest.raises(ValueError, match="'invalid_step' is not a valid JobStep"):
            JobSpec.from_dict(data)

    def test_jobstatus_from_dict_invalid_state_raises(self):
        """JobStatus.from_dict() raises ValueError for invalid state."""
        data = {"state": "invalid_state"}
        with pytest.raises(ValueError, match="'invalid_state' is not a valid JobState"):
            JobStatus.from_dict(data)

    def test_jobspec_empty_video_ids_list(self):
        """JobSpec can have empty video_ids list."""
        spec = JobSpec(job_id="job-123", video_ids=[], steps=[JobStep.TRANSCRIBE])
        assert spec.video_ids == []
        data = spec.to_dict()
        assert data["video_ids"] == []

    def test_jobspec_empty_steps_list(self):
        """JobSpec can have empty steps list."""
        spec = JobSpec(job_id="job-123", video_ids=["vid-1"], steps=[])
        assert spec.steps == []
        data = spec.to_dict()
        assert data["steps"] == []

    def test_jobstatus_mark_failed_empty_string_error(self):
        """mark_failed() accepts empty string as error message."""
        status = JobStatus()
        status.mark_started()
        status.mark_failed("")
        assert status.state == JobState.FAILED
        assert status.error == ""

    def test_videoref_empty_strings(self):
        """VideoRef accepts empty strings for required fields."""
        ref = VideoRef(video_id="", filename="", path="")
        assert ref.video_id == ""
        assert ref.filename == ""
        assert ref.path == ""
