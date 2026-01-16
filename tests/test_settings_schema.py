"""
Tests for src/config/settings_schema.py configuration system.

Covers:
- _validate_type() with valid/invalid values for str, bool, int, float
- SettingDefinition.validate_and_normalize() and validate_from_text()
- All normalizer functions (branding, clip generation, subtitle, export, output)
- validate_and_normalize_app_settings() function
- Helper functions: get_app_setting_definition(), get_app_settings_defaults(), etc.
- build_custom_subtitle_style() and get_effective_subtitle_style()
- StateManager.get_setting() and set_setting() integration
- JSON persistence round-trip via StateManager
"""

import json

import pytest

from src.config.settings_schema import (
    APP_SETTINGS,
    COLOR_MAP,
    NAMED_COLORS,
    SUBTITLE_PRESETS,
    SettingDefinition,
    SettingGroup,
    _hex_to_ass_color,
    _normalize_aspect_ratio,
    _normalize_auto_name_max_chars,
    _normalize_auto_name_method,
    _normalize_auto_name_word_count,
    _normalize_crf,
    _normalize_face_tracking_strategy,
    _normalize_ffmpeg_threads,
    _normalize_font_size,
    _normalize_logo_position,
    _normalize_logo_scale,
    _normalize_non_negative_int,
    _normalize_outline_width,
    _normalize_positive_float,
    _normalize_positive_int,
    _normalize_sample_rate,
    _normalize_shadow,
    _normalize_subtitle_color,
    _normalize_subtitle_mode,
    _normalize_subtitle_preset,
    _validate_type,
    build_custom_subtitle_style,
    get_app_setting_definition,
    get_app_settings_defaults,
    get_effective_subtitle_style,
    iter_app_setting_groups,
    iter_app_settings,
    list_app_settings_by_group,
    validate_and_normalize_app_settings,
)

# ============================================================================
# _validate_type() tests
# ============================================================================


class TestValidateType:
    """Tests for the _validate_type() function."""

    def test_validate_str_valid(self):
        """Valid string values are returned as strings."""
        assert _validate_type("hello", str) == "hello"
        assert _validate_type("", str) == ""
        assert _validate_type(None, str) == ""

    def test_validate_str_from_number(self):
        """Numbers are converted to strings."""
        assert _validate_type(123, str) == "123"
        assert _validate_type(3.14, str) == "3.14"

    def test_validate_bool_valid(self):
        """Valid boolean values are returned correctly."""
        assert _validate_type(True, bool) is True
        assert _validate_type(False, bool) is False
        assert _validate_type(1, bool) is True
        assert _validate_type(0, bool) is False
        assert _validate_type(None, bool) is False

    def test_validate_bool_from_string(self):
        """String representations of booleans are converted."""
        assert _validate_type("true", bool) is True
        assert _validate_type("True", bool) is True
        assert _validate_type("yes", bool) is True
        assert _validate_type("1", bool) is True
        assert _validate_type("on", bool) is True
        assert _validate_type("false", bool) is False
        assert _validate_type("False", bool) is False
        assert _validate_type("no", bool) is False
        assert _validate_type("0", bool) is False
        assert _validate_type("off", bool) is False

    def test_validate_bool_invalid(self):
        """Invalid boolean strings raise ValueError."""
        with pytest.raises(ValueError):
            _validate_type("maybe", bool)
        with pytest.raises(ValueError):
            _validate_type("2", bool)

    def test_validate_int_valid(self):
        """Valid integer values are returned correctly."""
        assert _validate_type(42, int) == 42
        assert _validate_type("42", int) == 42
        assert _validate_type(-10, int) == -10
        assert _validate_type(0, int) == 0

    def test_validate_int_invalid(self):
        """Invalid integer values raise ValueError."""
        with pytest.raises(ValueError):
            _validate_type("not_a_number", int)
        with pytest.raises(ValueError):
            _validate_type("3.14", int)

    def test_validate_float_valid(self):
        """Valid float values are returned correctly."""
        assert _validate_type(3.14, float) == 3.14
        assert _validate_type("3.14", float) == 3.14
        assert _validate_type(42, float) == 42.0
        assert _validate_type(-1.5, float) == -1.5

    def test_validate_float_invalid(self):
        """Invalid float values raise ValueError."""
        with pytest.raises(ValueError):
            _validate_type("not_a_number", float)


# ============================================================================
# SettingDefinition tests
# ============================================================================


class TestSettingDefinition:
    """Tests for SettingDefinition class methods."""

    def test_validate_and_normalize_no_normalizer(self):
        """Values are type-validated when no normalizer is provided."""
        definition = SettingDefinition(
            key="test_str",
            group="test",
            label="Test String",
            python_type=str,
            default="default_value",
        )
        assert definition.validate_and_normalize("hello") == "hello"
        assert definition.validate_and_normalize("") == ""

    def test_validate_and_normalize_with_normalizer(self):
        """Normalizer is applied after type validation."""
        definition = SettingDefinition(
            key="test_int",
            group="test",
            label="Test Int",
            python_type=int,
            default=1,
            normalize=_normalize_positive_int,
        )
        assert definition.validate_and_normalize(5) == 5
        assert definition.validate_and_normalize("10") == 10
        with pytest.raises(ValueError, match="positive"):
            definition.validate_and_normalize(0)

    def test_validate_from_text_string(self):
        """String values are passed through correctly."""
        definition = SettingDefinition(
            key="test_str",
            group="test",
            label="Test",
            python_type=str,
            default="default",
        )
        assert definition.validate_from_text("hello") == "hello"
        assert definition.validate_from_text("") == ""
        assert definition.validate_from_text(None) == ""

    def test_validate_from_text_bool(self):
        """Boolean text values are parsed correctly."""
        definition = SettingDefinition(
            key="test_bool",
            group="test",
            label="Test",
            python_type=bool,
            default=False,
        )
        assert definition.validate_from_text("true") is True
        assert definition.validate_from_text("yes") is True
        assert definition.validate_from_text("1") is True
        assert definition.validate_from_text("false") is False
        assert definition.validate_from_text("no") is False
        assert definition.validate_from_text("0") is False
        # Empty string returns default
        assert definition.validate_from_text("") is False
        with pytest.raises(ValueError, match="boolean"):
            definition.validate_from_text("maybe")

    def test_validate_from_text_int(self):
        """Integer text values are parsed correctly."""
        definition = SettingDefinition(
            key="test_int",
            group="test",
            label="Test",
            python_type=int,
            default=42,
        )
        assert definition.validate_from_text("10") == 10
        assert definition.validate_from_text("-5") == -5
        # Empty string returns default
        assert definition.validate_from_text("") == 42
        with pytest.raises(ValueError, match="integer"):
            definition.validate_from_text("not_int")

    def test_validate_from_text_float(self):
        """Float text values are parsed correctly."""
        definition = SettingDefinition(
            key="test_float",
            group="test",
            label="Test",
            python_type=float,
            default=1.0,
        )
        assert definition.validate_from_text("3.14") == 3.14
        assert definition.validate_from_text("-2.5") == -2.5
        # Empty string returns default
        assert definition.validate_from_text("") == 1.0
        with pytest.raises(ValueError, match="number"):
            definition.validate_from_text("not_float")


# ============================================================================
# Branding normalizers
# ============================================================================


class TestBrandingNormalizers:
    """Tests for branding-related normalizer functions."""

    def test_normalize_logo_position_valid(self):
        """Valid logo positions are normalized to lowercase."""
        assert _normalize_logo_position("top-right") == "top-right"
        assert _normalize_logo_position("TOP-LEFT") == "top-left"
        assert _normalize_logo_position("  bottom-right  ") == "bottom-right"
        assert _normalize_logo_position("BOTTOM-LEFT") == "bottom-left"

    def test_normalize_logo_position_invalid(self):
        """Invalid logo positions raise ValueError."""
        with pytest.raises(ValueError, match="Must be one of"):
            _normalize_logo_position("center")
        with pytest.raises(ValueError, match="Must be one of"):
            _normalize_logo_position("invalid")

    def test_normalize_logo_scale_valid(self):
        """Valid logo scales pass through."""
        assert _normalize_logo_scale(0.1) == 0.1
        assert _normalize_logo_scale(0.01) == 0.01
        assert _normalize_logo_scale(1.0) == 1.0
        assert _normalize_logo_scale(0.5) == 0.5

    def test_normalize_logo_scale_invalid(self):
        """Logo scales outside 0.01-1.0 raise ValueError."""
        with pytest.raises(ValueError, match="0.01 and 1.0"):
            _normalize_logo_scale(0.001)
        with pytest.raises(ValueError, match="0.01 and 1.0"):
            _normalize_logo_scale(1.5)
        with pytest.raises(ValueError, match="0.01 and 1.0"):
            _normalize_logo_scale(-0.1)


# ============================================================================
# Clip generation normalizers
# ============================================================================


class TestClipGenerationNormalizers:
    """Tests for clip generation normalizer functions."""

    def test_normalize_positive_int_valid(self):
        """Positive integers pass through."""
        assert _normalize_positive_int(1) == 1
        assert _normalize_positive_int(100) == 100

    def test_normalize_positive_int_invalid(self):
        """Non-positive integers raise ValueError."""
        with pytest.raises(ValueError, match="positive integer"):
            _normalize_positive_int(0)
        with pytest.raises(ValueError, match="positive integer"):
            _normalize_positive_int(-5)

    def test_normalize_non_negative_int_valid(self):
        """Non-negative integers pass through."""
        assert _normalize_non_negative_int(0) == 0
        assert _normalize_non_negative_int(10) == 10

    def test_normalize_non_negative_int_invalid(self):
        """Negative integers raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            _normalize_non_negative_int(-1)


# ============================================================================
# Subtitle normalizers
# ============================================================================


class TestSubtitleNormalizers:
    """Tests for subtitle-related normalizer functions."""

    def test_normalize_subtitle_mode_valid(self):
        """Valid subtitle modes are normalized."""
        assert _normalize_subtitle_mode("preset") == "preset"
        assert _normalize_subtitle_mode("CUSTOM") == "custom"
        assert _normalize_subtitle_mode("  Preset  ") == "preset"

    def test_normalize_subtitle_mode_invalid(self):
        """Invalid subtitle modes raise ValueError."""
        with pytest.raises(ValueError, match="preset.*custom"):
            _normalize_subtitle_mode("invalid")

    def test_normalize_subtitle_preset_valid(self):
        """Valid presets are normalized."""
        for preset in SUBTITLE_PRESETS:
            assert _normalize_subtitle_preset(preset) == preset
            assert _normalize_subtitle_preset(preset.upper()) == preset

    def test_normalize_subtitle_preset_invalid(self):
        """Invalid presets raise ValueError."""
        with pytest.raises(ValueError, match="Must be one of"):
            _normalize_subtitle_preset("nonexistent")

    def test_normalize_subtitle_color_named(self):
        """Named colors are recognized."""
        for color in NAMED_COLORS:
            assert _normalize_subtitle_color(color) == color
            assert _normalize_subtitle_color(color.upper()) == color

    def test_normalize_subtitle_color_hex(self):
        """Hex colors are validated."""
        assert _normalize_subtitle_color("#FF0000") == "#ff0000"
        assert _normalize_subtitle_color("#00ff00") == "#00ff00"
        assert _normalize_subtitle_color("#0000FF") == "#0000ff"

    def test_normalize_subtitle_color_invalid(self):
        """Invalid colors raise ValueError."""
        with pytest.raises(ValueError, match="color name.*hex"):
            _normalize_subtitle_color("orange")  # Not in NAMED_COLORS
        with pytest.raises(ValueError, match="color name.*hex"):
            _normalize_subtitle_color("#GGG")  # Invalid hex
        with pytest.raises(ValueError, match="color name.*hex"):
            _normalize_subtitle_color("#12345")  # Wrong length

    def test_normalize_font_size_valid(self):
        """Valid font sizes pass through."""
        assert _normalize_font_size(8) == 8
        assert _normalize_font_size(72) == 72
        assert _normalize_font_size(18) == 18

    def test_normalize_font_size_invalid(self):
        """Font sizes outside 8-72 raise ValueError."""
        with pytest.raises(ValueError, match="8 and 72"):
            _normalize_font_size(7)
        with pytest.raises(ValueError, match="8 and 72"):
            _normalize_font_size(73)

    def test_normalize_outline_width_valid(self):
        """Valid outline widths pass through."""
        assert _normalize_outline_width(0) == 0
        assert _normalize_outline_width(10) == 10
        assert _normalize_outline_width(5) == 5

    def test_normalize_outline_width_invalid(self):
        """Outline widths outside 0-10 raise ValueError."""
        with pytest.raises(ValueError, match="0 and 10"):
            _normalize_outline_width(-1)
        with pytest.raises(ValueError, match="0 and 10"):
            _normalize_outline_width(11)

    def test_normalize_shadow_valid(self):
        """Valid shadow depths pass through."""
        assert _normalize_shadow(0) == 0
        assert _normalize_shadow(5) == 5
        assert _normalize_shadow(3) == 3

    def test_normalize_shadow_invalid(self):
        """Shadow depths outside 0-5 raise ValueError."""
        with pytest.raises(ValueError, match="0 and 5"):
            _normalize_shadow(-1)
        with pytest.raises(ValueError, match="0 and 5"):
            _normalize_shadow(6)


# ============================================================================
# Export normalizers
# ============================================================================


class TestExportNormalizers:
    """Tests for export-related normalizer functions."""

    def test_normalize_aspect_ratio_valid(self):
        """Valid aspect ratios pass through."""
        assert _normalize_aspect_ratio("16:9") == "16:9"
        assert _normalize_aspect_ratio("9:16") == "9:16"
        assert _normalize_aspect_ratio("1:1") == "1:1"
        assert _normalize_aspect_ratio("4:3") == "4:3"
        assert _normalize_aspect_ratio("3:4") == "3:4"
        assert _normalize_aspect_ratio("") == ""
        assert _normalize_aspect_ratio("  ") == ""

    def test_normalize_aspect_ratio_invalid(self):
        """Invalid aspect ratios raise ValueError."""
        with pytest.raises(ValueError, match="Must be one of"):
            _normalize_aspect_ratio("2:1")
        with pytest.raises(ValueError, match="Must be one of"):
            _normalize_aspect_ratio("invalid")

    def test_normalize_crf_valid(self):
        """Valid CRF values pass through."""
        assert _normalize_crf(0) == 0
        assert _normalize_crf(51) == 51
        assert _normalize_crf(23) == 23

    def test_normalize_crf_invalid(self):
        """CRF values outside 0-51 raise ValueError."""
        with pytest.raises(ValueError, match="0 and 51"):
            _normalize_crf(-1)
        with pytest.raises(ValueError, match="0 and 51"):
            _normalize_crf(52)

    def test_normalize_face_tracking_strategy_valid(self):
        """Valid strategies are normalized."""
        assert _normalize_face_tracking_strategy("keep_in_frame") == "keep_in_frame"
        assert _normalize_face_tracking_strategy("CENTERED") == "centered"
        assert _normalize_face_tracking_strategy("  Keep_In_Frame  ") == "keep_in_frame"

    def test_normalize_face_tracking_strategy_invalid(self):
        """Invalid strategies raise ValueError."""
        with pytest.raises(ValueError, match="keep_in_frame.*centered"):
            _normalize_face_tracking_strategy("invalid")

    def test_normalize_sample_rate_valid(self):
        """Valid sample rates pass through."""
        assert _normalize_sample_rate(1) == 1
        assert _normalize_sample_rate(30) == 30
        assert _normalize_sample_rate(3) == 3

    def test_normalize_sample_rate_invalid(self):
        """Sample rates outside 1-30 raise ValueError."""
        with pytest.raises(ValueError, match="1 and 30"):
            _normalize_sample_rate(0)
        with pytest.raises(ValueError, match="1 and 30"):
            _normalize_sample_rate(31)

    def test_normalize_ffmpeg_threads_valid(self):
        """Valid thread counts pass through."""
        assert _normalize_ffmpeg_threads(0) == 0
        assert _normalize_ffmpeg_threads(64) == 64
        assert _normalize_ffmpeg_threads(-16) == -16
        assert _normalize_ffmpeg_threads(7) == 7

    def test_normalize_ffmpeg_threads_invalid(self):
        """Thread counts outside -16 to 64 raise ValueError."""
        with pytest.raises(ValueError, match="-16 and 64"):
            _normalize_ffmpeg_threads(-17)
        with pytest.raises(ValueError, match="-16 and 64"):
            _normalize_ffmpeg_threads(65)


# ============================================================================
# Output normalizers
# ============================================================================


class TestOutputNormalizers:
    """Tests for output/naming normalizer functions."""

    def test_normalize_auto_name_method_valid(self):
        """Valid naming methods are normalized."""
        assert _normalize_auto_name_method("filename") == "filename"
        assert _normalize_auto_name_method("FIRST_WORDS") == "first_words"
        assert _normalize_auto_name_method("  llm_summary  ") == "llm_summary"

    def test_normalize_auto_name_method_invalid(self):
        """Invalid naming methods raise ValueError."""
        with pytest.raises(ValueError, match="Must be one of"):
            _normalize_auto_name_method("invalid")

    def test_normalize_auto_name_word_count_valid(self):
        """Valid word counts pass through."""
        assert _normalize_auto_name_word_count(1) == 1
        assert _normalize_auto_name_word_count(15) == 15
        assert _normalize_auto_name_word_count(5) == 5

    def test_normalize_auto_name_word_count_invalid(self):
        """Word counts outside 1-15 raise ValueError."""
        with pytest.raises(ValueError, match="1 and 15"):
            _normalize_auto_name_word_count(0)
        with pytest.raises(ValueError, match="1 and 15"):
            _normalize_auto_name_word_count(16)

    def test_normalize_auto_name_max_chars_valid(self):
        """Valid max char limits pass through."""
        assert _normalize_auto_name_max_chars(10) == 10
        assert _normalize_auto_name_max_chars(100) == 100
        assert _normalize_auto_name_max_chars(40) == 40

    def test_normalize_auto_name_max_chars_invalid(self):
        """Max chars outside 10-100 raise ValueError."""
        with pytest.raises(ValueError, match="10 and 100"):
            _normalize_auto_name_max_chars(9)
        with pytest.raises(ValueError, match="10 and 100"):
            _normalize_auto_name_max_chars(101)


# ============================================================================
# validate_and_normalize_app_settings() tests
# ============================================================================


class TestValidateAndNormalizeAppSettings:
    """Tests for validate_and_normalize_app_settings() function."""

    def test_empty_settings_returns_defaults(self):
        """Empty settings dict returns all defaults."""
        validated, errors = validate_and_normalize_app_settings({})
        assert errors == {}
        defaults = get_app_settings_defaults()
        for key, default_value in defaults.items():
            assert key in validated

    def test_valid_settings_pass_through(self):
        """Valid settings are preserved after validation."""
        settings = {
            "min_clip_duration": 45,
            "max_clip_duration": 120,
            "subtitle_style_mode": "custom",
            "video_crf": 18,
        }
        validated, errors = validate_and_normalize_app_settings(settings)
        assert errors == {}
        assert validated["min_clip_duration"] == 45
        assert validated["max_clip_duration"] == 120
        assert validated["subtitle_style_mode"] == "custom"
        assert validated["video_crf"] == 18

    def test_invalid_settings_return_errors_and_defaults(self):
        """Invalid settings are reset to defaults with error messages."""
        settings = {
            "min_clip_duration": -5,  # Invalid: must be positive
            "video_crf": 100,  # Invalid: must be 0-51
            "subtitle_style_mode": "invalid_mode",  # Invalid
        }
        validated, errors = validate_and_normalize_app_settings(settings)
        # Should have errors for invalid keys
        assert "min_clip_duration" in errors
        assert "video_crf" in errors
        assert "subtitle_style_mode" in errors
        # Values should be reset to defaults
        defaults = get_app_settings_defaults()
        assert validated["min_clip_duration"] == defaults["min_clip_duration"]
        assert validated["video_crf"] == defaults["video_crf"]
        assert validated["subtitle_style_mode"] == defaults["subtitle_style_mode"]

    def test_unknown_keys_preserved(self):
        """Unknown keys are preserved as-is."""
        settings = {
            "custom_unknown_key": "custom_value",
            "another_custom": 42,
        }
        validated, errors = validate_and_normalize_app_settings(settings)
        assert errors == {}
        assert validated["custom_unknown_key"] == "custom_value"
        assert validated["another_custom"] == 42

    def test_mixed_valid_invalid_settings(self):
        """Mix of valid and invalid settings is handled correctly."""
        settings = {
            "min_clip_duration": 30,  # Valid
            "max_clip_duration": -10,  # Invalid
            "subtitle_preset": "bold",  # Valid
        }
        validated, errors = validate_and_normalize_app_settings(settings)
        assert "max_clip_duration" in errors
        assert "min_clip_duration" not in errors
        assert "subtitle_preset" not in errors
        assert validated["min_clip_duration"] == 30
        assert validated["subtitle_preset"] == "bold"


# ============================================================================
# Helper function tests
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_app_setting_definition_exists(self):
        """Returns definition for known settings."""
        definition = get_app_setting_definition("min_clip_duration")
        assert definition is not None
        assert definition.key == "min_clip_duration"
        assert definition.python_type is int

    def test_get_app_setting_definition_not_exists(self):
        """Returns None for unknown settings."""
        definition = get_app_setting_definition("nonexistent_key")
        assert definition is None

    def test_get_app_settings_defaults(self):
        """Returns dict of all default values."""
        defaults = get_app_settings_defaults()
        assert isinstance(defaults, dict)
        assert len(defaults) == len(APP_SETTINGS)
        for setting in APP_SETTINGS:
            assert setting.key in defaults
            assert defaults[setting.key] == setting.default

    def test_iter_app_settings(self):
        """Returns sequence of all settings."""
        settings = iter_app_settings()
        assert len(settings) == len(APP_SETTINGS)
        for i, setting in enumerate(settings):
            assert isinstance(setting, SettingDefinition)
            assert setting == APP_SETTINGS[i]

    def test_iter_app_setting_groups(self):
        """Returns sequence of all groups."""
        groups = iter_app_setting_groups()
        assert len(groups) > 0
        for group in groups:
            assert isinstance(group, SettingGroup)

    def test_list_app_settings_by_group(self):
        """Returns settings organized by group."""
        grouped = list_app_settings_by_group()
        assert isinstance(grouped, dict)
        # All settings should be accounted for
        total = sum(len(settings) for settings in grouped.values())
        assert total == len(APP_SETTINGS)


# ============================================================================
# Subtitle style helper tests
# ============================================================================


class TestSubtitleStyleHelpers:
    """Tests for subtitle style helper functions."""

    def test_hex_to_ass_color(self):
        """Hex colors are converted to ASS format correctly."""
        assert _hex_to_ass_color("#FF0000") == "&H000000FF"  # Red
        assert _hex_to_ass_color("#00FF00") == "&H0000FF00"  # Green
        assert _hex_to_ass_color("#0000FF") == "&H00FF0000"  # Blue
        assert _hex_to_ass_color("#FFFFFF") == "&H00FFFFFF"  # White
        assert _hex_to_ass_color("#000000") == "&H00000000"  # Black

    def test_build_custom_subtitle_style_defaults(self):
        """Default settings produce expected style dict."""
        settings = {
            "subtitle_font_family": "Arial",
            "subtitle_font_size": 18,
            "subtitle_primary_color": "yellow",
            "subtitle_outline_color": "black",
            "subtitle_outline_width": 2,
            "subtitle_shadow": 1,
            "subtitle_bold": False,
        }
        style = build_custom_subtitle_style(settings)
        assert style["FontName"] == "Arial"
        assert style["FontSize"] == "18"
        assert style["PrimaryColour"] == COLOR_MAP["yellow"]
        assert style["OutlineColour"] == COLOR_MAP["black"]
        assert style["Outline"] == "2"
        assert style["Shadow"] == "1"
        assert style["Bold"] == "0"

    def test_build_custom_subtitle_style_hex_colors(self):
        """Hex colors are converted correctly in style dict."""
        settings = {
            "subtitle_primary_color": "#FF0000",
            "subtitle_outline_color": "#00FF00",
        }
        style = build_custom_subtitle_style(settings)
        assert style["PrimaryColour"] == "&H000000FF"  # Red in ASS
        assert style["OutlineColour"] == "&H0000FF00"  # Green in ASS

    def test_build_custom_subtitle_style_bold(self):
        """Bold setting is converted correctly."""
        settings = {"subtitle_bold": True}
        style = build_custom_subtitle_style(settings)
        assert style["Bold"] == "-1"

        settings = {"subtitle_bold": False}
        style = build_custom_subtitle_style(settings)
        assert style["Bold"] == "0"

    def test_get_effective_subtitle_style_preset_mode(self):
        """Preset mode returns the preset name."""
        settings = {
            "subtitle_style_mode": "preset",
            "subtitle_preset": "bold",
        }
        assert get_effective_subtitle_style(settings) == "bold"

    def test_get_effective_subtitle_style_custom_mode(self):
        """Custom mode returns '__custom__' marker."""
        settings = {
            "subtitle_style_mode": "custom",
            "subtitle_preset": "bold",  # Ignored in custom mode
        }
        assert get_effective_subtitle_style(settings) == "__custom__"

    def test_get_effective_subtitle_style_default(self):
        """Missing mode defaults to preset."""
        settings = {}
        assert get_effective_subtitle_style(settings) == "default"


# ============================================================================
# StateManager integration tests
# ============================================================================


class TestStateManagerSettings:
    """Tests for StateManager.get_setting() and set_setting() integration."""

    def test_get_setting_returns_default_for_known_key(self, tmp_project_dir):
        """get_setting() returns schema default for known keys not in storage."""
        from src.utils.state_manager import StateManager

        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=tmp_project_dir / "config" / "test_settings.json",
        )
        # Known key with default from schema
        default = get_app_setting_definition("min_clip_duration").default
        assert sm.get_setting("min_clip_duration") == default

    def test_get_setting_returns_explicit_default(self, tmp_project_dir):
        """get_setting() returns explicit default when provided."""
        from src.utils.state_manager import StateManager

        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=tmp_project_dir / "config" / "test_settings.json",
        )
        # Unknown key with explicit default
        assert sm.get_setting("unknown_key", "fallback") == "fallback"

    def test_get_setting_returns_stored_value(self, tmp_project_dir):
        """get_setting() returns value from storage when available."""
        from src.utils.state_manager import StateManager

        # Pre-populate settings file
        settings_file = tmp_project_dir / "config" / "test_settings.json"
        settings_file.write_text(
            json.dumps({"min_clip_duration": 45}), encoding="utf-8"
        )

        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )
        assert sm.get_setting("min_clip_duration") == 45

    def test_set_setting_validates_known_key(self, tmp_project_dir):
        """set_setting() validates and normalizes known keys."""
        from src.utils.state_manager import StateManager

        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=tmp_project_dir / "config" / "test_settings.json",
        )
        # Valid value
        sm.set_setting("min_clip_duration", 60)
        assert sm.get_setting("min_clip_duration") == 60

        # Invalid value raises error
        with pytest.raises(ValueError):
            sm.set_setting("min_clip_duration", -10)

    def test_set_setting_accepts_unknown_key(self, tmp_project_dir):
        """set_setting() stores unknown keys without validation."""
        from src.utils.state_manager import StateManager

        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=tmp_project_dir / "config" / "test_settings.json",
        )
        sm.set_setting("custom_key", "custom_value")
        assert sm.get_setting("custom_key") == "custom_value"

    def test_set_setting_persists_to_file(self, tmp_project_dir):
        """set_setting() saves values to JSON file."""
        from src.utils.state_manager import StateManager

        settings_file = tmp_project_dir / "config" / "test_settings.json"
        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )
        sm.set_setting("video_crf", 18)

        # Read file directly to verify persistence
        with open(settings_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["video_crf"] == 18


# ============================================================================
# JSON persistence round-trip tests
# ============================================================================


class TestJSONPersistence:
    """Tests for JSON persistence round-trips."""

    def test_settings_persist_and_reload(self, tmp_project_dir):
        """Settings survive StateManager reload."""
        from src.utils.state_manager import StateManager

        settings_file = tmp_project_dir / "config" / "test_settings.json"

        # Create first instance and set values
        sm1 = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )
        sm1.set_setting("min_clip_duration", 45)
        sm1.set_setting("max_clip_duration", 120)
        sm1.set_setting("subtitle_style_mode", "custom")
        sm1.set_setting("video_crf", 18)
        sm1.set_setting("custom_key", {"nested": "value"})

        # Create second instance (simulating restart)
        sm2 = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )

        # Verify values persisted
        assert sm2.get_setting("min_clip_duration") == 45
        assert sm2.get_setting("max_clip_duration") == 120
        assert sm2.get_setting("subtitle_style_mode") == "custom"
        assert sm2.get_setting("video_crf") == 18
        assert sm2.get_setting("custom_key") == {"nested": "value"}

    def test_invalid_persisted_values_reset_to_defaults(self, tmp_project_dir):
        """Invalid persisted values are reset to defaults on load."""
        from src.utils.state_manager import StateManager

        settings_file = tmp_project_dir / "config" / "test_settings.json"

        # Write invalid values directly to file
        invalid_settings = {
            "min_clip_duration": -100,  # Invalid
            "video_crf": 999,  # Invalid
            "max_clip_duration": 60,  # Valid
        }
        settings_file.write_text(json.dumps(invalid_settings), encoding="utf-8")

        # Load StateManager (should validate and fix)
        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )

        # Invalid values should be reset to defaults
        defaults = get_app_settings_defaults()
        assert sm.get_setting("min_clip_duration") == defaults["min_clip_duration"]
        assert sm.get_setting("video_crf") == defaults["video_crf"]
        # Valid value should be preserved
        assert sm.get_setting("max_clip_duration") == 60

    def test_corrupted_json_starts_fresh(self, tmp_project_dir):
        """Corrupted JSON file results in fresh settings."""
        from src.utils.state_manager import StateManager

        settings_file = tmp_project_dir / "config" / "test_settings.json"

        # Write corrupted JSON
        settings_file.write_text("{ invalid json }", encoding="utf-8")

        # Load StateManager (should handle gracefully)
        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )

        # Should have defaults
        defaults = get_app_settings_defaults()
        assert sm.get_setting("min_clip_duration") == defaults["min_clip_duration"]

    def test_all_setting_categories_persist(self, tmp_project_dir):
        """Settings from all categories persist correctly."""
        from src.utils.state_manager import StateManager

        settings_file = tmp_project_dir / "config" / "test_settings.json"

        sm = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )

        # Set values from different categories (skip logo_path which requires file validation)
        sm.set_setting("logo_position", "bottom-left")  # branding
        sm.set_setting("logo_scale", 0.15)  # branding
        sm.set_setting("min_clip_duration", 45)  # clip_generation
        sm.set_setting("max_clips", 15)  # clip_generation
        sm.set_setting("subtitle_preset", "tiktok")  # subtitles
        sm.set_setting("subtitle_font_size", 24)  # subtitles
        sm.set_setting("video_crf", 20)  # export
        sm.set_setting("enable_face_tracking", True)  # export
        sm.set_setting("auto_name_method", "first_words")  # output

        # Reload and verify
        sm2 = StateManager(
            state_file=str(tmp_project_dir / "temp" / "project_state.json"),
            app_root=tmp_project_dir,
            settings_file=settings_file,
        )

        assert sm2.get_setting("logo_position") == "bottom-left"
        assert sm2.get_setting("logo_scale") == 0.15
        assert sm2.get_setting("min_clip_duration") == 45
        assert sm2.get_setting("max_clips") == 15
        assert sm2.get_setting("subtitle_preset") == "tiktok"
        assert sm2.get_setting("subtitle_font_size") == 24
        assert sm2.get_setting("video_crf") == 20
        assert sm2.get_setting("enable_face_tracking") is True
        assert sm2.get_setting("auto_name_method") == "first_words"


# ============================================================================
# Positive float normalizer test
# ============================================================================


class TestPositiveFloatNormalizer:
    """Tests for _normalize_positive_float function."""

    def test_normalize_positive_float_valid(self):
        """Positive floats pass through."""
        assert _normalize_positive_float(0.1) == 0.1
        assert _normalize_positive_float(5.0) == 5.0
        assert _normalize_positive_float(0.001) == 0.001

    def test_normalize_positive_float_invalid(self):
        """Zero and negative floats raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            _normalize_positive_float(0.0)
        with pytest.raises(ValueError, match="positive"):
            _normalize_positive_float(-1.5)
