# -*- coding: utf-8 -*-
"""
Tests for the Transcriber class (src/transcriber.py).

Covers initialization, transcription with mocked whisperx, JSON output validation,
and error handling for missing/corrupt files.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_whisper_model():
    """Mock whisper model returned by load_whisper_model."""
    model = MagicMock()
    model.transcribe.return_value = {
        "segments": [
            {"start": 0.0, "end": 3.5, "text": "Hello and welcome to the show"},
            {"start": 4.0, "end": 8.0, "text": "Today we will discuss AI topics"},
        ],
        "language": "en",
    }
    return model


@pytest.fixture
def mock_align_model():
    """Mock align model and metadata returned by load_align_model."""
    model_a = MagicMock()
    metadata = MagicMock()
    return model_a, metadata


@pytest.fixture
def mock_whisperx():
    """Mock the whisperx module with load_audio and align functions."""
    mock = MagicMock()
    mock.load_audio.return_value = MagicMock()  # Audio array mock
    mock.align.return_value = {
        "segments": [
            {
                "start": 0.0,
                "end": 3.5,
                "text": "Hello and welcome to the show",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "and", "start": 0.6, "end": 0.8},
                    {"word": "welcome", "start": 0.9, "end": 1.4},
                    {"word": "to", "start": 1.5, "end": 1.7},
                    {"word": "the", "start": 1.8, "end": 2.0},
                    {"word": "show", "start": 2.1, "end": 3.5},
                ],
            },
            {
                "start": 4.0,
                "end": 8.0,
                "text": "Today we will discuss AI topics",
                "words": [
                    {"word": "Today", "start": 4.0, "end": 4.5},
                    {"word": "we", "start": 4.6, "end": 4.8},
                    {"word": "will", "start": 4.9, "end": 5.2},
                    {"word": "discuss", "start": 5.3, "end": 5.9},
                    {"word": "AI", "start": 6.0, "end": 6.5},
                    {"word": "topics", "start": 6.6, "end": 8.0},
                ],
            },
        ],
        "word_segments": [],
    }
    return mock


# ============================================================================
# TRANSCRIBER INITIALIZATION TESTS
# ============================================================================


class TestTranscriberInit:
    """Tests for Transcriber.__init__() method."""

    def test_transcriber_init_default_device(self, mock_whisper_model):
        """Verify auto device selection defaults to 'cpu'."""
        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ) as mock_load:
            from src.transcriber import Transcriber

            transcriber = Transcriber(model_size="base", device="auto")

            assert transcriber.device == "cpu"
            mock_load.assert_called_once_with(
                model_size="base", device="cpu", compute_type="int8"
            )

    def test_transcriber_init_explicit_device(self, mock_whisper_model):
        """Verify explicit device parameter is respected."""
        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ) as mock_load:
            from src.transcriber import Transcriber

            transcriber = Transcriber(model_size="small", device="mps")

            assert transcriber.device == "mps"
            mock_load.assert_called_once_with(
                model_size="small", device="mps", compute_type="int8"
            )

    def test_transcriber_init_model_loading(self, mock_whisper_model):
        """Verify load_whisper_model is called with correct parameters."""
        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ) as mock_load:
            from src.transcriber import Transcriber

            transcriber = Transcriber(
                model_size="large-v2", device="cpu", compute_type="float16"
            )

            assert transcriber.model == mock_whisper_model
            assert transcriber.model_size == "large-v2"
            assert transcriber.compute_type == "float16"
            mock_load.assert_called_once_with(
                model_size="large-v2", device="cpu", compute_type="float16"
            )


# ============================================================================
# TRANSCRIBE METHOD TESTS
# ============================================================================


class TestTranscribeMethod:
    """Tests for Transcriber.transcribe() method."""

    def test_transcribe_missing_video_file(self, tmp_project_dir, mock_whisper_model):
        """Verify None is returned and error is logged for non-existent files."""
        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.transcribe("/nonexistent/video.mp4")

            assert result is None

    def test_transcribe_skip_if_exists(self, tmp_project_dir, mock_whisper_model):
        """Verify existing transcript is returned without reprocessing."""
        # Create a fake video file
        video_file = tmp_project_dir / "videos" / "test_video.mp4"
        video_file.touch()

        # Create existing transcript
        transcript_path = tmp_project_dir / "temp" / "test_video_transcript.json"
        transcript_data = {"video_id": "test_video", "language": "en", "segments": []}
        transcript_path.write_text(json.dumps(transcript_data), encoding="utf-8")

        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.transcribe(str(video_file), skip_if_exists=True)

            assert result == str(transcript_path)

    def test_transcribe_full_flow(
        self,
        tmp_project_dir,
        mock_whisper_model,
        mock_align_model,
        mock_whisperx,
    ):
        """Verify complete transcription flow with mocked whisperx."""
        # Create a fake video file
        video_file = tmp_project_dir / "videos" / "test_video.mp4"
        video_file.touch()

        # Create fake audio file (simulating _extract_audio success)
        audio_path = tmp_project_dir / "temp" / "test_video_audio.wav"
        audio_path.touch()

        with (
            patch(
                "src.transcriber.load_whisper_model", return_value=mock_whisper_model
            ),
            patch(
                "src.transcriber.load_align_model", return_value=mock_align_model
            ),
            patch.dict("sys.modules", {"whisperx": mock_whisperx}),
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.transcribe(str(video_file), skip_if_exists=False)

            assert result is not None
            assert result.endswith("test_video_transcript.json")

            # Verify the transcript file was created with correct structure
            transcript_path = Path(result)
            assert transcript_path.exists()

            transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
            assert transcript_data["video_id"] == "test_video"
            assert transcript_data["language"] == "en"
            assert "segments" in transcript_data
            assert len(transcript_data["segments"]) == 2

    def test_transcribe_audio_extraction_failure(
        self, tmp_project_dir, mock_whisper_model
    ):
        """Verify None is returned when ffmpeg audio extraction fails."""
        # Create a fake video file
        video_file = tmp_project_dir / "videos" / "test_video.mp4"
        video_file.touch()

        with (
            patch(
                "src.transcriber.load_whisper_model", return_value=mock_whisper_model
            ),
            patch("subprocess.run") as mock_subprocess,
        ):
            # Simulate ffmpeg failure
            mock_subprocess.return_value = MagicMock(
                returncode=1, stderr="Error: invalid input"
            )

            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.transcribe(str(video_file), skip_if_exists=False)

            assert result is None


# ============================================================================
# LOAD TRANSCRIPT TESTS
# ============================================================================


class TestLoadTranscript:
    """Tests for Transcriber.load_transcript() method."""

    def test_load_transcript_valid_json(
        self, tmp_project_dir, mock_whisper_model, sample_transcript
    ):
        """Verify JSON loading using sample_transcript fixture."""
        # Save sample_transcript to temp directory
        transcript_path = tmp_project_dir / "temp" / "sample_transcript.json"
        full_transcript = {
            "video_id": "sample_video",
            "video_path": "videos/sample_video.mp4",
            "audio_path": "temp/sample_video_audio.wav",
            **sample_transcript,
        }
        transcript_path.write_text(
            json.dumps(full_transcript, indent=2), encoding="utf-8"
        )

        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.load_transcript(str(transcript_path))

            assert result is not None
            assert result["video_id"] == "sample_video"
            assert result["language"] == "en"
            assert len(result["segments"]) == 2
            assert result["segments"][0]["text"] == "Hello and welcome to the show"
            # Verify word-level timestamps exist
            assert "words" in result["segments"][0]
            assert len(result["segments"][0]["words"]) == 6

    def test_load_transcript_invalid_path(self, tmp_project_dir, mock_whisper_model):
        """Verify None is returned for non-existent transcript file."""
        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.load_transcript("/nonexistent/transcript.json")

            assert result is None


# ============================================================================
# GET TRANSCRIPT SUMMARY TESTS
# ============================================================================


class TestGetTranscriptSummary:
    """Tests for Transcriber.get_transcript_summary() method."""

    def test_get_transcript_summary(
        self, tmp_project_dir, mock_whisper_model, sample_transcript
    ):
        """Verify summary dict contains expected fields."""
        # Save sample_transcript to temp directory
        transcript_path = tmp_project_dir / "temp" / "summary_transcript.json"
        full_transcript = {
            "video_id": "summary_video",
            "video_path": "videos/summary_video.mp4",
            "audio_path": "temp/summary_video_audio.wav",
            **sample_transcript,
        }
        transcript_path.write_text(
            json.dumps(full_transcript, indent=2), encoding="utf-8"
        )

        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.get_transcript_summary(str(transcript_path))

            assert result is not None
            assert result["language"] == "en"
            assert result["num_segments"] == 2
            assert result["total_duration"] == 8.0  # Last segment end time
            assert result["total_words"] == 12  # 6 + 6 words
            assert "Hello and welcome" in result["first_text"]

    def test_get_transcript_summary_empty_segments(
        self, tmp_project_dir, mock_whisper_model
    ):
        """Verify None is returned when segments list is empty."""
        # Save transcript with empty segments
        transcript_path = tmp_project_dir / "temp" / "empty_transcript.json"
        empty_transcript = {
            "video_id": "empty_video",
            "language": "en",
            "segments": [],
        }
        transcript_path.write_text(
            json.dumps(empty_transcript, indent=2), encoding="utf-8"
        )

        with patch(
            "src.transcriber.load_whisper_model", return_value=mock_whisper_model
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.get_transcript_summary(str(transcript_path))

            assert result is None


# ============================================================================
# LANGUAGE DETECTION TESTS
# ============================================================================


class TestLanguageDetection:
    """Tests for language detection functionality."""

    def test_language_detection(
        self,
        tmp_project_dir,
        mock_whisper_model,
        mock_align_model,
        mock_whisperx,
    ):
        """Verify detected language is stored in transcript output."""
        # Create a fake video file
        video_file = tmp_project_dir / "videos" / "spanish_video.mp4"
        video_file.touch()

        # Create fake audio file
        audio_path = tmp_project_dir / "temp" / "spanish_video_audio.wav"
        audio_path.touch()

        # Configure mock to return Spanish as detected language
        mock_whisper_model.transcribe.return_value = {
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "Hola y bienvenidos"},
            ],
            "language": "es",
        }

        with (
            patch(
                "src.transcriber.load_whisper_model", return_value=mock_whisper_model
            ),
            patch(
                "src.transcriber.load_align_model", return_value=mock_align_model
            ),
            patch.dict("sys.modules", {"whisperx": mock_whisperx}),
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.transcribe(str(video_file), skip_if_exists=False)

            assert result is not None

            # Verify Spanish language is in the transcript
            transcript_path = Path(result)
            transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
            assert transcript_data["language"] == "es"

    def test_language_code_mapping(
        self,
        tmp_project_dir,
        mock_whisper_model,
        mock_align_model,
        mock_whisperx,
    ):
        """Verify full language names are mapped to ISO codes for alignment."""
        # Create a fake video file
        video_file = tmp_project_dir / "videos" / "english_video.mp4"
        video_file.touch()

        # Create fake audio file
        audio_path = tmp_project_dir / "temp" / "english_video_audio.wav"
        audio_path.touch()

        # Configure mock to return full language name (as WhisperX sometimes does)
        mock_whisper_model.transcribe.return_value = {
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "Hello world"},
            ],
            "language": "english",  # Full name instead of 'en'
        }

        with (
            patch(
                "src.transcriber.load_whisper_model", return_value=mock_whisper_model
            ),
            patch(
                "src.transcriber.load_align_model", return_value=mock_align_model
            ) as mock_load_align,
            patch.dict("sys.modules", {"whisperx": mock_whisperx}),
        ):
            from src.transcriber import Transcriber

            transcriber = Transcriber()
            result = transcriber.transcribe(str(video_file), skip_if_exists=False)

            assert result is not None
            # Verify load_align_model was called with ISO code 'en' not 'english'
            mock_load_align.assert_called_once()
            call_kwargs = mock_load_align.call_args[1]
            assert call_kwargs["language_code"] == "en"
