# -*- coding: utf-8 -*-
"""
Comprehensive pytest tests for src/core/events.py.

Tests cover:
- LogLevel enum values and string behavior
- CoreEvent initialization with required/optional parameters and auto-generated ts
- LogEvent initialization and inheritance from CoreEvent
- ProgressEvent initialization with current, total, label defaults
- StateEvent initialization with updates dict default
- JobStatusEvent initialization with state and error defaults
- Frozen dataclass immutability for all event classes
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from src.core.events import (
    CoreEvent,
    JobStatusEvent,
    LogEvent,
    LogLevel,
    ProgressEvent,
    StateEvent,
)
from src.core.models import JobState


# ============================================================================
# TEST CLASS: LogLevel Enum
# ============================================================================


class TestLogLevel:
    """Tests for LogLevel enum values and behavior."""

    def test_loglevel_debug_value(self):
        """LogLevel.DEBUG has value 'debug'."""
        assert LogLevel.DEBUG.value == "debug"

    def test_loglevel_info_value(self):
        """LogLevel.INFO has value 'info'."""
        assert LogLevel.INFO.value == "info"

    def test_loglevel_warning_value(self):
        """LogLevel.WARNING has value 'warning'."""
        assert LogLevel.WARNING.value == "warning"

    def test_loglevel_error_value(self):
        """LogLevel.ERROR has value 'error'."""
        assert LogLevel.ERROR.value == "error"

    def test_loglevel_is_str_enum(self):
        """LogLevel inherits from str, so values can be used as strings."""
        assert isinstance(LogLevel.INFO, str)
        assert LogLevel.INFO == "info"

    def test_loglevel_all_values(self):
        """LogLevel has exactly 4 members."""
        assert len(LogLevel) == 4
        members = {m.value for m in LogLevel}
        assert members == {"debug", "info", "warning", "error"}

    def test_loglevel_from_value(self):
        """LogLevel can be instantiated from string value."""
        assert LogLevel("debug") == LogLevel.DEBUG
        assert LogLevel("info") == LogLevel.INFO
        assert LogLevel("warning") == LogLevel.WARNING
        assert LogLevel("error") == LogLevel.ERROR

    def test_loglevel_invalid_value_raises(self):
        """LogLevel raises ValueError for invalid value."""
        with pytest.raises(ValueError, match="'invalid' is not a valid LogLevel"):
            LogLevel("invalid")


# ============================================================================
# TEST CLASS: CoreEvent
# ============================================================================


class TestCoreEvent:
    """Tests for CoreEvent dataclass initialization and attributes."""

    def test_core_event_required_job_id(self):
        """CoreEvent requires job_id parameter."""
        event = CoreEvent(job_id="job-123")
        assert event.job_id == "job-123"

    def test_core_event_optional_video_id_default_none(self):
        """CoreEvent video_id defaults to None."""
        event = CoreEvent(job_id="job-123")
        assert event.video_id is None

    def test_core_event_video_id_can_be_set(self):
        """CoreEvent video_id can be explicitly set."""
        event = CoreEvent(job_id="job-123", video_id="vid-456")
        assert event.video_id == "vid-456"

    def test_core_event_ts_auto_generated(self):
        """CoreEvent ts is auto-generated as ISO timestamp."""
        event = CoreEvent(job_id="job-123")
        # ISO format pattern: YYYY-MM-DDTHH:MM:SS
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, event.ts)

    def test_core_event_ts_can_be_overridden(self):
        """CoreEvent ts can be explicitly set."""
        event = CoreEvent(job_id="job-123", ts="2024-01-01T12:00:00")
        assert event.ts == "2024-01-01T12:00:00"

    def test_core_event_is_frozen(self):
        """CoreEvent is a frozen dataclass (immutable)."""
        event = CoreEvent(job_id="job-123")
        with pytest.raises(FrozenInstanceError):
            event.job_id = "new-id"

    def test_core_event_video_id_is_frozen(self):
        """CoreEvent video_id cannot be modified."""
        event = CoreEvent(job_id="job-123", video_id="vid-456")
        with pytest.raises(FrozenInstanceError):
            event.video_id = "new-vid"

    def test_core_event_ts_is_frozen(self):
        """CoreEvent ts cannot be modified."""
        event = CoreEvent(job_id="job-123")
        with pytest.raises(FrozenInstanceError):
            event.ts = "2025-01-01T00:00:00"


# ============================================================================
# TEST CLASS: LogEvent
# ============================================================================


class TestLogEvent:
    """Tests for LogEvent dataclass initialization and inheritance."""

    def test_log_event_inherits_from_core_event(self):
        """LogEvent inherits from CoreEvent."""
        event = LogEvent(job_id="job-123")
        assert isinstance(event, CoreEvent)

    def test_log_event_requires_job_id(self):
        """LogEvent requires job_id from parent."""
        event = LogEvent(job_id="job-123")
        assert event.job_id == "job-123"

    def test_log_event_level_defaults_to_info(self):
        """LogEvent level defaults to LogLevel.INFO."""
        event = LogEvent(job_id="job-123")
        assert event.level == LogLevel.INFO

    def test_log_event_level_can_be_set(self):
        """LogEvent level can be explicitly set."""
        event = LogEvent(job_id="job-123", level=LogLevel.ERROR)
        assert event.level == LogLevel.ERROR

    def test_log_event_message_defaults_to_empty_string(self):
        """LogEvent message defaults to empty string."""
        event = LogEvent(job_id="job-123")
        assert event.message == ""

    def test_log_event_message_can_be_set(self):
        """LogEvent message can be explicitly set."""
        event = LogEvent(job_id="job-123", message="Test message")
        assert event.message == "Test message"

    def test_log_event_inherits_video_id(self):
        """LogEvent inherits video_id from CoreEvent."""
        event = LogEvent(job_id="job-123", video_id="vid-456")
        assert event.video_id == "vid-456"

    def test_log_event_inherits_ts(self):
        """LogEvent inherits auto-generated ts from CoreEvent."""
        event = LogEvent(job_id="job-123")
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, event.ts)

    def test_log_event_is_frozen(self):
        """LogEvent is a frozen dataclass (immutable)."""
        event = LogEvent(job_id="job-123", message="Test")
        with pytest.raises(FrozenInstanceError):
            event.message = "Modified"

    def test_log_event_level_is_frozen(self):
        """LogEvent level cannot be modified."""
        event = LogEvent(job_id="job-123", level=LogLevel.INFO)
        with pytest.raises(FrozenInstanceError):
            event.level = LogLevel.ERROR

    def test_log_event_all_log_levels(self):
        """LogEvent can be created with all LogLevel values."""
        for level in LogLevel:
            event = LogEvent(job_id="job-123", level=level)
            assert event.level == level


# ============================================================================
# TEST CLASS: ProgressEvent
# ============================================================================


class TestProgressEvent:
    """Tests for ProgressEvent dataclass initialization."""

    def test_progress_event_inherits_from_core_event(self):
        """ProgressEvent inherits from CoreEvent."""
        event = ProgressEvent(job_id="job-123")
        assert isinstance(event, CoreEvent)

    def test_progress_event_requires_job_id(self):
        """ProgressEvent requires job_id from parent."""
        event = ProgressEvent(job_id="job-123")
        assert event.job_id == "job-123"

    def test_progress_event_current_defaults_to_zero(self):
        """ProgressEvent current defaults to 0."""
        event = ProgressEvent(job_id="job-123")
        assert event.current == 0

    def test_progress_event_current_can_be_set(self):
        """ProgressEvent current can be explicitly set."""
        event = ProgressEvent(job_id="job-123", current=5)
        assert event.current == 5

    def test_progress_event_total_defaults_to_zero(self):
        """ProgressEvent total defaults to 0."""
        event = ProgressEvent(job_id="job-123")
        assert event.total == 0

    def test_progress_event_total_can_be_set(self):
        """ProgressEvent total can be explicitly set."""
        event = ProgressEvent(job_id="job-123", total=10)
        assert event.total == 10

    def test_progress_event_label_defaults_to_empty_string(self):
        """ProgressEvent label defaults to empty string."""
        event = ProgressEvent(job_id="job-123")
        assert event.label == ""

    def test_progress_event_label_can_be_set(self):
        """ProgressEvent label can be explicitly set."""
        event = ProgressEvent(job_id="job-123", label="Processing video")
        assert event.label == "Processing video"

    def test_progress_event_inherits_video_id(self):
        """ProgressEvent inherits video_id from CoreEvent."""
        event = ProgressEvent(job_id="job-123", video_id="vid-456")
        assert event.video_id == "vid-456"

    def test_progress_event_is_frozen(self):
        """ProgressEvent is a frozen dataclass (immutable)."""
        event = ProgressEvent(job_id="job-123", current=5)
        with pytest.raises(FrozenInstanceError):
            event.current = 10

    def test_progress_event_total_is_frozen(self):
        """ProgressEvent total cannot be modified."""
        event = ProgressEvent(job_id="job-123", total=10)
        with pytest.raises(FrozenInstanceError):
            event.total = 20

    def test_progress_event_label_is_frozen(self):
        """ProgressEvent label cannot be modified."""
        event = ProgressEvent(job_id="job-123", label="Test")
        with pytest.raises(FrozenInstanceError):
            event.label = "Modified"


# ============================================================================
# TEST CLASS: StateEvent
# ============================================================================


class TestStateEvent:
    """Tests for StateEvent dataclass initialization."""

    def test_state_event_inherits_from_core_event(self):
        """StateEvent inherits from CoreEvent."""
        event = StateEvent(job_id="job-123")
        assert isinstance(event, CoreEvent)

    def test_state_event_requires_job_id(self):
        """StateEvent requires job_id from parent."""
        event = StateEvent(job_id="job-123")
        assert event.job_id == "job-123"

    def test_state_event_updates_defaults_to_empty_dict(self):
        """StateEvent updates defaults to empty dict."""
        event = StateEvent(job_id="job-123")
        assert event.updates == {}

    def test_state_event_updates_can_be_set(self):
        """StateEvent updates can be explicitly set."""
        updates = {"transcript_path": "/path/to/transcript.json", "status": "complete"}
        event = StateEvent(job_id="job-123", updates=updates)
        assert event.updates == updates

    def test_state_event_inherits_video_id(self):
        """StateEvent inherits video_id from CoreEvent."""
        event = StateEvent(job_id="job-123", video_id="vid-456")
        assert event.video_id == "vid-456"

    def test_state_event_is_frozen(self):
        """StateEvent is a frozen dataclass (immutable)."""
        event = StateEvent(job_id="job-123")
        with pytest.raises(FrozenInstanceError):
            event.updates = {"new": "value"}

    def test_state_event_updates_dict_default_is_independent(self):
        """Each StateEvent gets its own independent updates dict."""
        event1 = StateEvent(job_id="job-1")
        event2 = StateEvent(job_id="job-2")
        # Mutating one should not affect the other (default_factory creates new dict)
        assert event1.updates is not event2.updates


# ============================================================================
# TEST CLASS: JobStatusEvent
# ============================================================================


class TestJobStatusEvent:
    """Tests for JobStatusEvent dataclass initialization."""

    def test_job_status_event_inherits_from_core_event(self):
        """JobStatusEvent inherits from CoreEvent."""
        event = JobStatusEvent(job_id="job-123")
        assert isinstance(event, CoreEvent)

    def test_job_status_event_requires_job_id(self):
        """JobStatusEvent requires job_id from parent."""
        event = JobStatusEvent(job_id="job-123")
        assert event.job_id == "job-123"

    def test_job_status_event_state_defaults_to_pending(self):
        """JobStatusEvent state defaults to JobState.PENDING."""
        event = JobStatusEvent(job_id="job-123")
        assert event.state == JobState.PENDING

    def test_job_status_event_state_can_be_set(self):
        """JobStatusEvent state can be explicitly set."""
        event = JobStatusEvent(job_id="job-123", state=JobState.RUNNING)
        assert event.state == JobState.RUNNING

    def test_job_status_event_all_job_states(self):
        """JobStatusEvent can be created with all JobState values."""
        for state in JobState:
            event = JobStatusEvent(job_id="job-123", state=state)
            assert event.state == state

    def test_job_status_event_error_defaults_to_none(self):
        """JobStatusEvent error defaults to None."""
        event = JobStatusEvent(job_id="job-123")
        assert event.error is None

    def test_job_status_event_error_can_be_set(self):
        """JobStatusEvent error can be explicitly set."""
        event = JobStatusEvent(job_id="job-123", error="Something went wrong")
        assert event.error == "Something went wrong"

    def test_job_status_event_failed_with_error(self):
        """JobStatusEvent can represent a failed state with error message."""
        event = JobStatusEvent(
            job_id="job-123",
            state=JobState.FAILED,
            error="Transcription failed: out of memory",
        )
        assert event.state == JobState.FAILED
        assert event.error == "Transcription failed: out of memory"

    def test_job_status_event_inherits_video_id(self):
        """JobStatusEvent inherits video_id from CoreEvent."""
        event = JobStatusEvent(job_id="job-123", video_id="vid-456")
        assert event.video_id == "vid-456"

    def test_job_status_event_is_frozen(self):
        """JobStatusEvent is a frozen dataclass (immutable)."""
        event = JobStatusEvent(job_id="job-123")
        with pytest.raises(FrozenInstanceError):
            event.state = JobState.RUNNING

    def test_job_status_event_error_is_frozen(self):
        """JobStatusEvent error cannot be modified."""
        event = JobStatusEvent(job_id="job-123", error="Test error")
        with pytest.raises(FrozenInstanceError):
            event.error = "New error"


# ============================================================================
# TEST CLASS: Event Equality and Hashing
# ============================================================================


class TestEventEquality:
    """Tests for event equality and hashability."""

    def test_core_event_equality_with_same_values(self):
        """CoreEvents with same values are equal."""
        ts = "2024-01-01T12:00:00"
        event1 = CoreEvent(job_id="job-123", video_id="vid-456", ts=ts)
        event2 = CoreEvent(job_id="job-123", video_id="vid-456", ts=ts)
        assert event1 == event2

    def test_core_event_inequality_with_different_job_id(self):
        """CoreEvents with different job_ids are not equal."""
        ts = "2024-01-01T12:00:00"
        event1 = CoreEvent(job_id="job-123", ts=ts)
        event2 = CoreEvent(job_id="job-456", ts=ts)
        assert event1 != event2

    def test_log_event_equality_with_same_values(self):
        """LogEvents with same values are equal."""
        ts = "2024-01-01T12:00:00"
        event1 = LogEvent(job_id="job-123", level=LogLevel.INFO, message="Test", ts=ts)
        event2 = LogEvent(job_id="job-123", level=LogLevel.INFO, message="Test", ts=ts)
        assert event1 == event2

    def test_frozen_events_are_hashable(self):
        """Frozen events can be used in sets and as dict keys."""
        ts = "2024-01-01T12:00:00"
        event = CoreEvent(job_id="job-123", ts=ts)
        # Should not raise
        event_set = {event}
        event_dict = {event: "value"}
        assert event in event_set
        assert event_dict[event] == "value"
