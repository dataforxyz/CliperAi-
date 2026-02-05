# -*- coding: utf-8 -*-
"""
Comprehensive tests for the DependencyManager module.

Tests cover DependencySpec, EnsureResult, DependencyProgress dataclasses,
ensure_all_required function behavior, and marker file functionality.
"""
import os
from dataclasses import FrozenInstanceError

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def isolated_dependency_manager(tmp_path, monkeypatch):
    """
    Fixture to isolate dependency manager state.

    Clears _ENSURED_IN_PROCESS set and redirects XDG_CACHE_HOME to tmp_path.
    """
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    from src.core import dependency_manager as dm

    dm._ENSURED_IN_PROCESS.clear()

    return dm


# ============================================================================
# TEST CLASSES
# ============================================================================


class TestDependencySpec:
    """Tests for DependencySpec dataclass."""

    def test_dataclass_creation(self, isolated_dependency_manager):
        """DependencySpec can be created with required fields."""
        dm = isolated_dependency_manager

        spec = dm.DependencySpec(
            key="test:dep",
            description="Test dependency",
            check=lambda: True,
            ensure=lambda: None,
        )

        assert spec.key == "test:dep"
        assert spec.description == "Test dependency"
        assert callable(spec.check)
        assert callable(spec.ensure)

    def test_frozen_immutability(self, isolated_dependency_manager):
        """DependencySpec is frozen and cannot be modified."""
        dm = isolated_dependency_manager

        spec = dm.DependencySpec(
            key="test:dep",
            description="Test dependency",
            check=lambda: True,
            ensure=lambda: None,
        )

        with pytest.raises(FrozenInstanceError):
            spec.key = "modified"


class TestEnsureResult:
    """Tests for EnsureResult dataclass."""

    def test_ok_returns_true_when_no_failures_and_not_canceled(self, isolated_dependency_manager):
        """ok property returns True when failed is empty and canceled is False."""
        dm = isolated_dependency_manager

        result = dm.EnsureResult(
            completed=["dep1", "dep2"],
            skipped=["dep3"],
            failed={},
            canceled=False,
        )

        assert result.ok is True

    def test_ok_returns_false_when_canceled(self, isolated_dependency_manager):
        """ok property returns False when canceled is True."""
        dm = isolated_dependency_manager

        result = dm.EnsureResult(
            completed=["dep1"],
            skipped=[],
            failed={},
            canceled=True,
        )

        assert result.ok is False

    def test_ok_returns_false_when_failed_non_empty(self, isolated_dependency_manager):
        """ok property returns False when failed dict is non-empty."""
        dm = isolated_dependency_manager

        result = dm.EnsureResult(
            completed=["dep1"],
            skipped=[],
            failed={"dep2": "Error message"},
            canceled=False,
        )

        assert result.ok is False

    def test_ok_returns_false_when_both_failed_and_canceled(self, isolated_dependency_manager):
        """ok property returns False when both failed and canceled."""
        dm = isolated_dependency_manager

        result = dm.EnsureResult(
            completed=[],
            skipped=[],
            failed={"dep1": "Error"},
            canceled=True,
        )

        assert result.ok is False


class TestDependencyProgress:
    """Tests for DependencyProgress dataclass."""

    def test_dataclass_creation(self, isolated_dependency_manager):
        """DependencyProgress can be created with required fields."""
        dm = isolated_dependency_manager

        progress = dm.DependencyProgress(
            key="test:dep",
            description="Test dependency",
            status=dm.DependencyStatus.CHECKING,
            index=1,
            total=3,
        )

        assert progress.key == "test:dep"
        assert progress.description == "Test dependency"
        assert progress.status == dm.DependencyStatus.CHECKING
        assert progress.index == 1
        assert progress.total == 3
        assert progress.message == ""  # default
        assert progress.attempt == 1   # default

    def test_default_values(self, isolated_dependency_manager):
        """DependencyProgress uses correct default values."""
        dm = isolated_dependency_manager

        progress = dm.DependencyProgress(
            key="test:dep",
            description="Test",
            status=dm.DependencyStatus.DONE,
            index=2,
            total=5,
        )

        assert progress.message == ""
        assert progress.attempt == 1

    def test_custom_message_and_attempt(self, isolated_dependency_manager):
        """DependencyProgress accepts custom message and attempt values."""
        dm = isolated_dependency_manager

        progress = dm.DependencyProgress(
            key="test:dep",
            description="Test",
            status=dm.DependencyStatus.ERROR,
            index=1,
            total=1,
            message="Download failed",
            attempt=3,
        )

        assert progress.message == "Download failed"
        assert progress.attempt == 3


class TestEnsureAllRequired:
    """Tests for ensure_all_required function."""

    def test_completes_all_specs(self, isolated_dependency_manager):
        """All specs are ensured and returned in completed list."""
        dm = isolated_dependency_manager

        ensure_calls = []

        specs = [
            dm.DependencySpec(
                key=f"dep{i}",
                description=f"Dependency {i}",
                check=lambda: False,  # Not already installed
                ensure=lambda i=i: ensure_calls.append(i),
            )
            for i in range(3)
        ]

        result = dm.ensure_all_required(specs)

        assert result.ok is True
        assert result.canceled is False
        assert set(result.completed) == {"dep0", "dep1", "dep2"}
        assert result.skipped == []
        assert result.failed == {}
        assert len(ensure_calls) == 3

    def test_skips_already_checked(self, isolated_dependency_manager):
        """Specs with check=True are added to skipped list."""
        dm = isolated_dependency_manager

        ensure_called = []

        spec = dm.DependencySpec(
            key="already_installed",
            description="Already installed dep",
            check=lambda: True,  # Already installed
            ensure=lambda: ensure_called.append(True),
        )

        result = dm.ensure_all_required([spec])

        assert result.ok is True
        assert "already_installed" in result.skipped
        assert "already_installed" not in result.completed
        assert ensure_called == []  # ensure should not be called

    def test_skips_already_ensured_in_process(self, isolated_dependency_manager):
        """Specs already in _ENSURED_IN_PROCESS are skipped immediately."""
        dm = isolated_dependency_manager

        # Pre-add to in-process set
        dm._ENSURED_IN_PROCESS.add("already_ensured")

        ensure_called = []
        check_called = []

        spec = dm.DependencySpec(
            key="already_ensured",
            description="Already ensured this run",
            check=lambda: (check_called.append(True), False)[1],
            ensure=lambda: ensure_called.append(True),
        )

        result = dm.ensure_all_required([spec])

        assert result.ok is True
        assert "already_ensured" in result.skipped
        assert check_called == []  # check should not be called
        assert ensure_called == []  # ensure should not be called

    def test_reports_progress(self, isolated_dependency_manager):
        """Reporter receives correct DependencyProgress events."""
        dm = isolated_dependency_manager

        events = []

        class MockReporter:
            def report(self, event):
                events.append(event)

            def is_cancelled(self):
                return False

        spec = dm.DependencySpec(
            key="test_dep",
            description="Test dependency",
            check=lambda: False,
            ensure=lambda: None,
        )

        result = dm.ensure_all_required([spec], reporter=MockReporter())

        assert result.ok is True

        # Should have CHECKING, DOWNLOADING, DONE events
        statuses = [e.status for e in events]
        assert dm.DependencyStatus.CHECKING in statuses
        assert dm.DependencyStatus.DOWNLOADING in statuses
        assert dm.DependencyStatus.DONE in statuses

        # All events should have correct key
        assert all(e.key == "test_dep" for e in events)

    def test_handles_ensure_error(self, isolated_dependency_manager):
        """Errors populate failed dict with error message."""
        dm = isolated_dependency_manager

        def failing_ensure():
            raise RuntimeError("Download failed")

        spec = dm.DependencySpec(
            key="failing_dep",
            description="Failing dependency",
            check=lambda: False,
            ensure=failing_ensure,
        )

        result = dm.ensure_all_required([spec], max_attempts=1)

        assert result.ok is False
        assert "failing_dep" in result.failed
        assert "Download failed" in result.failed["failing_dep"]

    def test_retries_on_error_with_retry_decision(self, isolated_dependency_manager):
        """on_error callback returning RETRY causes retry."""
        dm = isolated_dependency_manager

        call_count = {"ensure": 0}

        def flaky_ensure():
            call_count["ensure"] += 1
            if call_count["ensure"] < 2:
                raise RuntimeError("Temporary failure")

        def on_error(progress, exc):
            return dm.EnsureDecision.RETRY

        spec = dm.DependencySpec(
            key="flaky_dep",
            description="Flaky dependency",
            check=lambda: False,
            ensure=flaky_ensure,
        )

        result = dm.ensure_all_required([spec], on_error=on_error, max_attempts=3)

        assert result.ok is True
        assert "flaky_dep" in result.completed
        assert call_count["ensure"] == 2

    def test_skips_on_error_with_skip_decision(self, isolated_dependency_manager):
        """on_error returning SKIP adds to failed and continues to next spec."""
        dm = isolated_dependency_manager

        def on_error(progress, exc):
            return dm.EnsureDecision.SKIP

        specs = [
            dm.DependencySpec(
                key="failing_dep",
                description="Failing dependency",
                check=lambda: False,
                ensure=lambda: (_ for _ in ()).throw(RuntimeError("Fail")),
            ),
            dm.DependencySpec(
                key="good_dep",
                description="Good dependency",
                check=lambda: False,
                ensure=lambda: None,
            ),
        ]

        result = dm.ensure_all_required(specs, on_error=on_error, max_attempts=3)

        assert result.canceled is False
        assert "failing_dep" in result.failed
        assert "good_dep" in result.completed

    def test_cancels_on_error_with_cancel_decision(self, isolated_dependency_manager):
        """on_error returning CANCEL sets canceled=True and stops processing."""
        dm = isolated_dependency_manager

        second_spec_called = []

        def on_error(progress, exc):
            return dm.EnsureDecision.CANCEL

        specs = [
            dm.DependencySpec(
                key="failing_dep",
                description="Failing dependency",
                check=lambda: False,
                ensure=lambda: (_ for _ in ()).throw(RuntimeError("Fail")),
            ),
            dm.DependencySpec(
                key="second_dep",
                description="Second dependency",
                check=lambda: False,
                ensure=lambda: second_spec_called.append(True),
            ),
        ]

        result = dm.ensure_all_required(specs, on_error=on_error, max_attempts=3)

        assert result.canceled is True
        assert result.ok is False
        assert second_spec_called == []  # Second spec should not be processed

    def test_respects_max_attempts(self, isolated_dependency_manager):
        """Ensure is called at most max_attempts times on repeated failures."""
        dm = isolated_dependency_manager

        call_count = {"ensure": 0}

        def always_fail():
            call_count["ensure"] += 1
            raise RuntimeError("Always fails")

        def always_retry(progress, exc):
            return dm.EnsureDecision.RETRY

        spec = dm.DependencySpec(
            key="always_failing",
            description="Always failing",
            check=lambda: False,
            ensure=always_fail,
        )

        result = dm.ensure_all_required([spec], on_error=always_retry, max_attempts=3)

        assert result.ok is False
        assert "always_failing" in result.failed
        assert call_count["ensure"] == 3  # Exactly max_attempts

    def test_cancels_via_reporter(self, isolated_dependency_manager):
        """reporter.is_cancelled() returning True stops processing."""
        dm = isolated_dependency_manager

        specs_processed = []

        class CancellingReporter:
            def __init__(self):
                self.report_count = 0

            def report(self, event):
                self.report_count += 1

            def is_cancelled(self):
                # Cancel after first spec starts processing
                return self.report_count > 0

        specs = [
            dm.DependencySpec(
                key=f"dep{i}",
                description=f"Dep {i}",
                check=lambda: False,
                ensure=lambda i=i: specs_processed.append(i),
            )
            for i in range(3)
        ]

        result = dm.ensure_all_required(specs, reporter=CancellingReporter())

        assert result.canceled is True
        assert result.ok is False
        # Not all specs should be processed
        assert len(specs_processed) < 3


class TestMarkerFileFunctions:
    """Tests for marker file functions."""

    def test_marker_file_functions(self, isolated_dependency_manager):
        """mark_dependency_installed creates marker and is_dependency_marked_installed returns True."""
        dm = isolated_dependency_manager

        key = "test:marker_dep"

        # Initially not marked
        assert dm.is_dependency_marked_installed(key) is False

        # Mark as installed
        dm.mark_dependency_installed(key)

        # Now should be marked
        assert dm.is_dependency_marked_installed(key) is True

    def test_marker_sanitizes_key(self, isolated_dependency_manager):
        """Marker file path sanitizes special characters in key."""
        dm = isolated_dependency_manager

        key = "special:key/with\\weird<chars>"

        dm.mark_dependency_installed(key)

        assert dm.is_dependency_marked_installed(key) is True


# ============================================================================
# EXISTING TESTS (preserved)
# ============================================================================


def test_dependency_markers_make_ensure_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    from src.core import dependency_manager as dm

    dm._ENSURED_IN_PROCESS.clear()

    key = "test_dep:example"
    marker_path = dm._dependency_marker_path(key)
    if os.path.exists(marker_path):
        os.remove(marker_path)

    calls = {"ensure": 0}

    def ensure():
        calls["ensure"] += 1

    spec = dm.DependencySpec(
        key=key,
        description="Test dependency",
        check=lambda key=key: dm.is_dependency_marked_installed(key),
        ensure=ensure,
    )

    result1 = dm.ensure_all_required([spec])
    assert result1.ok
    assert calls["ensure"] == 1

    dm._ENSURED_IN_PROCESS.clear()
    result2 = dm.ensure_all_required([spec])
    assert result2.ok
    assert calls["ensure"] == 1
