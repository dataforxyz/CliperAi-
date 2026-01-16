"""
Shared pytest fixtures for the CLIPER test suite.
"""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import pytest

# ============================================================================
# ASYNC HELPER
# ============================================================================


async def _wait_until(
    pilot, predicate: Callable[[], bool], *, timeout: float = 5.0, step: float = 0.05
) -> None:
    """
    Wait until predicate returns True or timeout is reached.

    Args:
        pilot: Textual Pilot instance
        predicate: Callable returning bool
        timeout: Maximum time to wait in seconds
        step: Polling interval in seconds

    Raises:
        AssertionError: If timeout is reached before predicate returns True
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        if predicate():
            return
        if loop.time() >= deadline:
            raise AssertionError("Timed out waiting for UI state")
        await pilot.pause(step)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_project_dir(tmp_path: Path, monkeypatch):
    """
    Create a temporary project directory with state files and videos/ subdirectory.

    Creates:
        - temp/project_state.json: Empty dict for video state
        - temp/jobs_state.json: {"jobs": {}, "queue": []}
        - videos/: Empty subdirectory for video files

    The fixture also isolates the StateManager singleton by resetting it.
    """
    monkeypatch.chdir(tmp_path)

    # Create state files directory
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Create project_state.json (video state)
    project_state_file = temp_dir / "project_state.json"
    project_state_file.write_text("{}", encoding="utf-8")

    # Create jobs_state.json
    jobs_state_file = temp_dir / "jobs_state.json"
    jobs_state_file.write_text(
        json.dumps({"jobs": {}, "queue": []}, indent=2),
        encoding="utf-8",
    )

    # Create videos/ subdirectory
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # Isolate StateManager singleton
    import src.utils.state_manager as state_manager_module

    state_manager_module._state_manager_instance = None
    settings_file = tmp_path / "config" / "app_settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps({"_wizard_completed": True}), encoding="utf-8")
    state_manager_module._state_manager_init_kwargs = {
        "app_root": tmp_path,
        "settings_file": settings_file,
    }

    return tmp_path


@pytest.fixture
def mock_gemini_client(monkeypatch):
    """
    Mock langchain_google_genai.ChatGoogleGenerativeAI with canned responses.

    Returns a mock that simulates Gemini API responses with a configurable
    response content.
    """
    mock_response = MagicMock()
    mock_response.content = json.dumps(
        {
            "clips": [
                {
                    "clip_id": 1,
                    "copy": "Test copy with #AICDMX hashtag for engagement",
                    "metadata": {
                        "engagement_score": 8.5,
                        "viral_potential": 7.5,
                        "tone": "informative",
                        "target_platform": "instagram",
                    },
                }
            ]
        }
    )

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    mock_class = MagicMock(return_value=mock_llm)

    monkeypatch.setattr(
        "langchain_google_genai.ChatGoogleGenerativeAI",
        mock_class,
    )

    return mock_llm


@pytest.fixture(scope="session")
def sample_transcript():
    """
    WhisperX-compatible transcript dict with segments and word-level timestamps.

    Returns a dict with 'segments' array where each segment contains:
        - start: Start time in seconds
        - end: End time in seconds
        - text: Segment text
        - words: List of word dicts with word/start/end keys
    """
    return {
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
        "language": "en",
    }


# Skip marker for tests requiring ffmpeg
ffmpeg_available = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="ffmpeg not available",
)


@pytest.fixture(scope="session")
def sample_job_spec():
    """
    Valid JobSpec instance for testing.

    Returns a JobSpec with:
        - job_id: "test-job-001"
        - video_ids: ["test_video"]
        - steps: [JobStep.TRANSCRIBE]
        - settings: Empty dict
    """
    from src.core.models import JobSpec, JobStep

    return JobSpec(
        job_id="test-job-001",
        video_ids=["test_video"],
        steps=[JobStep.TRANSCRIBE],
        settings={},
    )
