"""
Comprehensive tests for src/downloader.py - YoutubeDownloader class
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yt_dlp

from src.core.dependency_manager import DependencyProgress, DependencyStatus
from src.downloader import YoutubeDownloader, download_video

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_reporter():
    """
    Mock implementation of DependencyReporter protocol for testing progress callbacks.
    """
    reporter = MagicMock()
    reporter.report = MagicMock()
    reporter.is_cancelled = MagicMock(return_value=False)
    reporter.reported_events: list[DependencyProgress] = []

    def capture_report(event: DependencyProgress):
        reporter.reported_events.append(event)

    reporter.report.side_effect = capture_report
    return reporter


@pytest.fixture
def mock_video_info():
    """
    Standard mock video info returned by yt-dlp.
    """
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Test Video Title",
        "duration": 212,
        "uploader": "Test Uploader",
        "view_count": 1000000,
        "description": "Test description",
        "thumbnail": "https://example.com/thumb.jpg",
        "ext": "mp4",
    }


@pytest.fixture
def downloader(tmp_project_dir):
    """
    YoutubeDownloader instance with tmp_project_dir as download directory.
    """
    download_dir = tmp_project_dir / "downloads"
    return YoutubeDownloader(download_dir=str(download_dir))


@pytest.fixture
def downloader_with_reporter(tmp_project_dir, mock_reporter):
    """
    YoutubeDownloader instance with mock reporter attached.
    """
    download_dir = tmp_project_dir / "downloads"
    return YoutubeDownloader(download_dir=str(download_dir), reporter=mock_reporter)


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestYoutubeDownloaderInit:
    """Tests for YoutubeDownloader.__init__"""

    def test_init_default_download_dir(self, tmp_project_dir, monkeypatch):
        """Test initialization with default download directory."""
        monkeypatch.chdir(tmp_project_dir)
        dl = YoutubeDownloader()
        assert dl.download_dir == Path("downloads")
        assert dl.download_dir.exists()

    def test_init_custom_download_dir(self, tmp_project_dir):
        """Test initialization with custom download directory."""
        custom_dir = tmp_project_dir / "my_videos"
        dl = YoutubeDownloader(download_dir=str(custom_dir))
        assert dl.download_dir == custom_dir
        assert custom_dir.exists()

    def test_init_creates_nested_directories(self, tmp_project_dir):
        """Test that nested directories are created."""
        nested_dir = tmp_project_dir / "a" / "b" / "c" / "videos"
        YoutubeDownloader(download_dir=str(nested_dir))
        assert nested_dir.exists()

    def test_init_with_reporter(self, tmp_project_dir, mock_reporter):
        """Test initialization with a DependencyReporter."""
        dl = YoutubeDownloader(
            download_dir=str(tmp_project_dir / "downloads"), reporter=mock_reporter
        )
        assert dl.reporter is mock_reporter

    def test_init_without_reporter(self, tmp_project_dir):
        """Test initialization without reporter sets None."""
        dl = YoutubeDownloader(download_dir=str(tmp_project_dir / "downloads"))
        assert dl.reporter is None

    def test_init_active_download_key_is_none(self, downloader):
        """Test that _active_download_key starts as None."""
        assert downloader._active_download_key is None


# ============================================================================
# URL VALIDATION TESTS
# ============================================================================


class TestValidateUrl:
    """Tests for YoutubeDownloader.validate_url()"""

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ",
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube.com/watch?v=dQw4w9WgXcQ",
        ],
    )
    def test_valid_youtube_com_urls(self, downloader, url):
        """Test validation of various youtube.com URL formats."""
        assert downloader.validate_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
            "youtu.be/dQw4w9WgXcQ",
        ],
    )
    def test_valid_youtu_be_urls(self, downloader, url):
        """Test validation of youtu.be short URL formats."""
        assert downloader.validate_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
        ],
    )
    def test_valid_embed_urls(self, downloader, url):
        """Test validation of embed and v/ URL formats."""
        assert downloader.validate_url(url) is True

    def test_url_with_extra_query_params(self, downloader):
        """Test URL with additional query parameters is valid."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        assert downloader.validate_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "   ",
            "not a url",
            "https://vimeo.com/123456789",
            "https://example.com/video",
            "https://google.com",
            "ftp://youtube.com/watch?v=dQw4w9WgXcQ",
        ],
    )
    def test_invalid_urls(self, downloader, url):
        """Test that non-YouTube URLs are rejected."""
        assert downloader.validate_url(url) is False

    def test_url_with_short_video_id(self, downloader):
        """Test URL with video ID shorter than 11 chars is invalid."""
        url = "https://www.youtube.com/watch?v=abc"
        assert downloader.validate_url(url) is False


# ============================================================================
# VIDEO ID EXTRACTION TESTS
# ============================================================================


class TestExtractVideoId:
    """Tests for YoutubeDownloader._extract_video_id()"""

    def test_extract_from_youtube_com_watch(self, downloader):
        """Test extraction from youtube.com/watch?v= format."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert downloader._extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_youtu_be(self, downloader):
        """Test extraction from youtu.be/ format."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert downloader._extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_with_extra_query_params(self, downloader):
        """Test extraction ignores extra query params in youtube.com URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        assert downloader._extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_from_youtu_be_with_query_params(self, downloader):
        """Test extraction from youtu.be with query params."""
        url = "https://youtu.be/dQw4w9WgXcQ?t=120"
        assert downloader._extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_returns_none_for_invalid_url(self, downloader):
        """Test extraction returns None for non-YouTube URL."""
        url = "https://example.com/video"
        assert downloader._extract_video_id(url) is None

    def test_extract_returns_none_for_empty_string(self, downloader):
        """Test extraction returns None for empty string."""
        assert downloader._extract_video_id("") is None


# ============================================================================
# GET VIDEO INFO TESTS
# ============================================================================


class TestGetVideoInfo:
    """Tests for YoutubeDownloader.get_video_info()"""

    def test_get_video_info_success(self, downloader, mock_video_info):
        """Test successful video info extraction."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.get_video_info(url)

            assert result is not None
            assert result["id"] == "dQw4w9WgXcQ"
            assert result["title"] == "Test Video Title"
            assert result["duration"] == 212
            mock_ydl.extract_info.assert_called_once_with(url, download=False)

    def test_get_video_info_invalid_url(self, downloader):
        """Test get_video_info returns None for invalid URL."""
        result = downloader.get_video_info("https://example.com/invalid")
        assert result is None

    def test_get_video_info_exception(self, downloader):
        """Test get_video_info returns None on yt-dlp exception."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = Exception("Network error")
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.get_video_info(url)

            assert result is None


# ============================================================================
# DOWNLOAD TESTS
# ============================================================================


class TestDownload:
    """Tests for YoutubeDownloader.download()"""

    def test_download_success(self, downloader, tmp_project_dir, mock_video_info):
        """Test successful video download."""
        download_path = (
            tmp_project_dir / "downloads" / "Test Video Title_dQw4w9WgXcQ.mp4"
        )
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download(url)

            assert result == str(download_path)
            mock_ydl.extract_info.assert_called_once_with(url, download=True)

    def test_download_with_quality_1080p(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test download with 1080p quality option."""
        download_path = tmp_project_dir / "downloads" / "Test_dQw4w9WgXcQ.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download(url, quality="1080p")

            # Verify the format option was set correctly
            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]
            assert "1080" in opts["format"]

    def test_download_with_custom_filename(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test download with custom output filename."""
        download_path = tmp_project_dir / "downloads" / "my_custom_name_dQw4w9WgXcQ.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download(url, output_filename="my_custom_name")

            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]
            assert "my_custom_name" in opts["outtmpl"]

    def test_download_sanitizes_filename(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test that special characters are removed from custom filename."""
        download_path = tmp_project_dir / "downloads" / "myfile_dQw4w9WgXcQ.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download(url, output_filename='my<>:"/\\|?*file')

            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]
            # Special characters should be removed
            assert "<" not in opts["outtmpl"]
            assert ">" not in opts["outtmpl"]
            assert "myfile" in opts["outtmpl"]

    def test_download_invalid_url(self, downloader):
        """Test download returns None for invalid URL."""
        result = downloader.download("https://example.com/invalid")
        assert result is None

    def test_download_file_not_found(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test download returns None when file not found after download."""
        # Don't create the file - simulate file not found after download
        nonexistent_path = tmp_project_dir / "downloads" / "nonexistent.mp4"

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(nonexistent_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download(url)

            assert result is None

    def test_download_converts_extension_to_mp4(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test that download converts non-mp4 extension to mp4."""
        # Create mp4 file, but prepare_filename returns .webm
        webm_path = tmp_project_dir / "downloads" / "video.webm"
        mp4_path = tmp_project_dir / "downloads" / "video.mp4"
        mp4_path.parent.mkdir(parents=True, exist_ok=True)
        mp4_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(webm_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download(url)

            assert result == str(mp4_path)


# ============================================================================
# DOWNLOAD ERROR HANDLING TESTS
# ============================================================================


class TestDownloadErrorHandling:
    """Tests for error handling in YoutubeDownloader.download()"""

    def test_download_error_yt_dlp_exception(self, downloader):
        """Test handling of yt_dlp.utils.DownloadError."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
                "Video unavailable"
            )
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download(url)

            assert result is None

    def test_download_error_generic_exception(self, downloader):
        """Test handling of generic exceptions."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = RuntimeError("Unexpected error")
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download(url)

            assert result is None

    def test_download_error_reports_to_reporter(
        self, downloader_with_reporter, mock_reporter
    ):
        """Test that download errors are reported to the reporter."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError(
                "Network error"
            )
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader_with_reporter.download(url)

            # Check that an error status was reported
            error_events = [
                e
                for e in mock_reporter.reported_events
                if e.status == DependencyStatus.ERROR
            ]
            assert len(error_events) > 0
            assert "Network error" in error_events[-1].message

    def test_download_file_not_found_reports_error(
        self, downloader_with_reporter, mock_reporter, mock_video_info, tmp_project_dir
    ):
        """Test that file not found after download reports error."""
        nonexistent_path = tmp_project_dir / "downloads" / "nonexistent.mp4"

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(nonexistent_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader_with_reporter.download(url)

            error_events = [
                e
                for e in mock_reporter.reported_events
                if e.status == DependencyStatus.ERROR
            ]
            assert len(error_events) > 0

    def test_download_resets_active_download_key_on_error(self, downloader):
        """Test that _active_download_key is reset after error."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = Exception("Error")
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download(url)

            assert downloader._active_download_key is None


# ============================================================================
# DOWNLOAD AUDIO ONLY TESTS
# ============================================================================


class TestDownloadAudioOnly:
    """Tests for YoutubeDownloader.download_audio_only()"""

    def test_download_audio_only_success(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test successful audio-only download."""
        audio_path = tmp_project_dir / "downloads" / "Test Video Title_dQw4w9WgXcQ.mp3"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(
                audio_path.with_suffix(".webm")
            )
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download_audio_only(url)

            assert result == str(audio_path)

    def test_download_audio_only_invalid_url(self, downloader):
        """Test download_audio_only returns None for invalid URL."""
        result = downloader.download_audio_only("https://example.com/invalid")
        assert result is None

    def test_download_audio_only_file_not_found(self, downloader, mock_video_info):
        """Test download_audio_only returns None when file not found."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = "/nonexistent/path.webm"
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download_audio_only(url)

            assert result is None

    def test_download_audio_only_exception(self, downloader):
        """Test download_audio_only returns None on exception."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.side_effect = Exception("FFmpeg not found")
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = downloader.download_audio_only(url)

            assert result is None

    def test_download_audio_only_uses_correct_format(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test that audio download uses bestaudio format."""
        audio_path = tmp_project_dir / "downloads" / "audio.mp3"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(
                audio_path.with_suffix(".webm")
            )
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download_audio_only(url)

            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]
            assert opts["format"] == "bestaudio/best"
            assert opts["postprocessors"][0]["key"] == "FFmpegExtractAudio"
            assert opts["postprocessors"][0]["preferredcodec"] == "mp3"


# ============================================================================
# PROGRESS HOOK TESTS
# ============================================================================


class TestProgressHook:
    """Tests for YoutubeDownloader._progress_hook()"""

    def test_progress_hook_downloading_status(self, downloader):
        """Test progress hook with downloading status."""
        downloader._active_download_key = "test_key"

        progress_dict = {
            "status": "downloading",
            "_percent_str": "50.5%",
            "_speed_str": "1.5MiB/s",
            "_eta_str": "00:30",
        }

        # Should not raise
        downloader._progress_hook(progress_dict)

    def test_progress_hook_finished_status(self, downloader):
        """Test progress hook with finished status."""
        downloader._active_download_key = "test_key"

        progress_dict = {
            "status": "finished",
        }

        # Should not raise
        downloader._progress_hook(progress_dict)

    def test_progress_hook_reports_downloading_to_reporter(
        self, downloader_with_reporter, mock_reporter
    ):
        """Test that downloading progress is reported to reporter."""
        downloader_with_reporter._active_download_key = "test_key"
        downloader_with_reporter._active_download_desc = "Test download"

        progress_dict = {
            "status": "downloading",
            "_percent_str": "75.0%",
            "_speed_str": "2.0MiB/s",
            "_eta_str": "00:15",
        }

        downloader_with_reporter._progress_hook(progress_dict)

        assert mock_reporter.report.called
        last_event = mock_reporter.reported_events[-1]
        assert last_event.status == DependencyStatus.DOWNLOADING
        assert "75.0%" in last_event.message

    def test_progress_hook_reports_finished_to_reporter(
        self, downloader_with_reporter, mock_reporter
    ):
        """Test that finished status is reported to reporter."""
        downloader_with_reporter._active_download_key = "test_key"
        downloader_with_reporter._active_download_desc = "Test download"

        progress_dict = {
            "status": "finished",
        }

        downloader_with_reporter._progress_hook(progress_dict)

        assert mock_reporter.report.called
        last_event = mock_reporter.reported_events[-1]
        assert last_event.status == DependencyStatus.DOWNLOADING
        assert "processing" in last_event.message.lower()

    def test_progress_hook_handles_missing_fields(self, downloader):
        """Test progress hook handles missing optional fields gracefully."""
        downloader._active_download_key = "test_key"

        progress_dict = {
            "status": "downloading",
            # Missing _percent_str, _speed_str, _eta_str
        }

        # Should not raise - uses 'N/A' defaults
        downloader._progress_hook(progress_dict)

    def test_progress_hook_no_report_without_active_key(
        self, downloader_with_reporter, mock_reporter
    ):
        """Test that no report is made when _active_download_key is None."""
        downloader_with_reporter._active_download_key = None

        progress_dict = {
            "status": "downloading",
            "_percent_str": "50%",
        }

        initial_call_count = mock_reporter.report.call_count
        downloader_with_reporter._progress_hook(progress_dict)

        # No new reports should be made (reporter.report shouldn't be called for progress)
        assert mock_reporter.report.call_count == initial_call_count


# ============================================================================
# REPORTER INTEGRATION TESTS
# ============================================================================


class TestReporterIntegration:
    """Tests for DependencyReporter integration in downloads."""

    def test_download_reports_starting_status(
        self, downloader_with_reporter, mock_reporter, mock_video_info, tmp_project_dir
    ):
        """Test that download reports DOWNLOADING status at start."""
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader_with_reporter.download(url)

            # First event should be DOWNLOADING with "Starting..."
            first_event = mock_reporter.reported_events[0]
            assert first_event.status == DependencyStatus.DOWNLOADING
            assert "Starting" in first_event.message

    def test_download_reports_done_on_success(
        self, downloader_with_reporter, mock_reporter, mock_video_info, tmp_project_dir
    ):
        """Test that successful download reports DONE status."""
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader_with_reporter.download(url)

            # Last event should be DONE
            done_events = [
                e
                for e in mock_reporter.reported_events
                if e.status == DependencyStatus.DONE
            ]
            assert len(done_events) > 0

    def test_download_key_includes_video_id(
        self, downloader_with_reporter, mock_reporter, mock_video_info, tmp_project_dir
    ):
        """Test that download key includes video ID."""
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader_with_reporter.download(url)

            first_event = mock_reporter.reported_events[0]
            assert "dQw4w9WgXcQ" in first_event.key


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


class TestDownloadVideoHelper:
    """Tests for download_video() helper function."""

    def test_download_video_helper_success(
        self, tmp_project_dir, mock_video_info, monkeypatch
    ):
        """Test download_video helper function."""
        monkeypatch.chdir(tmp_project_dir)
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            result = download_video(url)

            assert result == str(download_path)

    def test_download_video_helper_with_quality(
        self, tmp_project_dir, mock_video_info, monkeypatch
    ):
        """Test download_video helper with quality parameter."""
        monkeypatch.chdir(tmp_project_dir)
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            download_video(url, quality="720p")

            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]
            assert "720" in opts["format"]

    def test_download_video_helper_invalid_url(self, tmp_project_dir, monkeypatch):
        """Test download_video helper with invalid URL."""
        monkeypatch.chdir(tmp_project_dir)
        result = download_video("https://example.com/invalid")
        assert result is None


# ============================================================================
# QUALITY FORMAT MAPPING TESTS
# ============================================================================


class TestQualityFormatMapping:
    """Tests for quality format mapping in download()."""

    @pytest.mark.parametrize(
        "quality,expected_height",
        [
            ("best", None),  # 'best' doesn't have height restriction
            ("1080p", "1080"),
            ("720p", "720"),
            ("480p", "480"),
            ("360p", "360"),
        ],
    )
    def test_quality_format_options(
        self, downloader, tmp_project_dir, mock_video_info, quality, expected_height
    ):
        """Test that quality options map to correct yt-dlp formats."""
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download(url, quality=quality)

            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]

            if expected_height:
                assert expected_height in opts["format"]
            else:
                assert "bestvideo+bestaudio/best" == opts["format"]

    def test_unknown_quality_defaults_to_best(
        self, downloader, tmp_project_dir, mock_video_info
    ):
        """Test that unknown quality option defaults to 'best'."""
        download_path = tmp_project_dir / "downloads" / "video.mp4"
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
            mock_ydl.__exit__ = MagicMock(return_value=False)
            mock_ydl.extract_info.return_value = mock_video_info
            mock_ydl.prepare_filename.return_value = str(download_path)
            mock_ydl_class.return_value = mock_ydl

            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            downloader.download(url, quality="unknown_quality")

            call_args = mock_ydl_class.call_args
            opts = call_args[0][0]
            assert opts["format"] == "bestvideo+bestaudio/best"
