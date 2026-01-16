"""
Tests for CleanupManager module.

Covers:
- CleanupManager initialization with custom directories
- get_video_artifacts() retrieval of video artifacts from state
- delete_video_artifacts() with selective and full cleanup
- dry_run mode (listing without deletion)
- _clean_cache_and_residuals() pattern matching for temp files
- delete_all_project_data() full cleanup behavior
- State synchronization after cleanup operations
- Preservation of final outputs when not targeted for deletion
"""

from pathlib import Path

import pytest

from src.cleanup_manager import CleanupManager


@pytest.fixture
def cleanup_test_dirs(tmp_project_dir: Path):
    """
    Create mock file structure for cleanup tests.

    Creates:
        - downloads/: Contains mock video files
        - temp/: Contains transcript and clips metadata files
        - output/: Contains exported clips directories
    """
    downloads_dir = tmp_project_dir / "downloads"
    temp_dir = tmp_project_dir / "temp"
    output_dir = tmp_project_dir / "output"

    downloads_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": tmp_project_dir,
        "downloads": downloads_dir,
        "temp": temp_dir,
        "output": output_dir,
    }


@pytest.fixture
def cleanup_manager(cleanup_test_dirs):
    """Create CleanupManager with test directories."""
    return CleanupManager(
        downloads_dir=str(cleanup_test_dirs["downloads"]),
        temp_dir=str(cleanup_test_dirs["temp"]),
        output_dir=str(cleanup_test_dirs["output"]),
    )


@pytest.fixture
def video_with_artifacts(cleanup_test_dirs, cleanup_manager):
    """
    Create a video entry in state with associated artifact files.

    Creates:
        - downloads/test_video.mp4 (mock video file)
        - temp/test_video_transcript.json (transcript file)
        - temp/test_video_clips.json (clips metadata file)
        - output/test_video_ABC123/clip_001.mp4 (exported clip)
    """
    video_key = "test_video_ABC123"
    downloads_dir = cleanup_test_dirs["downloads"]
    temp_dir = cleanup_test_dirs["temp"]
    output_dir = cleanup_test_dirs["output"]

    # Create mock files
    video_file = downloads_dir / "test_video.mp4"
    video_file.write_bytes(b"mock video content" * 100)

    transcript_file = temp_dir / "test_video_transcript.json"
    transcript_file.write_text('{"segments": []}', encoding="utf-8")

    clips_metadata_file = temp_dir / "test_video_clips.json"
    clips_metadata_file.write_text('{"clips": []}', encoding="utf-8")

    # Create output directory with clips
    output_video_dir = output_dir / video_key
    output_video_dir.mkdir(parents=True, exist_ok=True)
    clip_file = output_video_dir / "clip_001.mp4"
    clip_file.write_bytes(b"mock clip content" * 50)

    # Register video in state
    cleanup_manager.state_manager.register_video(
        video_id=video_key,
        filename="test_video.mp4",
        video_path=str(video_file),
    )
    cleanup_manager.state_manager.mark_transcribed(video_key, str(transcript_file))
    cleanup_manager.state_manager.mark_clips_generated(
        video_key,
        clips=[{"clip_id": 1}],
        clips_metadata_path=str(clips_metadata_file),
    )
    cleanup_manager.state_manager.mark_clips_exported(
        video_key,
        exported_paths=[str(clip_file)],
    )

    return {
        "video_key": video_key,
        "video_file": video_file,
        "transcript_file": transcript_file,
        "clips_metadata_file": clips_metadata_file,
        "output_video_dir": output_video_dir,
        "clip_file": clip_file,
    }


class TestCleanupManagerInitialization:
    """Tests for CleanupManager initialization."""

    def test_cleanup_manager_initialization(self, cleanup_test_dirs):
        """Verify custom directory paths are set correctly."""
        manager = CleanupManager(
            downloads_dir=str(cleanup_test_dirs["downloads"]),
            temp_dir=str(cleanup_test_dirs["temp"]),
            output_dir=str(cleanup_test_dirs["output"]),
        )

        assert manager.downloads_dir == cleanup_test_dirs["downloads"]
        assert manager.temp_dir == cleanup_test_dirs["temp"]
        assert manager.output_dir == cleanup_test_dirs["output"]

    def test_cleanup_manager_default_initialization(self, tmp_project_dir):
        """Verify default directories are set when not provided."""
        manager = CleanupManager()

        assert manager.downloads_dir == Path("downloads")
        assert manager.temp_dir == Path("temp")
        assert manager.output_dir == Path("output")


class TestGetVideoArtifacts:
    """Tests for get_video_artifacts() method."""

    def test_get_video_artifacts_returns_artifact_info(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify artifact metadata is retrieved from state."""
        video_key = video_with_artifacts["video_key"]
        artifacts = cleanup_manager.get_video_artifacts(video_key)

        assert "download" in artifacts
        assert "transcript" in artifacts
        assert "clips_metadata" in artifacts
        assert "output" in artifacts

        # Verify download artifact
        assert artifacts["download"]["exists"] is True
        assert artifacts["download"]["type"] == "video"
        assert artifacts["download"]["size"] > 0

        # Verify transcript artifact
        assert artifacts["transcript"]["exists"] is True
        assert artifacts["transcript"]["type"] == "json"

        # Verify clips_metadata artifact
        assert artifacts["clips_metadata"]["exists"] is True
        assert artifacts["clips_metadata"]["type"] == "json"

        # Verify output artifact
        assert artifacts["output"]["exists"] is True
        assert artifacts["output"]["type"] == "directory"
        assert artifacts["output"]["clip_count"] == 1

    def test_get_video_artifacts_nonexistent_video(self, cleanup_manager):
        """Verify empty dict returned for unknown video."""
        artifacts = cleanup_manager.get_video_artifacts("nonexistent_video")
        assert artifacts == {}

    def test_get_video_artifacts_includes_temp_files(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify temp files (orphaned *_temp.mp4) are detected."""
        video_key = video_with_artifacts["video_key"]
        output_dir = video_with_artifacts["output_video_dir"]

        # Create orphaned temp file
        temp_file = output_dir / "clip_001_temp.mp4"
        temp_file.write_bytes(b"temp content" * 100)

        artifacts = cleanup_manager.get_video_artifacts(video_key)

        assert "temp_files" in artifacts
        assert artifacts["temp_files"]["exists"] is True
        assert artifacts["temp_files"]["type"] == "temp_videos"
        assert artifacts["temp_files"]["file_count"] == 1


class TestDeleteVideoArtifacts:
    """Tests for delete_video_artifacts() method."""

    def test_delete_video_artifacts_removes_files(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify files are deleted for specified artifact types."""
        video_key = video_with_artifacts["video_key"]

        # Delete all artifacts
        results = cleanup_manager.delete_video_artifacts(video_key)

        assert all(results.values())
        assert not video_with_artifacts["video_file"].exists()
        assert not video_with_artifacts["transcript_file"].exists()
        assert not video_with_artifacts["clips_metadata_file"].exists()
        assert not video_with_artifacts["output_video_dir"].exists()

    def test_delete_video_artifacts_selective_cleanup(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify only specified artifact types are deleted."""
        video_key = video_with_artifacts["video_key"]

        # Delete only transcript and clips_metadata
        results = cleanup_manager.delete_video_artifacts(
            video_key, artifact_types=["transcript", "clips_metadata"]
        )

        assert results["transcript"] is True
        assert results["clips_metadata"] is True

        # Transcript and clips_metadata should be deleted
        assert not video_with_artifacts["transcript_file"].exists()
        assert not video_with_artifacts["clips_metadata_file"].exists()

        # Download and output should remain
        assert video_with_artifacts["video_file"].exists()
        assert video_with_artifacts["output_video_dir"].exists()

    def test_delete_video_artifacts_dry_run_no_deletion(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify files remain after dry_run=True."""
        video_key = video_with_artifacts["video_key"]

        results = cleanup_manager.delete_video_artifacts(video_key, dry_run=True)

        # All results should report success (simulated)
        assert all(results.values())

        # But files should still exist
        assert video_with_artifacts["video_file"].exists()
        assert video_with_artifacts["transcript_file"].exists()
        assert video_with_artifacts["clips_metadata_file"].exists()
        assert video_with_artifacts["output_video_dir"].exists()

    def test_delete_video_artifacts_updates_state(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify state is updated after cleanup."""
        video_key = video_with_artifacts["video_key"]

        # Verify initial state
        state_before = cleanup_manager.state_manager.get_video_state(video_key)
        assert state_before["transcribed"] is True
        assert state_before["clips_generated"] is True

        # Delete transcript and clips_metadata
        cleanup_manager.delete_video_artifacts(
            video_key, artifact_types=["transcript", "clips_metadata"]
        )

        # Verify state is updated
        state_after = cleanup_manager.state_manager.get_video_state(video_key)
        assert state_after["transcribed"] is False
        assert state_after["transcript_path"] is None
        assert state_after["clips_generated"] is False
        assert state_after["clips_metadata_path"] is None

    def test_delete_video_artifacts_removes_from_state_when_all_deleted(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify video is removed from state when all artifacts deleted."""
        video_key = video_with_artifacts["video_key"]

        # Delete all standard artifact types
        cleanup_manager.delete_video_artifacts(
            video_key,
            artifact_types=["download", "transcript", "clips_metadata", "output"],
        )

        # Verify video removed from state
        state = cleanup_manager.state_manager.get_video_state(video_key)
        assert state is None

    def test_delete_video_artifacts_nonexistent_artifact_succeeds(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify deletion succeeds when artifact doesn't exist."""
        video_key = video_with_artifacts["video_key"]

        # Delete transcript file manually
        video_with_artifacts["transcript_file"].unlink()

        # Try to delete again - should report success
        results = cleanup_manager.delete_video_artifacts(
            video_key, artifact_types=["transcript"]
        )

        assert results["transcript"] is True


class TestDeleteAllProjectData:
    """Tests for delete_all_project_data() method."""

    def test_delete_all_project_data_clears_directories(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify all directories are cleaned."""
        results = cleanup_manager.delete_all_project_data()

        assert results["downloads"] is True
        assert results["temp"] is True
        assert results["output"] is True
        assert results["cache"] is True
        assert results["state"] is True

        # Directories should exist but be empty (recreated)
        assert cleanup_manager.downloads_dir.exists()
        assert cleanup_manager.output_dir.exists()
        assert list(cleanup_manager.downloads_dir.iterdir()) == []
        # temp dir may have state files, check output is empty
        assert not list(cleanup_manager.output_dir.iterdir())

    def test_delete_all_project_data_dry_run(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify directories remain in dry_run mode."""
        results = cleanup_manager.delete_all_project_data(dry_run=True)

        # All results should report success (simulated)
        assert all(results.values())

        # Files should still exist
        assert video_with_artifacts["video_file"].exists()
        assert video_with_artifacts["output_video_dir"].exists()

    def test_delete_all_project_data_resets_state(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify project state is reset after cleanup."""
        video_key = video_with_artifacts["video_key"]

        # Verify video exists in state before
        assert cleanup_manager.state_manager.get_video_state(video_key) is not None

        cleanup_manager.delete_all_project_data()

        # Verify state is empty
        assert cleanup_manager.state_manager.get_all_videos() == {}


class TestCleanCacheAndResiduals:
    """Tests for _clean_cache_and_residuals() method."""

    def test_clean_cache_and_residuals_removes_temp_files(
        self, cleanup_manager, cleanup_test_dirs
    ):
        """Verify temp file patterns are matched and removed."""
        output_dir = cleanup_test_dirs["output"]

        # Create temp files with various patterns
        temp_patterns = [
            "temp_something.mp4",
            "temp_reframed_clip.mp4",
            "clip_001_temp.mp4",
        ]
        for pattern in temp_patterns:
            temp_file = output_dir / pattern
            temp_file.write_bytes(b"temp content")

        result = cleanup_manager._clean_cache_and_residuals()

        assert result is True
        # Verify temp files are removed
        for pattern in temp_patterns:
            assert not (output_dir / pattern).exists()

    def test_clean_cache_and_residuals_removes_lock_files(
        self, cleanup_manager, cleanup_test_dirs
    ):
        """Verify lock files are removed from temp directory."""
        temp_dir = cleanup_test_dirs["temp"]

        # Create lock files
        lock_file = temp_dir / "process.lock"
        lock_file.write_text("locked")

        result = cleanup_manager._clean_cache_and_residuals()

        assert result is True
        assert not lock_file.exists()

    def test_clean_cache_and_residuals_removes_orphaned_srts(
        self, cleanup_manager, cleanup_test_dirs
    ):
        """Verify orphaned SRT files (without matching MP4) are removed."""
        output_dir = cleanup_test_dirs["output"]

        # Create orphaned SRT (no matching MP4)
        orphaned_srt = output_dir / "orphaned_clip.srt"
        orphaned_srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello")

        # Create paired SRT (with matching MP4)
        paired_srt = output_dir / "paired_clip.srt"
        paired_srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nWorld")
        paired_mp4 = output_dir / "paired_clip.mp4"
        paired_mp4.write_bytes(b"video content")

        result = cleanup_manager._clean_cache_and_residuals()

        assert result is True
        # Orphaned SRT should be removed
        assert not orphaned_srt.exists()
        # Paired SRT should remain
        assert paired_srt.exists()
        assert paired_mp4.exists()


class TestPreservation:
    """Tests for preservation of non-targeted artifacts."""

    def test_preservation_of_non_targeted_artifacts(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify artifacts not in artifact_types list are preserved."""
        video_key = video_with_artifacts["video_key"]

        # Delete only download, preserve everything else
        results = cleanup_manager.delete_video_artifacts(
            video_key, artifact_types=["download"]
        )

        assert results["download"] is True

        # Download should be deleted
        assert not video_with_artifacts["video_file"].exists()

        # Other artifacts should remain
        assert video_with_artifacts["transcript_file"].exists()
        assert video_with_artifacts["clips_metadata_file"].exists()
        assert video_with_artifacts["output_video_dir"].exists()
        assert video_with_artifacts["clip_file"].exists()

    def test_preservation_with_dry_run_and_selective_types(
        self, cleanup_manager, video_with_artifacts
    ):
        """Verify complex preservation scenario with dry_run and selective types."""
        video_key = video_with_artifacts["video_key"]

        # Dry run on output only
        results = cleanup_manager.delete_video_artifacts(
            video_key, artifact_types=["output"], dry_run=True
        )

        assert results["output"] is True

        # All files should remain (dry run)
        assert video_with_artifacts["video_file"].exists()
        assert video_with_artifacts["transcript_file"].exists()
        assert video_with_artifacts["clips_metadata_file"].exists()
        assert video_with_artifacts["output_video_dir"].exists()
        assert video_with_artifacts["clip_file"].exists()

        # State should not be modified during dry run
        state = cleanup_manager.state_manager.get_video_state(video_key)
        assert state is not None
        assert state["clips_generated"] is True
