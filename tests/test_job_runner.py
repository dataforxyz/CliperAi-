"""
Comprehensive pytest tests for JobRunner.

Tests cover:
- JobRunner initialization with StateManager
- run_job() execution flow
- Event emission patterns (JobStatusEvent, ProgressEvent, LogEvent, StateEvent)
- Step execution ordering
- Error handling with proper state transitions
- Resume capability for interrupted jobs (skip_done behavior)
- Directory structure creation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.events import (
    JobStatusEvent,
    LogEvent,
    LogLevel,
    ProgressEvent,
)
from src.core.job_runner import JobRunner
from src.core.models import JobSpec, JobState, JobStep

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_state_manager():
    """
    Create a MagicMock StateManager with required methods configured.
    """
    sm = MagicMock()
    sm.get_video_path.return_value = "/videos/test_video.mp4"
    sm.get_video_state.return_value = {}
    sm.is_transcribed.return_value = False
    sm.is_shorts_exported.return_value = False
    sm.load_settings.return_value = {"_wizard_completed": True}
    sm.get_setting.return_value = None
    return sm


@pytest.fixture
def event_collector():
    """
    Provide an emit callback that captures all emitted events.
    """
    events: list[object] = []

    def emit(event: object) -> None:
        events.append(event)

    return events, emit


@pytest.fixture
def job_runner(mock_state_manager, event_collector):
    """
    Create a JobRunner with mocked StateManager and event collector.
    """
    events, emit = event_collector
    runner = JobRunner(state_manager=mock_state_manager, emit=emit)
    return runner, events, mock_state_manager


# ============================================================================
# TEST CLASS: JobRunner Initialization
# ============================================================================


class TestJobRunnerInit:
    """Tests for JobRunner constructor parameter binding and initial state."""

    def test_init_stores_state_manager(self, mock_state_manager, event_collector):
        """JobRunner stores the provided state_manager."""
        _, emit = event_collector
        runner = JobRunner(state_manager=mock_state_manager, emit=emit)
        assert runner.state_manager is mock_state_manager

    def test_init_stores_emit_callback(self, mock_state_manager, event_collector):
        """JobRunner stores the provided emit callback."""
        _, emit = event_collector
        runner = JobRunner(state_manager=mock_state_manager, emit=emit)
        assert runner.emit is emit

    def test_init_empty_dependency_cache(self, mock_state_manager, event_collector):
        """JobRunner initializes with empty dependency cache."""
        _, emit = event_collector
        runner = JobRunner(state_manager=mock_state_manager, emit=emit)
        assert runner._dependency_ok_cache == set()


# ============================================================================
# TEST CLASS: run_job Event Emission
# ============================================================================


class TestRunJobEventEmission:
    """Tests for event emission during run_job execution."""

    def test_run_job_emits_started_event(self, job_runner, tmp_project_dir):
        """run_job emits JobStatusEvent with JobState.RUNNING on job start."""
        runner, events, _sm = job_runner
        job = JobSpec(
            job_id="test-started",
            video_ids=["vid1"],
            steps=[],
            settings={},
        )

        runner.run_job(job)

        # First event should be JobStatusEvent with RUNNING state
        status_events = [e for e in events if isinstance(e, JobStatusEvent)]
        assert len(status_events) >= 1
        assert status_events[0].job_id == "test-started"
        assert status_events[0].state == JobState.RUNNING

    def test_run_job_emits_finished_ok_event(self, job_runner, tmp_project_dir):
        """run_job emits JobStatusEvent with JobState.SUCCEEDED on completion."""
        runner, events, _sm = job_runner
        job = JobSpec(
            job_id="test-finished",
            video_ids=["vid1"],
            steps=[],  # No steps = immediate success
            settings={},
        )

        result = runner.run_job(job)

        # Last JobStatusEvent should have SUCCEEDED state
        status_events = [e for e in events if isinstance(e, JobStatusEvent)]
        assert len(status_events) >= 2
        assert status_events[-1].job_id == "test-finished"
        assert status_events[-1].state == JobState.SUCCEEDED
        assert result.state == JobState.SUCCEEDED

    def test_run_job_emits_progress_events(self, job_runner, tmp_project_dir):
        """run_job emits ProgressEvent before and after each step."""
        runner, events, _sm = job_runner

        # Mock transcription step to prevent actual execution
        with patch.object(runner, "_step_transcribe"):
            job = JobSpec(
                job_id="test-progress",
                video_ids=["vid1"],
                steps=[JobStep.TRANSCRIBE],
                settings={},
            )
            runner.run_job(job)

        # Should have progress events
        progress_events = [e for e in events if isinstance(e, ProgressEvent)]
        assert len(progress_events) >= 2  # Before and after step

        # First progress event should have current=0
        assert progress_events[0].current == 0
        assert progress_events[0].total == 1
        assert progress_events[0].video_id == "vid1"

        # Second progress event should have current=1 (after step)
        assert progress_events[1].current == 1

    def test_run_job_failure_emits_error_events(self, job_runner, tmp_project_dir):
        """run_job emits LogEvent and JobStatusEvent with FAILED on exception."""
        runner, events, _sm = job_runner

        # Make transcription step raise an exception
        with patch.object(
            runner, "_step_transcribe", side_effect=RuntimeError("Test error")
        ):
            job = JobSpec(
                job_id="test-failure",
                video_ids=["vid1"],
                steps=[JobStep.TRANSCRIBE],
                settings={},
            )
            result = runner.run_job(job)

        # Should have error log event
        log_events = [
            e for e in events if isinstance(e, LogEvent) and e.level == LogLevel.ERROR
        ]
        assert len(log_events) >= 1
        assert "Test error" in log_events[-1].message

        # Should have FAILED status event
        status_events = [e for e in events if isinstance(e, JobStatusEvent)]
        assert status_events[-1].state == JobState.FAILED
        assert status_events[-1].error == "Test error"
        assert result.state == JobState.FAILED


# ============================================================================
# TEST CLASS: _run_step Routing
# ============================================================================


class TestRunStepRouting:
    """Tests for _run_step dispatcher routing to correct step handlers."""

    def test_run_step_routes_to_transcribe(self, job_runner, tmp_project_dir):
        """_run_step calls _step_transcribe for JobStep.TRANSCRIBE."""
        runner, _events, _sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(runner, "_step_transcribe") as mock_transcribe:
            runner._run_step(
                job_id="job1",
                video_id="vid1",
                step=JobStep.TRANSCRIBE,
                settings={},
                run_output_dir=run_output_dir,
            )

        mock_transcribe.assert_called_once()
        call_kwargs = mock_transcribe.call_args[1]
        assert call_kwargs["job_id"] == "job1"
        assert call_kwargs["video_id"] == "vid1"

    def test_run_step_routes_to_generate_clips(self, job_runner, tmp_project_dir):
        """_run_step calls _step_generate_clips for JobStep.GENERATE_CLIPS."""
        runner, _events, _sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(runner, "_step_generate_clips") as mock_gen:
            runner._run_step(
                job_id="job1",
                video_id="vid1",
                step=JobStep.GENERATE_CLIPS,
                settings={},
                run_output_dir=run_output_dir,
            )

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["job_id"] == "job1"
        assert call_kwargs["video_id"] == "vid1"

    def test_run_step_routes_to_export_clips(self, job_runner, tmp_project_dir):
        """_run_step calls _step_export_clips for JobStep.EXPORT_CLIPS."""
        runner, _events, _sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(runner, "_step_export_clips") as mock_export:
            runner._run_step(
                job_id="job1",
                video_id="vid1",
                step=JobStep.EXPORT_CLIPS,
                settings={},
                run_output_dir=run_output_dir,
            )

        mock_export.assert_called_once()
        call_kwargs = mock_export.call_args[1]
        assert call_kwargs["job_id"] == "job1"
        assert call_kwargs["video_id"] == "vid1"

    def test_run_step_routes_to_export_shorts(self, job_runner, tmp_project_dir):
        """_run_step calls _step_export_shorts for JobStep.EXPORT_SHORTS."""
        runner, _events, _sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(runner, "_step_export_shorts") as mock_shorts:
            runner._run_step(
                job_id="job1",
                video_id="vid1",
                step=JobStep.EXPORT_SHORTS,
                settings={},
                run_output_dir=run_output_dir,
            )

        mock_shorts.assert_called_once()
        call_kwargs = mock_shorts.call_args[1]
        assert call_kwargs["job_id"] == "job1"
        assert call_kwargs["video_id"] == "vid1"

    def test_run_step_raises_for_download(self, job_runner, tmp_project_dir):
        """_run_step raises ValueError for JobStep.DOWNLOAD."""
        runner, _events, _sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError, match="DOWNLOAD is not supported"):
            runner._run_step(
                job_id="job1",
                video_id="vid1",
                step=JobStep.DOWNLOAD,
                settings={},
                run_output_dir=run_output_dir,
            )


# ============================================================================
# TEST CLASS: Step Skip Behavior (Resume Capability)
# ============================================================================


class TestStepSkipBehavior:
    """Tests for skip_done behavior enabling resume capability."""

    def test_transcribe_skips_when_already_done(self, job_runner, tmp_project_dir):
        """_step_transcribe skips when is_transcribed returns True."""
        runner, events, sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Configure state manager to indicate transcription is done
        sm.is_transcribed.return_value = True
        sm.get_video_state.return_value = {
            "transcript_path": "/some/path/transcript.json",
        }

        # This should NOT raise or call Transcriber
        runner._step_transcribe(
            job_id="job1",
            video_id="vid1",
            settings={"skip_done": True},
            run_output_dir=run_output_dir,
        )

        # Should have emitted a skip log message
        log_events = [e for e in events if isinstance(e, LogEvent)]
        skip_logs = [
            e
            for e in log_events
            if "skipping" in e.message.lower()
            or "already transcribed" in e.message.lower()
        ]
        assert len(skip_logs) >= 1

    def test_generate_clips_skips_when_already_done(self, job_runner, tmp_project_dir):
        """_step_generate_clips skips when clips_generated is True."""
        runner, events, sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Configure state manager to indicate clips are generated
        sm.get_video_state.return_value = {
            "transcript_path": "/some/path/transcript.json",
            "clips_generated": True,
            "clips_metadata_path": "/some/path/clips.json",
        }

        # This should NOT raise or call ClipsGenerator
        runner._step_generate_clips(
            job_id="job1",
            video_id="vid1",
            settings={"skip_done": True},
            run_output_dir=run_output_dir,
        )

        # Should have emitted a skip log message
        log_events = [e for e in events if isinstance(e, LogEvent)]
        skip_logs = [
            e
            for e in log_events
            if "skipping" in e.message.lower() or "already" in e.message.lower()
        ]
        assert len(skip_logs) >= 1

    def test_export_clips_skips_when_already_done(self, job_runner, tmp_project_dir):
        """_step_export_clips skips when clips_exported is True."""
        runner, events, sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Configure state manager to indicate clips are exported
        sm.get_video_state.return_value = {
            "clips": [{"start": 0, "end": 10}],
            "clips_exported": True,
            "exported_clips": ["/some/path/clip1.mp4"],
        }

        # This should NOT raise or call VideoExporter
        runner._step_export_clips(
            job_id="job1",
            video_id="vid1",
            settings={"skip_done": True},
            run_output_dir=run_output_dir,
        )

        # Should have emitted a skip log message
        log_events = [e for e in events if isinstance(e, LogEvent)]
        skip_logs = [
            e
            for e in log_events
            if "skipping" in e.message.lower() or "already" in e.message.lower()
        ]
        assert len(skip_logs) >= 1

    def test_shorts_skips_when_already_exported(self, job_runner, tmp_project_dir):
        """_step_export_shorts skips when is_shorts_exported returns True."""
        runner, events, sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        # Configure state manager to indicate shorts are exported
        sm.is_shorts_exported.return_value = True

        # This should NOT raise or call SubtitleGenerator/VideoExporter
        runner._step_export_shorts(
            job_id="job1",
            video_id="vid1",
            settings={"shorts": {"skip_done": True}},
            run_output_dir=run_output_dir,
        )

        # Should have emitted a skip log message
        log_events = [e for e in events if isinstance(e, LogEvent)]
        skip_logs = [
            e
            for e in log_events
            if "skipping" in e.message.lower() or "already" in e.message.lower()
        ]
        assert len(skip_logs) >= 1


# ============================================================================
# TEST CLASS: Directory Creation
# ============================================================================


class TestDirectoryCreation:
    """Tests for directory structure creation."""

    def test_ensure_run_output_dir_creates_cache_dir(self, job_runner, tmp_project_dir):
        """_ensure_run_output_dir creates output/.cache/{job_id}/ directory."""
        runner, _events, _sm = job_runner

        cache_dir = runner._ensure_run_output_dir(job_id="test-job", video_ids=["vid1"])

        assert cache_dir.exists()
        assert cache_dir.is_dir()
        assert "output" in str(cache_dir)
        assert ".cache" in str(cache_dir)
        assert "test-job" in str(cache_dir)

    def test_ensure_video_run_dir_creates_subdirectory(
        self, job_runner, tmp_project_dir
    ):
        """_ensure_video_run_dir creates per-video subdirectory."""
        runner, _events, _sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test-job"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        video_dir = runner._ensure_video_run_dir(
            run_output_dir=run_output_dir, video_id="vid1"
        )

        assert video_dir.exists()
        assert video_dir.is_dir()
        assert video_dir == run_output_dir / "vid1"


# ============================================================================
# TEST CLASS: Progress Calculation
# ============================================================================


class TestProgressCalculation:
    """Tests for progress total calculation."""

    def test_progress_total_calculation_single_video_single_step(
        self, job_runner, tmp_project_dir
    ):
        """progress_total = len(video_ids) * len(steps) for single video/step."""
        runner, _events, _sm = job_runner

        with patch.object(runner, "_step_transcribe"):
            job = JobSpec(
                job_id="test-progress",
                video_ids=["vid1"],
                steps=[JobStep.TRANSCRIBE],
                settings={},
            )
            result = runner.run_job(job)

        assert result.progress_total == 1  # 1 video * 1 step

    def test_progress_total_calculation_multiple_videos_multiple_steps(
        self, job_runner, tmp_project_dir
    ):
        """progress_total = len(video_ids) * len(steps) for multiple videos/steps."""
        runner, _events, _sm = job_runner

        with (
            patch.object(runner, "_step_transcribe"),
            patch.object(runner, "_step_generate_clips"),
        ):
            job = JobSpec(
                job_id="test-progress",
                video_ids=["vid1", "vid2", "vid3"],
                steps=[JobStep.TRANSCRIBE, JobStep.GENERATE_CLIPS],
                settings={},
            )
            result = runner.run_job(job)

        assert result.progress_total == 6  # 3 videos * 2 steps


# ============================================================================
# TEST CLASS: Step Ordering
# ============================================================================


class TestStepOrdering:
    """Tests for step execution ordering."""

    def test_step_ordering_multiple_videos_multiple_steps(
        self, job_runner, tmp_project_dir
    ):
        """Steps execute in video-then-step order."""
        runner, _events, _sm = job_runner
        execution_order: list[tuple] = []

        def track_transcribe(**kwargs):
            execution_order.append(("transcribe", kwargs["video_id"]))

        def track_generate_clips(**kwargs):
            execution_order.append(("generate_clips", kwargs["video_id"]))

        with (
            patch.object(runner, "_step_transcribe", side_effect=track_transcribe),
            patch.object(
                runner, "_step_generate_clips", side_effect=track_generate_clips
            ),
        ):
            job = JobSpec(
                job_id="test-order",
                video_ids=["vid1", "vid2"],
                steps=[JobStep.TRANSCRIBE, JobStep.GENERATE_CLIPS],
                settings={},
            )
            runner.run_job(job)

        # Should process all steps for vid1 before vid2
        expected_order = [
            ("transcribe", "vid1"),
            ("generate_clips", "vid1"),
            ("transcribe", "vid2"),
            ("generate_clips", "vid2"),
        ]
        assert execution_order == expected_order


# ============================================================================
# TEST CLASS: Job Status Transitions
# ============================================================================


class TestJobStatusTransitions:
    """Tests for job status state machine transitions."""

    def test_job_status_transitions_pending_to_running_to_succeeded(
        self, job_runner, tmp_project_dir
    ):
        """Job transitions from PENDING -> RUNNING -> SUCCEEDED on success."""
        runner, events, _sm = job_runner

        job = JobSpec(
            job_id="test-transitions",
            video_ids=["vid1"],
            steps=[],  # No steps for immediate success
            settings={},
        )
        result = runner.run_job(job)

        # Collect status events in order
        status_events = [e for e in events if isinstance(e, JobStatusEvent)]
        assert len(status_events) == 2

        # First: RUNNING
        assert status_events[0].state == JobState.RUNNING

        # Second: SUCCEEDED
        assert status_events[1].state == JobState.SUCCEEDED

        # Final result
        assert result.state == JobState.SUCCEEDED
        assert result.error is None

    def test_job_status_transitions_pending_to_running_to_failed(
        self, job_runner, tmp_project_dir
    ):
        """Job transitions from PENDING -> RUNNING -> FAILED on error."""
        runner, events, _sm = job_runner

        with patch.object(
            runner, "_step_transcribe", side_effect=Exception("Simulated failure")
        ):
            job = JobSpec(
                job_id="test-failure-transition",
                video_ids=["vid1"],
                steps=[JobStep.TRANSCRIBE],
                settings={},
            )
            result = runner.run_job(job)

        # Collect status events in order
        status_events = [e for e in events if isinstance(e, JobStatusEvent)]
        assert len(status_events) == 2

        # First: RUNNING
        assert status_events[0].state == JobState.RUNNING

        # Second: FAILED
        assert status_events[1].state == JobState.FAILED
        assert status_events[1].error == "Simulated failure"

        # Final result
        assert result.state == JobState.FAILED
        assert result.error == "Simulated failure"


# ============================================================================
# TEST CLASS: Integration with conftest.py Fixtures
# ============================================================================


class TestWithSharedFixtures:
    """Tests using shared fixtures from conftest.py."""

    def test_with_tmp_project_dir_fixture(
        self, tmp_project_dir, sample_job_spec, event_collector
    ):
        """JobRunner works with tmp_project_dir and sample_job_spec fixtures."""
        from src.utils.state_manager import get_state_manager

        events, emit = event_collector
        sm = get_state_manager()

        # Register a test video
        sm.register_video(
            video_id="test_video",
            filename="test_video.mp4",
            video_path=str(tmp_project_dir / "videos" / "test_video.mp4"),
        )

        runner = JobRunner(state_manager=sm, emit=emit)

        # Mock transcription to avoid actual execution
        with patch.object(runner, "_step_transcribe"):
            result = runner.run_job(sample_job_spec)

        assert result.state == JobState.SUCCEEDED
        status_events = [e for e in events if isinstance(e, JobStatusEvent)]
        assert len(status_events) >= 2

    def test_state_manager_isolation_with_tmp_project_dir(
        self, tmp_project_dir, event_collector
    ):
        """StateManager singleton is properly isolated by tmp_project_dir fixture."""
        from src.utils.state_manager import get_state_manager

        _events, _emit = event_collector
        sm = get_state_manager()

        # State should be empty initially
        assert sm.get_all_videos() == {}

        # Register a video
        sm.register_video(
            video_id="isolated_video",
            filename="isolated.mp4",
            video_path="/test/isolated.mp4",
        )

        # Video should be registered
        assert sm.get_video_state("isolated_video") is not None


# ============================================================================
# TEST CLASS: Error Handling Edge Cases
# ============================================================================


class TestErrorHandling:
    """Tests for error handling edge cases."""

    def test_missing_video_path_raises_file_not_found(
        self, job_runner, tmp_project_dir
    ):
        """_get_video_path raises FileNotFoundError when video path not registered."""
        runner, _events, sm = job_runner
        sm.get_video_path.return_value = None

        with pytest.raises(FileNotFoundError, match="Video path not registered"):
            runner._get_video_path("nonexistent_video")

    def test_transcription_without_transcript_path_raises_runtime_error(
        self, job_runner, tmp_project_dir
    ):
        """_step_generate_clips raises RuntimeError when no transcript_path exists."""
        runner, _events, sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        sm.get_video_state.return_value = {}  # No transcript_path

        with pytest.raises(RuntimeError, match="No transcript_path found"):
            runner._step_generate_clips(
                job_id="job1",
                video_id="vid1",
                settings={},
                run_output_dir=run_output_dir,
            )

    def test_export_without_clips_raises_runtime_error(
        self, job_runner, tmp_project_dir
    ):
        """_step_export_clips raises RuntimeError when no clips in state."""
        runner, _events, sm = job_runner
        run_output_dir = Path(tmp_project_dir) / "output" / ".cache" / "test"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        sm.get_video_state.return_value = {"clips": []}  # Empty clips

        with pytest.raises(RuntimeError, match="No clips in state"):
            runner._step_export_clips(
                job_id="job1",
                video_id="vid1",
                settings={},
                run_output_dir=run_output_dir,
            )
