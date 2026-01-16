"""
Tests for video_registry.py and video_namer.py utilities.

Tests cover:
- Video file extension validation (is_supported_video_file)
- Video discovery and state registration (discover_downloads_and_register)
- Local path collection and validation (collect_local_video_paths)
- Video registration with content_type/preset (register_local_videos)
- Filename slugification (_slugify)
- Filler word filtering and word extraction (_extract_first_words)
- Video name generation with multiple methods (generate_video_name)
"""

import json
from pathlib import Path

import pytest

from src.utils.video_namer import (
    FILLER_WORDS,
    _extract_first_words,
    _slugify,
    generate_video_name,
)
from src.utils.video_registry import (
    SUPPORTED_VIDEO_EXTENSIONS,
    collect_local_video_paths,
    discover_downloads_and_register,
    is_supported_video_file,
    register_local_videos,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_video_files(tmp_project_dir: Path):
    """
    Create mock video files in downloads/ directory for discovery tests.

    Creates files with various extensions (supported and unsupported).
    """
    downloads_dir = tmp_project_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    created_files = {}

    # Supported video files
    for ext in [".mp4", ".mkv", ".webm", ".mov", ".m4v"]:
        video_file = downloads_dir / f"test_video{ext}"
        video_file.write_bytes(b"fake video content")
        created_files[ext] = video_file

    # Unsupported files (should be ignored)
    unsupported = downloads_dir / "document.txt"
    unsupported.write_text("not a video")
    created_files[".txt"] = unsupported

    image = downloads_dir / "image.jpg"
    image.write_bytes(b"fake image")
    created_files[".jpg"] = image

    return created_files


@pytest.fixture
def transcript_file(tmp_project_dir: Path, sample_transcript):
    """Create a transcript JSON file for video_namer tests."""
    transcript_path = tmp_project_dir / "temp" / "test_transcript.json"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")
    return transcript_path


# ============================================================================
# VIDEO REGISTRY TESTS
# ============================================================================


class TestIsSupportedVideoFile:
    """Tests for is_supported_video_file()"""

    def test_supported_extensions_accepted(self, tmp_path: Path):
        """Verify all supported extensions are accepted."""
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            video_file = tmp_path / f"video{ext}"
            video_file.write_bytes(b"content")
            assert (
                is_supported_video_file(video_file) is True
            ), f"{ext} should be supported"

    def test_uppercase_extensions_accepted(self, tmp_path: Path):
        """Verify uppercase extensions are also accepted."""
        video_file = tmp_path / "video.MP4"
        video_file.write_bytes(b"content")
        assert is_supported_video_file(video_file) is True

    def test_unsupported_extensions_rejected(self, tmp_path: Path):
        """Verify unsupported extensions are rejected."""
        unsupported = [".txt", ".jpg", ".png", ".pdf", ".avi", ".flv"]
        for ext in unsupported:
            test_file = tmp_path / f"file{ext}"
            test_file.write_bytes(b"content")
            assert (
                is_supported_video_file(test_file) is False
            ), f"{ext} should not be supported"

    def test_directory_rejected(self, tmp_path: Path):
        """Verify directories are rejected even with video-like names."""
        video_dir = tmp_path / "video.mp4"
        video_dir.mkdir()
        assert is_supported_video_file(video_dir) is False

    def test_nonexistent_file_rejected(self, tmp_path: Path):
        """Verify nonexistent files are rejected."""
        nonexistent = tmp_path / "nonexistent.mp4"
        assert is_supported_video_file(nonexistent) is False


class TestDiscoverDownloadsAndRegister:
    """Tests for discover_downloads_and_register()"""

    def test_discovers_video_files(self, tmp_project_dir: Path, mock_video_files):
        """Verify video files in downloads/ are discovered."""
        from src.utils.state_manager import get_state_manager

        state_manager = get_state_manager()
        discovered = discover_downloads_and_register(state_manager)

        # Should find all supported video files
        discovered_names = {p.name for p in discovered}
        assert "test_video.mp4" in discovered_names
        assert "test_video.mkv" in discovered_names
        assert "test_video.webm" in discovered_names

        # Should NOT include unsupported files
        assert "document.txt" not in discovered_names
        assert "image.jpg" not in discovered_names

    def test_registers_videos_in_state(self, tmp_project_dir: Path, mock_video_files):
        """Verify discovered videos are registered in state."""
        from src.utils.state_manager import get_state_manager

        state_manager = get_state_manager()
        discover_downloads_and_register(state_manager)

        all_videos = state_manager.get_all_videos()
        assert len(all_videos) >= 1

        # Check that at least one video was registered with correct data
        video_state = state_manager.get_video_state("test_video")
        assert video_state is not None
        assert video_state.get("filename") in [
            f"test_video{ext}" for ext in SUPPORTED_VIDEO_EXTENSIONS
        ]

    def test_creates_downloads_dir_if_missing(self, tmp_project_dir: Path):
        """Verify downloads/ directory is created if it doesn't exist."""
        from src.utils.state_manager import get_state_manager

        downloads_dir = tmp_project_dir / "downloads"
        if downloads_dir.exists():
            import shutil

            shutil.rmtree(downloads_dir)

        state_manager = get_state_manager()
        discover_downloads_and_register(state_manager)

        assert downloads_dir.exists()

    def test_returns_sorted_list(self, tmp_project_dir: Path):
        """Verify returned list is sorted by filename."""
        from src.utils.state_manager import get_state_manager

        downloads_dir = tmp_project_dir / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        # Create files with various names
        (downloads_dir / "zebra.mp4").write_bytes(b"content")
        (downloads_dir / "alpha.mp4").write_bytes(b"content")
        (downloads_dir / "Beta.mp4").write_bytes(b"content")

        state_manager = get_state_manager()
        discovered = discover_downloads_and_register(state_manager)

        names = [p.name.lower() for p in discovered]
        assert names == sorted(names)


class TestCollectLocalVideoPaths:
    """Tests for collect_local_video_paths()"""

    def test_single_file_path(self, tmp_project_dir: Path):
        """Verify single file path is collected correctly."""
        video_file = tmp_project_dir / "single_video.mp4"
        video_file.write_bytes(b"content")

        paths, errors = collect_local_video_paths(str(video_file))

        assert len(paths) == 1
        assert paths[0].name == "single_video.mp4"
        assert len(errors) == 0

    def test_folder_path_collects_videos(self, tmp_project_dir: Path, mock_video_files):
        """Verify folder path collects all supported videos inside."""
        downloads_dir = tmp_project_dir / "downloads"

        paths, _errors = collect_local_video_paths(str(downloads_dir))

        assert len(paths) >= 3  # At least mp4, mkv, webm
        # Verify all are video files
        for p in paths:
            assert p.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS

    def test_comma_separated_paths(self, tmp_project_dir: Path):
        """Verify comma-separated paths are all collected."""
        video1 = tmp_project_dir / "video1.mp4"
        video2 = tmp_project_dir / "video2.mkv"
        video1.write_bytes(b"content")
        video2.write_bytes(b"content")

        input_str = f"{video1}, {video2}"
        paths, errors = collect_local_video_paths(input_str)

        assert len(paths) == 2
        assert len(errors) == 0

    def test_nonexistent_path_returns_error(self, tmp_project_dir: Path):
        """Verify nonexistent paths return errors."""
        paths, errors = collect_local_video_paths("/nonexistent/path/video.mp4")

        assert len(paths) == 0
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_unsupported_file_returns_error(self, tmp_project_dir: Path):
        """Verify unsupported file types return errors."""
        txt_file = tmp_project_dir / "document.txt"
        txt_file.write_text("not a video")

        paths, errors = collect_local_video_paths(str(txt_file))

        assert len(paths) == 0
        assert len(errors) == 1
        assert "unsupported" in errors[0].lower()

    def test_empty_folder_returns_error(self, tmp_project_dir: Path):
        """Verify empty folder returns an error."""
        empty_dir = tmp_project_dir / "empty_folder"
        empty_dir.mkdir()

        paths, errors = collect_local_video_paths(str(empty_dir))

        assert len(paths) == 0
        assert len(errors) == 1
        assert "no supported videos" in errors[0].lower()

    def test_empty_input_returns_error(self):
        """Verify empty input returns an error."""
        paths, errors = collect_local_video_paths("")

        assert len(paths) == 0
        assert len(errors) == 1
        assert "no input" in errors[0].lower()

    def test_deduplicates_paths(self, tmp_project_dir: Path):
        """Verify duplicate paths are deduplicated."""
        video = tmp_project_dir / "video.mp4"
        video.write_bytes(b"content")

        input_str = f"{video}, {video}, {video}"
        paths, _errors = collect_local_video_paths(input_str)

        assert len(paths) == 1

    def test_handles_quoted_paths(self, tmp_project_dir: Path):
        """Verify quoted paths are handled correctly."""
        video = tmp_project_dir / "video.mp4"
        video.write_bytes(b"content")

        paths, _errors = collect_local_video_paths(f'"{video}"')

        assert len(paths) == 1


class TestRegisterLocalVideos:
    """Tests for register_local_videos()"""

    def test_registers_videos_returns_ids(self, tmp_project_dir: Path):
        """Verify videos are registered and IDs are returned."""
        from src.utils.state_manager import get_state_manager

        video1 = tmp_project_dir / "video1.mp4"
        video2 = tmp_project_dir / "video2.mkv"
        video1.write_bytes(b"content")
        video2.write_bytes(b"content")

        state_manager = get_state_manager()
        video_ids = register_local_videos(state_manager, [video1, video2])

        assert len(video_ids) == 2
        assert "video1" in video_ids
        assert "video2" in video_ids

    def test_registers_with_content_type(self, tmp_project_dir: Path):
        """Verify content_type is stored in state."""
        from src.utils.state_manager import get_state_manager

        video = tmp_project_dir / "tutorial_video.mp4"
        video.write_bytes(b"content")

        state_manager = get_state_manager()
        register_local_videos(state_manager, [video], content_type="podcast")

        video_state = state_manager.get_video_state("tutorial_video")
        assert video_state is not None
        assert video_state.get("content_type") == "podcast"

    def test_registers_with_preset(self, tmp_project_dir: Path):
        """Verify preset is stored in state."""
        from src.utils.state_manager import get_state_manager

        video = tmp_project_dir / "preset_video.mp4"
        video.write_bytes(b"content")

        preset = {"aspect_ratio": "9:16", "quality": "high"}
        state_manager = get_state_manager()
        register_local_videos(state_manager, [video], preset=preset)

        video_state = state_manager.get_video_state("preset_video")
        assert video_state is not None
        assert video_state.get("preset") == preset

    def test_skips_unsupported_files(self, tmp_project_dir: Path):
        """Verify unsupported files are skipped silently."""
        from src.utils.state_manager import get_state_manager

        video = tmp_project_dir / "video.mp4"
        txt = tmp_project_dir / "document.txt"
        video.write_bytes(b"content")
        txt.write_text("not a video")

        state_manager = get_state_manager()
        video_ids = register_local_videos(state_manager, [video, txt])

        assert len(video_ids) == 1
        assert "video" in video_ids


# ============================================================================
# VIDEO NAMER TESTS
# ============================================================================


class TestSlugify:
    """Tests for _slugify()"""

    def test_basic_slugification(self):
        """Verify basic text is slugified correctly."""
        result = _slugify("Hello World")
        assert result == "hello_world"

    def test_special_characters_removed(self):
        """Verify special characters are removed."""
        result = _slugify("Video: Episode #1 (2024)")
        assert result == "video_episode_1_2024"

    def test_multiple_spaces_collapsed(self):
        """Verify multiple spaces become single underscore."""
        result = _slugify("hello    world")
        assert result == "hello_world"

    def test_max_chars_truncation(self):
        """Verify text is truncated at max_chars."""
        long_text = "this is a very long title that should be truncated"
        result = _slugify(long_text, max_chars=20)
        assert len(result) <= 20

    def test_truncation_respects_word_boundaries(self):
        """Verify truncation doesn't cut words in half."""
        text = "hello beautiful world today"
        result = _slugify(text, max_chars=15)
        # Should not cut in middle of a word
        assert not result.endswith("_") and not result.endswith("-")
        assert "_" not in result[-3:] or result.endswith("world") or len(result) <= 15

    def test_empty_input_returns_default(self):
        """Verify empty input returns default name."""
        assert _slugify("") == "unnamed_video"
        assert _slugify("   ") == "unnamed_video"

    def test_only_special_chars_returns_default(self):
        """Verify input with only special chars returns default."""
        assert _slugify("!@#$%^&*()") == "unnamed_video"

    def test_leading_trailing_underscores_stripped(self):
        """Verify leading/trailing underscores are stripped."""
        result = _slugify("  _hello_world_  ")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_unicode_characters(self):
        """Verify unicode characters are handled."""
        result = _slugify("Café résumé naïve")
        assert "caf" in result
        assert "_" in result


class TestExtractFirstWords:
    """Tests for _extract_first_words()"""

    def test_extracts_from_word_level_transcript(self, sample_transcript):
        """Verify extraction from word-level transcript data."""
        result = _extract_first_words(sample_transcript, word_count=5)
        words = result.split()

        assert len(words) == 5
        # "Hello" should be extracted (not a filler)
        assert "hello" in words

    def test_filters_filler_words(self):
        """Verify filler words are filtered out."""
        transcript = {
            "segments": [
                {
                    "words": [
                        {"word": "Um"},
                        {"word": "so"},
                        {"word": "like"},
                        {"word": "important"},
                        {"word": "topic"},
                        {"word": "here"},
                    ]
                }
            ]
        }
        result = _extract_first_words(transcript, word_count=3)
        words = result.lower().split()

        # Filler words should be filtered
        assert "um" not in words
        assert "so" not in words
        assert "like" not in words
        # Meaningful words should be present
        assert "important" in words
        assert "topic" in words

    def test_fallback_to_segment_text(self):
        """Verify fallback to segment text when no word-level data."""
        transcript = {"segments": [{"text": "Welcome to the amazing show today"}]}
        result = _extract_first_words(transcript, word_count=3)
        words = result.split()

        assert len(words) == 3
        # "the" is a filler, should be filtered
        assert "the" not in words

    def test_empty_transcript_returns_empty(self):
        """Verify empty transcript returns empty string."""
        assert _extract_first_words({}, word_count=5) == ""
        assert _extract_first_words({"segments": []}, word_count=5) == ""

    def test_filters_single_char_words(self):
        """Verify single character words are filtered."""
        transcript = {"segments": [{"text": "I a b interesting topic today"}]}
        result = _extract_first_words(transcript, word_count=3)
        words = result.split()

        # Single char "a", "b" should be filtered
        assert "a" not in words
        assert "b" not in words

    def test_respects_word_count_limit(self):
        """Verify word count limit is respected."""
        transcript = {
            "segments": [{"text": "one two three four five six seven eight nine ten"}]
        }
        result = _extract_first_words(transcript, word_count=3)
        words = result.split()

        assert len(words) == 3

    def test_filler_words_constant_contains_expected(self):
        """Verify FILLER_WORDS contains expected common fillers."""
        assert "um" in FILLER_WORDS
        assert "uh" in FILLER_WORDS
        assert "like" in FILLER_WORDS
        assert "so" in FILLER_WORDS
        # Spanish fillers
        assert "pues" in FILLER_WORDS
        assert "bueno" in FILLER_WORDS


class TestGenerateVideoName:
    """Tests for generate_video_name()"""

    def test_filename_method(self):
        """Verify filename method uses original filename."""
        result = generate_video_name(
            original_filename="My Cool Video.mp4",
            method="filename",
        )
        assert result == "my_cool_video"

    def test_filename_method_with_special_chars(self):
        """Verify filename method handles special characters."""
        result = generate_video_name(
            original_filename="Video: Episode #1 (2024).mp4",
            method="filename",
        )
        assert "video" in result
        assert "episode" in result

    def test_first_words_method(self, transcript_file):
        """Verify first_words method extracts from transcript."""
        result = generate_video_name(
            transcript_path=str(transcript_file),
            original_filename="original.mp4",
            method="first_words",
            word_count=3,
        )
        # Should contain words from transcript, not filename
        assert "original" not in result
        assert len(result) > 0

    def test_first_words_fallback_to_filename(self, tmp_project_dir: Path):
        """Verify first_words falls back to filename when transcript missing."""
        result = generate_video_name(
            transcript_path=None,
            original_filename="fallback_video.mp4",
            method="first_words",
        )
        assert result == "fallback_video"

    def test_first_words_fallback_nonexistent_transcript(self, tmp_project_dir: Path):
        """Verify fallback when transcript file doesn't exist."""
        result = generate_video_name(
            transcript_path="/nonexistent/transcript.json",
            original_filename="fallback_video.mp4",
            method="first_words",
        )
        assert result == "fallback_video"

    def test_max_chars_respected(self, transcript_file):
        """Verify max_chars limit is respected."""
        result = generate_video_name(
            transcript_path=str(transcript_file),
            original_filename="original.mp4",
            method="first_words",
            max_chars=15,
        )
        assert len(result) <= 15

    def test_empty_transcript_falls_back(self, tmp_project_dir: Path):
        """Verify empty transcript falls back to filename."""
        empty_transcript = tmp_project_dir / "temp" / "empty.json"
        empty_transcript.parent.mkdir(parents=True, exist_ok=True)
        empty_transcript.write_text('{"segments": []}', encoding="utf-8")

        result = generate_video_name(
            transcript_path=str(empty_transcript),
            original_filename="fallback.mp4",
            method="first_words",
        )
        assert result == "fallback"

    def test_invalid_json_falls_back(self, tmp_project_dir: Path):
        """Verify invalid JSON transcript falls back to filename."""
        invalid_transcript = tmp_project_dir / "temp" / "invalid.json"
        invalid_transcript.parent.mkdir(parents=True, exist_ok=True)
        invalid_transcript.write_text("not valid json", encoding="utf-8")

        result = generate_video_name(
            transcript_path=str(invalid_transcript),
            original_filename="fallback.mp4",
            method="first_words",
        )
        assert result == "fallback"
