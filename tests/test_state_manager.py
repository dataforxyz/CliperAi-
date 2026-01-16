"""
Comprehensive pytest tests for StateManager.

Tests cover:
- Singleton pattern enforcement
- Video CRUD operations
- Job queue operations
- JSON file persistence
- Settings management
- Edge cases (corruption, missing files, validation errors)
"""

import json
from pathlib import Path

import src.utils.state_manager as state_manager_module
from src.utils.state_manager import get_state_manager


class TestSingletonPattern:
    """Tests for the singleton pattern via get_state_manager()."""

    def test_get_state_manager_returns_same_instance(self, tmp_project_dir):
        """get_state_manager() should return the same instance on multiple calls."""
        manager1 = get_state_manager()
        manager2 = get_state_manager()

        assert manager1 is manager2

    def test_singleton_reset_via_module_global(self, tmp_project_dir):
        """Resetting _state_manager_instance to None should create a new instance."""
        manager1 = get_state_manager()

        # Reset the singleton
        state_manager_module._state_manager_instance = None

        manager2 = get_state_manager()

        assert manager1 is not manager2

    def test_singleton_uses_init_kwargs(self, tmp_project_dir):
        """The singleton should use _state_manager_init_kwargs for initialization."""
        # tmp_project_dir already sets up init kwargs with app_root and settings_file
        manager = get_state_manager()

        assert manager.app_root == tmp_project_dir


class TestVideoRegistration:
    """Tests for video registration and state management."""

    def test_register_new_video(self, tmp_project_dir):
        """Registering a new video should create state entry."""
        manager = get_state_manager()

        manager.register_video(
            video_id="test_video_001",
            filename="test.mp4",
            video_path="/path/to/test.mp4",
            content_type="podcast",
        )

        state = manager.get_video_state("test_video_001")
        assert state is not None
        assert state["filename"] == "test.mp4"
        assert state["content_type"] == "podcast"
        assert state["downloaded"] is True
        assert state["transcribed"] is False

    def test_register_video_persists_to_disk(self, tmp_project_dir):
        """Registered video should be persisted to JSON file."""
        manager = get_state_manager()

        manager.register_video(
            video_id="persist_test",
            filename="persist.mp4",
        )

        # Read the state file directly
        state_file = tmp_project_dir / "temp" / "project_state.json"
        with open(state_file, encoding="utf-8") as f:
            persisted_state = json.load(f)

        assert "persist_test" in persisted_state
        assert persisted_state["persist_test"]["filename"] == "persist.mp4"

    def test_register_existing_video_updates_metadata(self, tmp_project_dir):
        """Re-registering a video should update metadata without resetting progress."""
        manager = get_state_manager()

        # First registration
        manager.register_video(
            video_id="update_test",
            filename="original.mp4",
            content_type="tutorial",
        )

        # Mark as transcribed
        manager.mark_transcribed("update_test", "/path/to/transcript.json")

        # Re-register with updated metadata
        manager.register_video(
            video_id="update_test",
            filename="updated.mp4",
            content_type="podcast",
        )

        state = manager.get_video_state("update_test")
        assert state["filename"] == "updated.mp4"
        assert state["content_type"] == "podcast"
        # Progress should be preserved
        assert state["transcribed"] is True

    def test_register_video_with_preset(self, tmp_project_dir):
        """Registering a video with a preset should store the preset."""
        manager = get_state_manager()

        preset = {"target_duration": 60, "aspect_ratio": "9:16"}
        manager.register_video(
            video_id="preset_test",
            filename="preset.mp4",
            preset=preset,
        )

        state = manager.get_video_state("preset_test")
        assert state["preset"] == preset


class TestVideoStateRetrieval:
    """Tests for video state retrieval methods."""

    def test_get_video_state_returns_none_for_unknown(self, tmp_project_dir):
        """get_video_state should return None for unregistered videos."""
        manager = get_state_manager()

        assert manager.get_video_state("nonexistent") is None

    def test_get_all_videos_returns_all_registered(self, tmp_project_dir):
        """get_all_videos should return all registered videos."""
        manager = get_state_manager()

        manager.register_video("vid1", "video1.mp4")
        manager.register_video("vid2", "video2.mp4")
        manager.register_video("vid3", "video3.mp4")

        all_videos = manager.get_all_videos()

        assert len(all_videos) == 3
        assert "vid1" in all_videos
        assert "vid2" in all_videos
        assert "vid3" in all_videos

    def test_is_transcribed_false_by_default(self, tmp_project_dir):
        """is_transcribed should return False for new videos."""
        manager = get_state_manager()

        manager.register_video("new_video", "new.mp4")

        assert manager.is_transcribed("new_video") is False

    def test_is_transcribed_true_after_mark(self, tmp_project_dir):
        """is_transcribed should return True after marking."""
        manager = get_state_manager()

        manager.register_video("transcribed_video", "transcribed.mp4")
        manager.mark_transcribed("transcribed_video", "/path/to/transcript.json")

        assert manager.is_transcribed("transcribed_video") is True

    def test_is_transcribed_false_for_unknown_video(self, tmp_project_dir):
        """is_transcribed should return False for unknown videos."""
        manager = get_state_manager()

        assert manager.is_transcribed("unknown_video") is False

    def test_get_next_step_transcribe(self, tmp_project_dir):
        """get_next_step should return 'transcribe' for new videos."""
        manager = get_state_manager()

        manager.register_video("step_test", "step.mp4")

        assert manager.get_next_step("step_test") == "transcribe"

    def test_get_next_step_generate_clips(self, tmp_project_dir):
        """get_next_step should return 'generate_clips' after transcription."""
        manager = get_state_manager()

        manager.register_video("step_test2", "step2.mp4")
        manager.mark_transcribed("step_test2", "/path/to/transcript.json")

        assert manager.get_next_step("step_test2") == "generate_clips"

    def test_get_next_step_export(self, tmp_project_dir):
        """get_next_step should return 'export' after clips generated."""
        manager = get_state_manager()

        manager.register_video("step_test3", "step3.mp4")
        manager.mark_transcribed("step_test3", "/path/to/transcript.json")
        manager.mark_clips_generated("step_test3", [{"clip_id": 1}])

        assert manager.get_next_step("step_test3") == "export"

    def test_get_next_step_done(self, tmp_project_dir):
        """get_next_step should return 'done' after export."""
        manager = get_state_manager()

        manager.register_video("step_test4", "step4.mp4")
        manager.mark_transcribed("step_test4", "/path/to/transcript.json")
        manager.mark_clips_generated("step_test4", [{"clip_id": 1}])
        manager.mark_clips_exported("step_test4", ["/path/to/clip1.mp4"])

        assert manager.get_next_step("step_test4") == "done"

    def test_get_next_step_unknown_for_unregistered(self, tmp_project_dir):
        """get_next_step should return 'unknown' for unregistered videos."""
        manager = get_state_manager()

        assert manager.get_next_step("unregistered") == "unknown"


class TestVideoMarkMethods:
    """Tests for video marking methods."""

    def test_mark_transcribed(self, tmp_project_dir):
        """mark_transcribed should update transcription state."""
        manager = get_state_manager()

        manager.register_video("mark_test", "mark.mp4")
        manager.mark_transcribed("mark_test", "/path/to/transcript.json")

        state = manager.get_video_state("mark_test")
        assert state["transcribed"] is True
        assert state["transcription_path"] == str(Path("/path/to/transcript.json"))
        assert state["transcript_path"] == str(Path("/path/to/transcript.json"))

    def test_mark_clips_generated(self, tmp_project_dir):
        """mark_clips_generated should store clips metadata."""
        manager = get_state_manager()

        manager.register_video("clips_test", "clips.mp4")
        clips = [
            {"clip_id": 1, "start": 0, "end": 60},
            {"clip_id": 2, "start": 60, "end": 120},
        ]
        manager.mark_clips_generated("clips_test", clips, "/path/to/clips.json")

        state = manager.get_video_state("clips_test")
        assert state["clips_generated"] is True
        assert state["clips"] == clips
        assert state["clips_metadata_path"] == str(Path("/path/to/clips.json"))

    def test_mark_clips_exported(self, tmp_project_dir):
        """mark_clips_exported should store exported paths."""
        manager = get_state_manager()

        manager.register_video("export_test", "export.mp4")
        exported_paths = ["/path/to/clip1.mp4", "/path/to/clip2.mp4"]
        manager.mark_clips_exported("export_test", exported_paths, aspect_ratio="9:16")

        state = manager.get_video_state("export_test")
        assert state["clips_exported"] is True
        assert len(state["exported_clips"]) == 2
        assert state["export_aspect_ratio"] == "9:16"

    def test_mark_shorts_exported(self, tmp_project_dir):
        """mark_shorts_exported should store shorts export info."""
        manager = get_state_manager()

        manager.register_video("shorts_test", "shorts.mp4")
        manager.mark_shorts_exported(
            "shorts_test",
            "/path/to/short.mp4",
            srt_path="/path/to/short.srt",
            input_path="/path/to/input.mp4",
        )

        state = manager.get_video_state("shorts_test")
        assert state["shorts_exported"] is True
        assert state["shorts_export_path"] == "/path/to/short.mp4"
        assert state["shorts_srt_path"] == "/path/to/short.srt"
        assert state["shorts_input_path"] == "/path/to/input.mp4"

    def test_is_shorts_exported_true_after_mark(self, tmp_project_dir):
        """is_shorts_exported should return True after marking."""
        manager = get_state_manager()

        manager.register_video("shorts_check", "shorts.mp4")
        assert manager.is_shorts_exported("shorts_check") is False

        manager.mark_shorts_exported("shorts_check", "/path/to/short.mp4")
        assert manager.is_shorts_exported("shorts_check") is True

    def test_mark_on_unregistered_video_does_nothing(self, tmp_project_dir):
        """Marking methods should silently skip unregistered videos."""
        manager = get_state_manager()

        # These should not raise
        manager.mark_transcribed("unknown", "/path/to/transcript.json")
        manager.mark_clips_generated("unknown", [])
        manager.mark_clips_exported("unknown", [])
        manager.mark_shorts_exported("unknown", "/path/to/short.mp4")

        assert manager.get_video_state("unknown") is None


class TestClearVideoState:
    """Tests for clear_video_state method."""

    def test_clear_video_state_removes_video(self, tmp_project_dir):
        """clear_video_state should remove the video from state."""
        manager = get_state_manager()

        manager.register_video("clear_test", "clear.mp4")
        assert manager.get_video_state("clear_test") is not None

        manager.clear_video_state("clear_test")
        assert manager.get_video_state("clear_test") is None

    def test_clear_video_state_persists_deletion(self, tmp_project_dir):
        """Cleared video should be removed from persisted state."""
        manager = get_state_manager()

        manager.register_video("persist_clear", "persist.mp4")
        manager.clear_video_state("persist_clear")

        # Read state file directly
        state_file = tmp_project_dir / "temp" / "project_state.json"
        with open(state_file, encoding="utf-8") as f:
            persisted_state = json.load(f)

        assert "persist_clear" not in persisted_state

    def test_clear_unknown_video_does_nothing(self, tmp_project_dir):
        """Clearing unknown video should not raise."""
        manager = get_state_manager()

        # Should not raise
        manager.clear_video_state("nonexistent")


class TestAutoGeneratedName:
    """Tests for auto-generated name feature."""

    def test_set_auto_generated_name(self, tmp_project_dir):
        """set_auto_generated_name should store the name."""
        manager = get_state_manager()

        manager.register_video("name_test", "name.mp4")
        manager.set_auto_generated_name("name_test", "AI Tutorial Episode 1")

        state = manager.get_video_state("name_test")
        assert state["auto_generated_name"] == "AI Tutorial Episode 1"

    def test_get_auto_generated_name(self, tmp_project_dir):
        """get_auto_generated_name should retrieve the stored name."""
        manager = get_state_manager()

        manager.register_video("get_name_test", "get_name.mp4")
        manager.set_auto_generated_name("get_name_test", "Machine Learning Basics")

        assert (
            manager.get_auto_generated_name("get_name_test")
            == "Machine Learning Basics"
        )

    def test_get_auto_generated_name_none_by_default(self, tmp_project_dir):
        """get_auto_generated_name should return None if not set."""
        manager = get_state_manager()

        manager.register_video("no_name_test", "no_name.mp4")

        assert manager.get_auto_generated_name("no_name_test") is None

    def test_get_auto_generated_name_unknown_video(self, tmp_project_dir):
        """get_auto_generated_name should return None for unknown videos."""
        manager = get_state_manager()

        assert manager.get_auto_generated_name("unknown") is None


class TestJobQueueOperations:
    """Tests for job queue operations."""

    def test_enqueue_job(self, tmp_project_dir):
        """enqueue_job should add a job to the queue."""
        manager = get_state_manager()

        job_spec = {"video_ids": ["vid1"], "steps": ["transcribe"]}
        job_id = manager.enqueue_job(job_spec)

        assert job_id is not None
        assert len(job_id) == 12  # UUID hex[:12]

    def test_enqueue_job_with_existing_id(self, tmp_project_dir):
        """enqueue_job should use provided job_id if present."""
        manager = get_state_manager()

        job_spec = {"job_id": "custom-job-id", "video_ids": ["vid1"]}
        job_id = manager.enqueue_job(job_spec)

        assert job_id == "custom-job-id"

    def test_enqueue_job_persists(self, tmp_project_dir):
        """Enqueued job should be persisted to jobs_state.json."""
        manager = get_state_manager()

        job_spec = {"job_id": "persist-job", "video_ids": ["vid1"]}
        manager.enqueue_job(job_spec)

        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        with open(jobs_file, encoding="utf-8") as f:
            jobs_state = json.load(f)

        assert "persist-job" in jobs_state["jobs"]
        assert "persist-job" in jobs_state["queue"]

    def test_get_job(self, tmp_project_dir):
        """get_job should return the full job entry."""
        manager = get_state_manager()

        job_spec = {"job_id": "get-job-test", "video_ids": ["vid1"]}
        manager.enqueue_job(job_spec, initial_status={"state": "running"})

        job = manager.get_job("get-job-test")
        assert job is not None
        assert job["spec"]["video_ids"] == ["vid1"]
        assert job["status"]["state"] == "running"

    def test_get_job_returns_none_for_unknown(self, tmp_project_dir):
        """get_job should return None for unknown job_id."""
        manager = get_state_manager()

        assert manager.get_job("unknown-job") is None

    def test_get_job_spec(self, tmp_project_dir):
        """get_job_spec should return only the spec."""
        manager = get_state_manager()

        job_spec = {"job_id": "spec-test", "video_ids": ["vid1"], "custom_key": "value"}
        manager.enqueue_job(job_spec)

        spec = manager.get_job_spec("spec-test")
        assert spec["video_ids"] == ["vid1"]
        assert spec["custom_key"] == "value"

    def test_get_job_status(self, tmp_project_dir):
        """get_job_status should return only the status."""
        manager = get_state_manager()

        job_spec = {"job_id": "status-test", "video_ids": ["vid1"]}
        manager.enqueue_job(
            job_spec, initial_status={"state": "pending", "progress": 0}
        )

        status = manager.get_job_status("status-test")
        assert status["state"] == "pending"
        assert status["progress"] == 0

    def test_list_jobs(self, tmp_project_dir):
        """list_jobs should return all jobs."""
        manager = get_state_manager()

        manager.enqueue_job({"job_id": "job1", "video_ids": ["v1"]})
        manager.enqueue_job({"job_id": "job2", "video_ids": ["v2"]})

        jobs = manager.list_jobs()
        assert len(jobs) == 2
        assert "job1" in jobs
        assert "job2" in jobs


class TestJobMutations:
    """Tests for job mutation operations."""

    def test_update_job_status(self, tmp_project_dir):
        """update_job_status should merge updates into existing status."""
        manager = get_state_manager()

        manager.enqueue_job(
            {"job_id": "update-test", "video_ids": ["v1"]},
            initial_status={"state": "pending", "progress": 0},
        )

        manager.update_job_status("update-test", {"state": "running", "progress": 50})

        status = manager.get_job_status("update-test")
        assert status["state"] == "running"
        assert status["progress"] == 50

    def test_update_job_status_persists(self, tmp_project_dir):
        """Status updates should be persisted."""
        manager = get_state_manager()

        manager.enqueue_job({"job_id": "persist-update", "video_ids": ["v1"]})
        manager.update_job_status("persist-update", {"state": "completed"})

        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        with open(jobs_file, encoding="utf-8") as f:
            jobs_state = json.load(f)

        assert jobs_state["jobs"]["persist-update"]["status"]["state"] == "completed"

    def test_update_job_status_unknown_job(self, tmp_project_dir):
        """update_job_status should silently skip unknown jobs."""
        manager = get_state_manager()

        # Should not raise
        manager.update_job_status("unknown-job", {"state": "running"})

    def test_dequeue_next_job_id(self, tmp_project_dir):
        """dequeue_next_job_id should return and remove the first job from queue."""
        manager = get_state_manager()

        manager.enqueue_job({"job_id": "first", "video_ids": ["v1"]})
        manager.enqueue_job({"job_id": "second", "video_ids": ["v2"]})

        job_id = manager.dequeue_next_job_id()
        assert job_id == "first"

        # Job should still exist but not be in queue
        assert manager.get_job("first") is not None

        # Next dequeue should return second
        job_id = manager.dequeue_next_job_id()
        assert job_id == "second"

    def test_dequeue_next_job_id_empty_queue(self, tmp_project_dir):
        """dequeue_next_job_id should return None for empty queue."""
        manager = get_state_manager()

        assert manager.dequeue_next_job_id() is None

    def test_remove_job(self, tmp_project_dir):
        """remove_job should delete job from both jobs dict and queue."""
        manager = get_state_manager()

        manager.enqueue_job({"job_id": "remove-test", "video_ids": ["v1"]})
        assert manager.get_job("remove-test") is not None

        manager.remove_job("remove-test")

        assert manager.get_job("remove-test") is None

        # Verify not in queue either
        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        with open(jobs_file, encoding="utf-8") as f:
            jobs_state = json.load(f)
        assert "remove-test" not in jobs_state["queue"]


class TestSettingsManagement:
    """Tests for settings management."""

    def test_get_setting_with_default(self, tmp_project_dir):
        """get_setting should return schema default for undefined keys."""
        manager = get_state_manager()

        # This setting should have a schema-defined default
        value = manager.get_setting("subtitle_bold")
        assert isinstance(value, bool)

    def test_get_setting_custom_default(self, tmp_project_dir):
        """get_setting should use provided default for unknown keys."""
        manager = get_state_manager()

        value = manager.get_setting("unknown_key", default="custom_default")
        assert value == "custom_default"

    def test_set_setting(self, tmp_project_dir):
        """set_setting should update and persist the value."""
        manager = get_state_manager()

        manager.set_setting("subtitle_bold", True)

        assert manager.get_setting("subtitle_bold") is True

        # Verify persistence
        settings_file = tmp_project_dir / "config" / "app_settings.json"
        with open(settings_file, encoding="utf-8") as f:
            settings = json.load(f)
        assert settings["subtitle_bold"] is True

    def test_set_setting_validates_known_keys(self, tmp_project_dir):
        """set_setting should validate values for known settings."""
        manager = get_state_manager()

        # min_clip_duration should be normalized to positive int
        manager.set_setting("min_clip_duration", 45)
        value = manager.get_setting("min_clip_duration")
        assert value == 45

    def test_set_setting_allows_unknown_keys(self, tmp_project_dir):
        """set_setting should allow arbitrary unknown keys."""
        manager = get_state_manager()

        manager.set_setting("custom_unknown_key", {"nested": "value"})
        assert manager.get_setting("custom_unknown_key") == {"nested": "value"}

    def test_load_settings_returns_copy(self, tmp_project_dir):
        """load_settings should return a copy of settings dict."""
        manager = get_state_manager()

        settings1 = manager.load_settings()
        settings2 = manager.load_settings()

        assert settings1 is not settings2
        assert settings1 == settings2


class TestWizardFlow:
    """Tests for first run wizard tracking."""

    def test_is_first_run_false_when_wizard_completed(self, tmp_project_dir):
        """is_first_run should return False when wizard is completed."""
        # tmp_project_dir fixture sets _wizard_completed: true
        manager = get_state_manager()

        assert manager.is_first_run() is False

    def test_is_first_run_true_initially(self, tmp_project_dir):
        """is_first_run should return True before wizard completion."""
        # Reset settings to simulate first run
        manager = get_state_manager()
        manager.settings["_wizard_completed"] = False
        manager._save_settings()

        # Create a fresh manager
        state_manager_module._state_manager_instance = None
        settings_file = tmp_project_dir / "config" / "app_settings.json"
        settings_file.write_text(json.dumps({}), encoding="utf-8")

        manager = get_state_manager()
        assert manager.is_first_run() is True

    def test_mark_wizard_completed(self, tmp_project_dir):
        """mark_wizard_completed should set the flag and persist."""
        manager = get_state_manager()

        # Simulate first run
        manager.settings["_wizard_completed"] = False

        manager.mark_wizard_completed()

        assert manager.is_first_run() is False

        # Verify persistence
        settings_file = tmp_project_dir / "config" / "app_settings.json"
        with open(settings_file, encoding="utf-8") as f:
            settings = json.load(f)
        assert settings["_wizard_completed"] is True


class TestJSONPersistence:
    """Tests for JSON file load/save operations."""

    def test_load_state_creates_empty_dict_for_missing_file(self, tmp_project_dir):
        """_load_state should return empty dict if file doesn't exist."""
        manager = get_state_manager()

        # Remove state file
        state_file = tmp_project_dir / "temp" / "project_state.json"
        state_file.unlink()

        loaded = manager._load_state()
        assert loaded == {}

    def test_load_jobs_state_creates_defaults_for_missing_file(self, tmp_project_dir):
        """_load_jobs_state should return default structure if file doesn't exist."""
        manager = get_state_manager()

        # Remove jobs file
        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        jobs_file.unlink()

        loaded = manager._load_jobs_state()
        assert loaded == {"jobs": {}, "queue": []}

    def test_save_state_creates_file(self, tmp_project_dir):
        """_save_state should create the state file."""
        manager = get_state_manager()

        # Remove state file
        state_file = tmp_project_dir / "temp" / "project_state.json"
        state_file.unlink()

        manager.state = {"test_video": {"filename": "test.mp4"}}
        manager._save_state()

        assert state_file.exists()
        with open(state_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved == {"test_video": {"filename": "test.mp4"}}

    def test_state_survives_manager_recreation(self, tmp_project_dir):
        """State should persist across StateManager instances."""
        manager = get_state_manager()

        manager.register_video("survive_test", "survive.mp4")
        manager.mark_transcribed("survive_test", "/path/to/transcript.json")

        # Reset singleton
        state_manager_module._state_manager_instance = None

        # Create new manager
        new_manager = get_state_manager()

        state = new_manager.get_video_state("survive_test")
        assert state is not None
        assert state["transcribed"] is True


class TestEdgeCasesCorruption:
    """Tests for edge cases: file corruption, missing files, validation errors."""

    def test_corrupted_project_state_returns_empty(self, tmp_project_dir):
        """Corrupted project_state.json should result in empty state."""
        # Write corrupted JSON
        state_file = tmp_project_dir / "temp" / "project_state.json"
        state_file.write_text("{ invalid json }", encoding="utf-8")

        # Reset singleton to force reload
        state_manager_module._state_manager_instance = None

        manager = get_state_manager()
        assert manager.state == {}

    def test_corrupted_jobs_state_returns_default(self, tmp_project_dir):
        """Corrupted jobs_state.json should result in default structure."""
        # Write corrupted JSON
        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        jobs_file.write_text("not valid json at all", encoding="utf-8")

        # Reset singleton to force reload
        state_manager_module._state_manager_instance = None

        manager = get_state_manager()
        assert manager.jobs_state == {"jobs": {}, "queue": []}

    def test_corrupted_settings_returns_empty(self, tmp_project_dir):
        """Corrupted app_settings.json should result in validated defaults."""
        # Write corrupted JSON
        settings_file = tmp_project_dir / "config" / "app_settings.json"
        settings_file.write_text("corrupted { data", encoding="utf-8")

        # Reset singleton to force reload
        state_manager_module._state_manager_instance = None

        manager = get_state_manager()
        # Settings should be validated defaults, not empty
        assert isinstance(manager.settings, dict)

    def test_missing_temp_directory_created(self, tmp_project_dir):
        """Missing temp directory should be created."""
        import shutil

        temp_dir = tmp_project_dir / "temp"
        shutil.rmtree(temp_dir)
        assert not temp_dir.exists()

        # Reset singleton
        state_manager_module._state_manager_instance = None

        get_state_manager()
        assert temp_dir.exists()

    def test_non_dict_jobs_state_normalized(self, tmp_project_dir):
        """Non-dict jobs_state.json content should be normalized."""
        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        jobs_file.write_text('"just a string"', encoding="utf-8")

        state_manager_module._state_manager_instance = None

        manager = get_state_manager()
        assert manager.jobs_state == {"jobs": {}, "queue": []}

    def test_jobs_state_missing_keys_filled(self, tmp_project_dir):
        """Jobs state with missing keys should have defaults filled."""
        jobs_file = tmp_project_dir / "temp" / "jobs_state.json"
        jobs_file.write_text('{"jobs": {"j1": {}}}', encoding="utf-8")

        state_manager_module._state_manager_instance = None

        manager = get_state_manager()
        # Should have both 'jobs' and 'queue' keys
        assert "jobs" in manager.jobs_state
        assert "queue" in manager.jobs_state
        assert manager.jobs_state["queue"] == []

    def test_invalid_setting_reset_to_default(self, tmp_project_dir):
        """Invalid setting values should be reset to defaults during load."""
        # Write settings with invalid value (negative font size)
        settings_file = tmp_project_dir / "config" / "app_settings.json"
        settings_file.write_text(
            json.dumps({"subtitle_font_size": -100, "_wizard_completed": True}),
            encoding="utf-8",
        )

        state_manager_module._state_manager_instance = None

        manager = get_state_manager()
        # Font size should be reset to a valid default
        font_size = manager.get_setting("subtitle_font_size")
        assert font_size > 0


class TestVideoPath:
    """Tests for video path handling."""

    def test_get_video_path(self, tmp_project_dir):
        """get_video_path should return the stored path."""
        manager = get_state_manager()

        manager.register_video("path_test", "path.mp4", video_path="/videos/path.mp4")

        assert manager.get_video_path("path_test") == str(Path("/videos/path.mp4"))

    def test_get_video_path_none_for_unknown(self, tmp_project_dir):
        """get_video_path should return None for unknown videos."""
        manager = get_state_manager()

        assert manager.get_video_path("unknown") is None

    def test_normalize_path_handles_none(self, tmp_project_dir):
        """_normalize_path should return None for None input."""
        manager = get_state_manager()

        assert manager._normalize_path(None) is None

    def test_normalize_path_converts_to_string(self, tmp_project_dir):
        """_normalize_path should convert Path to string."""
        manager = get_state_manager()

        result = manager._normalize_path("/some/path/video.mp4")
        assert isinstance(result, str)
