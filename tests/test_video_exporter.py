"""
Comprehensive pytest tests for src/video_exporter.py

Tests cover:
- Helper functions (_safe_parse_ffprobe_r_frame_rate, _resolve_ffmpeg_threads)
- Filter generation (_get_logo_overlay_filter, _get_subtitle_filter, _get_aspect_ratio_filter)
- Path escaping (_escape_ffmpeg_filter_path)
- Integration tests with mocked subprocess for _export_single_clip
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.video_exporter import (
    VideoExporter,
    _resolve_ffmpeg_threads,
    _safe_parse_ffprobe_r_frame_rate,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def exporter():
    """
    Create VideoExporter instance bypassing __init__ to avoid ffmpeg check.
    Uses __new__ pattern from test_logo_scale_filtergraph.py.
    """
    exp = VideoExporter.__new__(VideoExporter)
    # Initialize minimal attributes needed for tests
    exp.subtitle_generator = MagicMock()
    return exp


# ============================================================================
# TESTS FOR _safe_parse_ffprobe_r_frame_rate()
# ============================================================================


class TestSafeParseFFprobeRFrameRate:
    """Tests for the _safe_parse_ffprobe_r_frame_rate helper function."""

    def test_valid_fraction_30_1(self):
        """Parse standard 30fps as fraction."""
        result = _safe_parse_ffprobe_r_frame_rate("30/1")
        assert result == 30.0

    def test_valid_fraction_30000_1001(self):
        """Parse NTSC 29.97fps as fraction."""
        result = _safe_parse_ffprobe_r_frame_rate("30000/1001")
        assert abs(result - 29.97) < 0.01

    def test_valid_fraction_24000_1001(self):
        """Parse 23.976fps (film) as fraction."""
        result = _safe_parse_ffprobe_r_frame_rate("24000/1001")
        assert abs(result - 23.976) < 0.01

    def test_valid_fraction_60_1(self):
        """Parse 60fps as fraction."""
        result = _safe_parse_ffprobe_r_frame_rate("60/1")
        assert result == 60.0

    def test_integer_input(self):
        """Handle integer input directly."""
        result = _safe_parse_ffprobe_r_frame_rate(30)
        assert result == 30.0

    def test_float_input(self):
        """Handle float input directly."""
        result = _safe_parse_ffprobe_r_frame_rate(29.97)
        assert result == 29.97

    def test_none_input(self):
        """Return 0.0 for None input."""
        result = _safe_parse_ffprobe_r_frame_rate(None)
        assert result == 0.0

    def test_empty_string(self):
        """Return 0.0 for empty string."""
        result = _safe_parse_ffprobe_r_frame_rate("")
        assert result == 0.0

    def test_whitespace_string(self):
        """Return 0.0 for whitespace-only string."""
        result = _safe_parse_ffprobe_r_frame_rate("   ")
        assert result == 0.0

    def test_invalid_string(self):
        """Return 0.0 for invalid string."""
        result = _safe_parse_ffprobe_r_frame_rate("invalid")
        assert result == 0.0

    def test_negative_fraction(self):
        """Return 0.0 for negative fraction."""
        result = _safe_parse_ffprobe_r_frame_rate("-30/1")
        assert result == 0.0

    def test_zero_denominator(self):
        """Return 0.0 for zero denominator (division by zero)."""
        result = _safe_parse_ffprobe_r_frame_rate("30/0")
        assert result == 0.0

    def test_list_input(self):
        """Return 0.0 for non-string, non-numeric input."""
        result = _safe_parse_ffprobe_r_frame_rate([30, 1])
        assert result == 0.0

    def test_dict_input(self):
        """Return 0.0 for dict input."""
        result = _safe_parse_ffprobe_r_frame_rate({"fps": 30})
        assert result == 0.0


# ============================================================================
# TESTS FOR _resolve_ffmpeg_threads()
# ============================================================================


class TestResolveFFmpegThreads:
    """Tests for the _resolve_ffmpeg_threads helper function."""

    def test_zero_returns_auto(self):
        """Zero means auto (let ffmpeg decide)."""
        result = _resolve_ffmpeg_threads(0)
        assert result == 0

    def test_positive_value_passthrough(self):
        """Positive values pass through unchanged."""
        assert _resolve_ffmpeg_threads(4) == 4
        assert _resolve_ffmpeg_threads(8) == 8
        assert _resolve_ffmpeg_threads(16) == 16
        assert _resolve_ffmpeg_threads(1) == 1

    def test_negative_value_cpu_relative(self):
        """Negative values subtract from CPU count."""
        with patch("os.cpu_count", return_value=8):
            # -1 means all CPUs minus 1
            result = _resolve_ffmpeg_threads(-1)
            assert result == 7

            # -2 means all CPUs minus 2
            result = _resolve_ffmpeg_threads(-2)
            assert result == 6

    def test_negative_value_minimum_one(self):
        """Negative values that would result in 0 or less return 1."""
        with patch("os.cpu_count", return_value=4):
            # -4 would be 0, but minimum is 1
            result = _resolve_ffmpeg_threads(-4)
            assert result == 1

            # -5 would be -1, but minimum is 1
            result = _resolve_ffmpeg_threads(-5)
            assert result == 1

    def test_negative_with_none_cpu_count(self):
        """Handle None from os.cpu_count() (fallback to 4)."""
        with patch("os.cpu_count", return_value=None):
            # Uses fallback of 4 CPUs
            result = _resolve_ffmpeg_threads(-1)
            assert result == 3  # 4 - 1


# ============================================================================
# TESTS FOR _get_logo_overlay_filter()
# ============================================================================


class TestGetLogoOverlayFilter:
    """Tests for the _get_logo_overlay_filter method."""

    def test_top_right_position(self, exporter):
        """Test logo placement in top-right corner."""
        chains, output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="top-right",
            scale=0.1,
        )
        assert len(chains) == 2
        assert "scale2ref" in chains[0]
        assert "main_w*0.1" in chains[0]
        assert "W-w-20:20" in chains[1]  # top-right position
        assert output == "[v_out]"

    def test_top_left_position(self, exporter):
        """Test logo placement in top-left corner."""
        chains, output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="top-left",
            scale=0.1,
        )
        assert "20:20" in chains[1]  # top-left position
        assert output == "[v_out]"

    def test_bottom_right_position(self, exporter):
        """Test logo placement in bottom-right corner."""
        chains, output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="bottom-right",
            scale=0.1,
        )
        assert "W-w-20:H-h-20" in chains[1]  # bottom-right position
        assert output == "[v_out]"

    def test_bottom_left_position(self, exporter):
        """Test logo placement in bottom-left corner."""
        chains, output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="bottom-left",
            scale=0.1,
        )
        assert "20:H-h-20" in chains[1]  # bottom-left position
        assert output == "[v_out]"

    def test_invalid_position_defaults_to_top_right(self, exporter):
        """Invalid position defaults to top-right."""
        chains, output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="center",  # invalid
            scale=0.1,
        )
        assert "W-w-20:20" in chains[1]  # defaults to top-right
        assert output == "[v_out]"

    def test_scale_0_1(self, exporter):
        """Test 10% scale (logo is 10% of video width)."""
        chains, _output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="top-right",
            scale=0.1,
        )
        assert "main_w*0.1" in chains[0]

    def test_scale_0_25(self, exporter):
        """Test 25% scale (logo is 25% of video width)."""
        chains, _output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="top-right",
            scale=0.25,
        )
        assert "main_w*0.25" in chains[0]

    def test_scale_0_5(self, exporter):
        """Test 50% scale (logo is half of video width)."""
        chains, _output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="top-right",
            scale=0.5,
        )
        assert "main_w*0.5" in chains[0]

    def test_custom_stream_labels(self, exporter):
        """Test with custom stream labels."""
        chains, output = exporter._get_logo_overlay_filter(
            video_stream="[v_filtered]",
            logo_stream="[2:v]",
            position="top-right",
            scale=0.15,
        )
        assert "[2:v][v_filtered]" in chains[0]
        assert "main_w*0.15" in chains[0]
        assert output == "[v_out]"

    def test_filter_chain_structure(self, exporter):
        """Verify filter chain has correct structure for FFmpeg."""
        chains, _output = exporter._get_logo_overlay_filter(
            video_stream="[0:v]",
            logo_stream="[1:v]",
            position="top-right",
            scale=0.1,
        )
        # First chain: scale2ref with logo and video inputs
        assert "[1:v][0:v]scale2ref" in chains[0]
        assert "[logo_scaled][video_for_overlay]" in chains[0]
        # Second chain: overlay
        assert "[video_for_overlay][logo_scaled]overlay=" in chains[1]


# ============================================================================
# TESTS FOR _get_subtitle_filter()
# ============================================================================


class TestGetSubtitleFilter:
    """Tests for the _get_subtitle_filter method."""

    def test_default_style(self, exporter):
        """Test default subtitle style."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "default")
        assert "subtitles='/path/to/subs.srt'" in result
        assert "FontName=Arial" in result
        assert "FontSize=18" in result
        assert "PrimaryColour=&H0000FFFF" in result  # Yellow
        assert "Bold=0" in result

    def test_bold_style(self, exporter):
        """Test bold subtitle style."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "bold")
        assert "FontSize=22" in result
        assert "Bold=-1" in result

    def test_yellow_style(self, exporter):
        """Test yellow subtitle style."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "yellow")
        assert "FontSize=20" in result
        assert "PrimaryColour=&H0000FFFF" in result
        assert "Bold=-1" in result

    def test_tiktok_style(self, exporter):
        """Test TikTok subtitle style with alignment."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "tiktok")
        assert "FontSize=20" in result
        assert "Shadow=2" in result
        assert "Alignment=10" in result  # Center top

    def test_small_style(self, exporter):
        """Test small subtitle style with margin."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "small")
        assert "FontSize=10" in result
        assert "Alignment=6" in result
        assert "MarginV=100" in result

    def test_tiny_style(self, exporter):
        """Test tiny subtitle style."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "tiny")
        assert "FontSize=8" in result
        assert "Shadow=0" in result
        assert "Alignment=6" in result
        assert "MarginV=100" in result

    def test_custom_style(self, exporter):
        """Test custom subtitle style with __custom__ flag."""
        custom_style = {
            "FontName": "Helvetica",
            "FontSize": "24",
            "PrimaryColour": "&H00FF00FF",  # Magenta
            "OutlineColour": "&H00FFFFFF",
            "Outline": "3",
            "Shadow": "2",
            "Bold": "-1",
        }
        result = exporter._get_subtitle_filter(
            "/path/to/subs.srt", "__custom__", custom_style
        )
        assert "FontName=Helvetica" in result
        assert "FontSize=24" in result
        assert "PrimaryColour=&H00FF00FF" in result

    def test_custom_style_with_alignment(self, exporter):
        """Test custom style with optional Alignment parameter."""
        custom_style = {
            "FontName": "Arial",
            "FontSize": "20",
            "PrimaryColour": "&H0000FFFF",
            "OutlineColour": "&H00000000",
            "Outline": "2",
            "Shadow": "1",
            "Bold": "0",
            "Alignment": "5",  # Custom alignment
        }
        result = exporter._get_subtitle_filter(
            "/path/to/subs.srt", "__custom__", custom_style
        )
        assert "Alignment=5" in result

    def test_custom_style_with_margin(self, exporter):
        """Test custom style with optional MarginV parameter."""
        custom_style = {
            "FontName": "Arial",
            "FontSize": "20",
            "PrimaryColour": "&H0000FFFF",
            "OutlineColour": "&H00000000",
            "Outline": "2",
            "Shadow": "1",
            "Bold": "0",
            "MarginV": "50",
        }
        result = exporter._get_subtitle_filter(
            "/path/to/subs.srt", "__custom__", custom_style
        )
        assert "MarginV=50" in result

    def test_unknown_style_defaults_to_default(self, exporter):
        """Unknown style falls back to default."""
        result = exporter._get_subtitle_filter("/path/to/subs.srt", "nonexistent_style")
        assert "FontSize=18" in result  # default style value
        assert "Bold=0" in result

    def test_custom_style_ignored_without_flag(self, exporter):
        """Custom style dict is ignored when style is not __custom__."""
        custom_style = {
            "FontName": "CustomFont",
            "FontSize": "100",
            "PrimaryColour": "&H000000FF",
            "OutlineColour": "&H00000000",
            "Outline": "5",
            "Shadow": "5",
            "Bold": "-1",
        }
        result = exporter._get_subtitle_filter(
            "/path/to/subs.srt", "default", custom_style
        )
        # Should use default style, not custom
        assert "FontSize=18" in result
        assert "FontSize=100" not in result


# ============================================================================
# TESTS FOR _get_aspect_ratio_filter()
# ============================================================================


class TestGetAspectRatioFilter:
    """Tests for the _get_aspect_ratio_filter method."""

    def test_9_16_vertical(self, exporter):
        """Test 9:16 vertical aspect ratio (TikTok, Reels, Shorts)."""
        result = exporter._get_aspect_ratio_filter("9:16")
        assert result == "crop=ih*9/16:ih,scale=1080:1920"

    def test_1_1_square(self, exporter):
        """Test 1:1 square aspect ratio (Instagram post)."""
        result = exporter._get_aspect_ratio_filter("1:1")
        assert result == "crop=ih:ih,scale=1080:1080"

    def test_16_9_horizontal(self, exporter):
        """Test 16:9 horizontal aspect ratio (standard)."""
        result = exporter._get_aspect_ratio_filter("16:9")
        assert result == "scale=1920:1080"

    def test_unrecognized_ratio_returns_none(self, exporter):
        """Unrecognized aspect ratio returns None."""
        result = exporter._get_aspect_ratio_filter("4:3")
        assert result is None

    def test_invalid_ratio_returns_none(self, exporter):
        """Invalid aspect ratio string returns None."""
        result = exporter._get_aspect_ratio_filter("invalid")
        assert result is None

    def test_empty_string_returns_none(self, exporter):
        """Empty string returns None."""
        result = exporter._get_aspect_ratio_filter("")
        assert result is None


# ============================================================================
# TESTS FOR _escape_ffmpeg_filter_path()
# ============================================================================


class TestEscapeFFmpegFilterPath:
    """Tests for the _escape_ffmpeg_filter_path method."""

    def test_simple_path_unchanged(self, exporter):
        """Simple path without special chars remains unchanged."""
        result = exporter._escape_ffmpeg_filter_path("/path/to/file.srt")
        assert result == "/path/to/file.srt"

    def test_escape_backslashes(self, exporter):
        """Backslashes are escaped."""
        result = exporter._escape_ffmpeg_filter_path("/path\\to\\file.srt")
        assert result == "/path\\\\to\\\\file.srt"

    def test_escape_colons(self, exporter):
        """Colons are escaped (important for Windows drive letters)."""
        result = exporter._escape_ffmpeg_filter_path("C:/path/to/file.srt")
        assert result == "C\\:/path/to/file.srt"

    def test_escape_single_quotes(self, exporter):
        """Single quotes are escaped."""
        result = exporter._escape_ffmpeg_filter_path("/path/it's/file.srt")
        assert result == "/path/it\\'s/file.srt"

    def test_escape_all_special_chars(self, exporter):
        """All special characters are escaped in correct order."""
        # Order matters: backslashes first, then colons, then quotes
        # Colons are also escaped (C: becomes C\:)
        result = exporter._escape_ffmpeg_filter_path("C:\\path's:file.srt")
        assert result == "C\\:\\\\path\\'s\\:file.srt"

    def test_windows_path_full_escape(self, exporter):
        """Full Windows path with drive letter is properly escaped."""
        # C: colon is also escaped in addition to backslashes and quotes
        result = exporter._escape_ffmpeg_filter_path(
            "C:\\Users\\John's Files\\subs.srt"
        )
        assert result == "C\\:\\\\Users\\\\John\\'s Files\\\\subs.srt"


# ============================================================================
# INTEGRATION TESTS FOR _export_single_clip()
# ============================================================================


class TestExportSingleClipIntegration:
    """Integration tests for _export_single_clip with mocked subprocess."""

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run to capture FFmpeg commands."""
        with patch("src.video_exporter.subprocess.run") as mock_run:
            # Default: all FFmpeg calls succeed
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            yield mock_run

    @pytest.fixture
    def setup_clip_export(self, tmp_path, exporter):
        """Set up common fixtures for clip export tests."""
        # Create test directories
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create dummy video file
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        # Create dummy transcript
        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text('{"segments": []}')

        # Sample clip data
        clip = {
            "clip_id": "clip_001",
            "start_time": 10.0,
            "end_time": 40.0,
            "text_preview": "Test clip content",
        }

        return {
            "exporter": exporter,
            "video_path": video_path,
            "output_dir": output_dir,
            "transcript_path": transcript_path,
            "clip": clip,
        }

    def test_basic_export_command_structure(
        self, mock_subprocess_run, setup_clip_export
    ):
        """Test basic clip export generates correct FFmpeg command structure."""
        data = setup_clip_export

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=False,
            transcript_path=None,
        )

        # Verify FFmpeg was called
        assert mock_subprocess_run.called
        cmd = mock_subprocess_run.call_args[0][0]

        # Verify basic command structure
        assert cmd[0] == "ffmpeg"
        assert "-ss" in cmd
        assert "-t" in cmd
        assert "-i" in cmd
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-y" in cmd

    def test_export_with_aspect_ratio(self, mock_subprocess_run, setup_clip_export):
        """Test clip export with aspect ratio conversion."""
        data = setup_clip_export

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio="9:16",
            add_subtitles=False,
            transcript_path=None,
        )

        cmd = mock_subprocess_run.call_args[0][0]

        # Verify aspect ratio filter is applied
        assert "-vf" in cmd
        vf_index = cmd.index("-vf")
        vf_value = cmd[vf_index + 1]
        assert "crop=ih*9/16:ih,scale=1080:1920" in vf_value

    def test_export_with_subtitles(self, mock_subprocess_run, setup_clip_export):
        """Test clip export with subtitles enabled."""
        data = setup_clip_export

        # Mock subtitle generator
        data["exporter"].subtitle_generator.generate_srt_for_clip = MagicMock(
            return_value=True
        )

        # Create dummy SRT file that will exist
        srt_path = data["output_dir"] / "clip_001.srt"
        srt_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nTest subtitle\n")

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=True,
            transcript_path=str(data["transcript_path"]),
            subtitle_style="default",
        )

        # Verify subtitle generator was called
        data["exporter"].subtitle_generator.generate_srt_for_clip.assert_called_once()

        cmd = mock_subprocess_run.call_args[0][0]
        # Verify subtitle filter is in command (either -vf or filter_complex)
        cmd_str = " ".join(cmd)
        assert "subtitles=" in cmd_str

    def test_export_with_logo(self, mock_subprocess_run, setup_clip_export, tmp_path):
        """Test clip export with logo overlay."""
        data = setup_clip_export

        # Create dummy logo file
        logo_path = tmp_path / "logo.png"
        logo_path.touch()

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=False,
            transcript_path=None,
            add_logo=True,
            logo_path=str(logo_path),
            logo_position="top-right",
            logo_scale=0.1,
        )

        cmd = mock_subprocess_run.call_args[0][0]

        # Verify filter_complex is used for logo
        assert "-filter_complex" in cmd

        # Verify logo is a second input
        i_indices = [i for i, x in enumerate(cmd) if x == "-i"]
        assert len(i_indices) >= 2  # At least video and logo inputs

    def test_two_step_processing_logo_and_subtitles(
        self, mock_subprocess_run, setup_clip_export, tmp_path
    ):
        """Test that logo + subtitles uses two-step processing."""
        data = setup_clip_export

        # Mock subtitle generator
        data["exporter"].subtitle_generator.generate_srt_for_clip = MagicMock(
            return_value=True
        )

        # Create dummy files
        srt_path = data["output_dir"] / "clip_001.srt"
        srt_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nTest\n")

        logo_path = tmp_path / "logo.png"
        logo_path.touch()

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=True,
            transcript_path=str(data["transcript_path"]),
            subtitle_style="default",
            add_logo=True,
            logo_path=str(logo_path),
            logo_position="top-right",
            logo_scale=0.1,
        )

        # Verify subprocess.run was called twice (two-step process)
        assert mock_subprocess_run.call_count == 2

        # First call should have logo filter_complex and -sn flag
        first_call_cmd = mock_subprocess_run.call_args_list[0][0][0]
        assert "-filter_complex" in first_call_cmd
        assert "-sn" in first_call_cmd  # Discard subtitle streams

        # Second call should have subtitle filter
        second_call_cmd = mock_subprocess_run.call_args_list[1][0][0]
        cmd_str = " ".join(second_call_cmd)
        assert "subtitles=" in cmd_str

    def test_audio_mapping_with_face_tracking(
        self, mock_subprocess_run, setup_clip_export, tmp_path
    ):
        """Test audio mapping when using reframed video without audio."""
        data = setup_clip_export

        # Create dummy reframed video file (simulating face tracking output)
        reframed_path = data["output_dir"] / "clip_001_reframed_temp.mp4"
        reframed_path.touch()

        # Mock FaceReframer
        with patch("src.video_exporter.FaceReframer") as mock_reframer_class:
            mock_reframer = MagicMock()
            mock_reframer.reframe_video = MagicMock()
            mock_reframer_class.return_value = mock_reframer

            # Make it look like reframing succeeded by having the file exist
            def create_reframed(*args, **kwargs):
                reframed_path.touch()

            mock_reframer.reframe_video.side_effect = create_reframed

            data["exporter"]._export_single_clip(
                video_path=data["video_path"],
                clip=data["clip"],
                video_name="test_video",
                output_dir=data["output_dir"],
                aspect_ratio="9:16",
                add_subtitles=False,
                transcript_path=None,
                enable_face_tracking=True,
                face_tracking_strategy="keep_in_frame",
            )

            # Verify FaceReframer was used
            mock_reframer.reframe_video.assert_called_once()

            # When face tracking is enabled, there should be 2 inputs:
            # [0] = reframed video (no audio)
            # [1] = original video (with audio)
            cmd = mock_subprocess_run.call_args[0][0]
            i_indices = [i for i, x in enumerate(cmd) if x == "-i"]

            # Should have at least 2 -i flags
            assert len(i_indices) >= 2

            # Audio should be mapped from the second input (index 1)
            cmd_str = " ".join(cmd)
            assert "1:a" in cmd_str  # Audio from original video

    def test_crf_and_threads_parameters(self, mock_subprocess_run, setup_clip_export):
        """Test CRF and threads parameters are passed to FFmpeg."""
        data = setup_clip_export

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=False,
            transcript_path=None,
            video_crf=18,
            ffmpeg_threads=4,
        )

        cmd = mock_subprocess_run.call_args[0][0]

        # Verify CRF
        crf_index = cmd.index("-crf")
        assert cmd[crf_index + 1] == "18"

        # Verify threads
        threads_index = cmd.index("-threads")
        assert cmd[threads_index + 1] == "4"

    def test_export_returns_output_path_on_success(
        self, mock_subprocess_run, setup_clip_export
    ):
        """Test that successful export returns the output path."""
        data = setup_clip_export

        result = data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=False,
            transcript_path=None,
        )

        expected_output = data["output_dir"] / "clip_001.mp4"
        assert result == expected_output

    def test_export_returns_none_on_ffmpeg_failure(
        self, mock_subprocess_run, setup_clip_export
    ):
        """Test that failed FFmpeg call returns None."""
        data = setup_clip_export

        # Make FFmpeg fail
        mock_subprocess_run.return_value = MagicMock(
            returncode=1, stderr="FFmpeg error", stdout=""
        )

        result = data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=False,
            transcript_path=None,
        )

        assert result is None

    def test_preset_fast_is_used(self, mock_subprocess_run, setup_clip_export):
        """Test that preset 'fast' is used for encoding."""
        data = setup_clip_export

        data["exporter"]._export_single_clip(
            video_path=data["video_path"],
            clip=data["clip"],
            video_name="test_video",
            output_dir=data["output_dir"],
            aspect_ratio=None,
            add_subtitles=False,
            transcript_path=None,
        )

        cmd = mock_subprocess_run.call_args[0][0]

        preset_index = cmd.index("-preset")
        assert cmd[preset_index + 1] == "fast"


# ============================================================================
# MAIN ENTRY POINT FOR RUNNING TESTS DIRECTLY
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
