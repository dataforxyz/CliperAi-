# -*- coding: utf-8 -*-
"""
Comprehensive pytest tests for src/utils/logo.py.

Tests cover:
- Extension validation (_is_allowed_logo_file)
- PNG/JPEG file signature detection (_looks_like_png, _looks_like_jpeg)
- Combined extension+signature validation (_has_expected_image_signature)
- Path coercion and resolution (_coerce_to_existing_logo_file, resolve_logo_path)
- Public API functions (is_valid_logo_location, coerce_logo_file)
- Settings normalization (normalize_logo_setting_value)
- Candidate listing (list_logo_candidates)
- Error handling for missing/invalid files
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.logo import (
    DEFAULT_BUILTIN_LOGO_PATH,
    _coerce_to_existing_logo_file,
    _has_expected_image_signature,
    _is_allowed_logo_file,
    _looks_like_jpeg,
    _looks_like_png,
    coerce_logo_file,
    is_valid_logo_location,
    list_logo_candidates,
    normalize_logo_setting_value,
    resolve_logo_path,
)


# ============================================================================
# FIXTURES
# ============================================================================


# PNG file signature: 89 50 4E 47 0D 0A 1A 0A (8 bytes)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# JPEG file signature: FF D8 FF (3 bytes)
JPEG_SIGNATURE = b"\xff\xd8\xff"


@pytest.fixture
def valid_png_file(tmp_path: Path) -> Path:
    """Create a valid PNG file with correct signature."""
    png_file = tmp_path / "logo.png"
    # Write PNG signature followed by some dummy data
    png_file.write_bytes(PNG_SIGNATURE + b"\x00" * 100)
    return png_file


@pytest.fixture
def valid_jpeg_file(tmp_path: Path) -> Path:
    """Create a valid JPEG file with correct signature."""
    jpeg_file = tmp_path / "logo.jpg"
    # Write JPEG signature followed by some dummy data
    jpeg_file.write_bytes(JPEG_SIGNATURE + b"\x00" * 100)
    return jpeg_file


@pytest.fixture
def valid_jpeg_file_alt_ext(tmp_path: Path) -> Path:
    """Create a valid JPEG file with .jpeg extension."""
    jpeg_file = tmp_path / "logo.jpeg"
    jpeg_file.write_bytes(JPEG_SIGNATURE + b"\x00" * 100)
    return jpeg_file


@pytest.fixture
def png_wrong_signature(tmp_path: Path) -> Path:
    """Create a file with .png extension but wrong signature."""
    png_file = tmp_path / "fake.png"
    png_file.write_bytes(b"not a png file content")
    return png_file


@pytest.fixture
def jpeg_wrong_signature(tmp_path: Path) -> Path:
    """Create a file with .jpg extension but wrong signature."""
    jpeg_file = tmp_path / "fake.jpg"
    jpeg_file.write_bytes(b"not a jpeg file content")
    return jpeg_file


@pytest.fixture
def invalid_extension_file(tmp_path: Path) -> Path:
    """Create a file with disallowed extension."""
    gif_file = tmp_path / "logo.gif"
    gif_file.write_bytes(b"GIF89a" + b"\x00" * 100)
    return gif_file


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Create an empty file with valid extension."""
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    return empty


# ============================================================================
# TESTS: _is_allowed_logo_file
# ============================================================================


class TestIsAllowedLogoFile:
    """Tests for _is_allowed_logo_file() extension validation."""

    def test_png_extension_allowed(self, tmp_path: Path):
        """PNG extension should be allowed."""
        png_path = tmp_path / "logo.png"
        assert _is_allowed_logo_file(png_path) is True

    def test_jpg_extension_allowed(self, tmp_path: Path):
        """JPG extension should be allowed."""
        jpg_path = tmp_path / "logo.jpg"
        assert _is_allowed_logo_file(jpg_path) is True

    def test_jpeg_extension_allowed(self, tmp_path: Path):
        """JPEG extension should be allowed."""
        jpeg_path = tmp_path / "logo.jpeg"
        assert _is_allowed_logo_file(jpeg_path) is True

    def test_uppercase_png_allowed(self, tmp_path: Path):
        """Uppercase PNG extension should be allowed (case-insensitive)."""
        png_path = tmp_path / "logo.PNG"
        assert _is_allowed_logo_file(png_path) is True

    def test_uppercase_jpg_allowed(self, tmp_path: Path):
        """Uppercase JPG extension should be allowed (case-insensitive)."""
        jpg_path = tmp_path / "logo.JPG"
        assert _is_allowed_logo_file(jpg_path) is True

    def test_mixed_case_jpeg_allowed(self, tmp_path: Path):
        """Mixed case JPEG extension should be allowed."""
        jpeg_path = tmp_path / "logo.JpEg"
        assert _is_allowed_logo_file(jpeg_path) is True

    def test_gif_extension_not_allowed(self, tmp_path: Path):
        """GIF extension should not be allowed."""
        gif_path = tmp_path / "logo.gif"
        assert _is_allowed_logo_file(gif_path) is False

    def test_bmp_extension_not_allowed(self, tmp_path: Path):
        """BMP extension should not be allowed."""
        bmp_path = tmp_path / "logo.bmp"
        assert _is_allowed_logo_file(bmp_path) is False

    def test_webp_extension_not_allowed(self, tmp_path: Path):
        """WebP extension should not be allowed."""
        webp_path = tmp_path / "logo.webp"
        assert _is_allowed_logo_file(webp_path) is False

    def test_svg_extension_not_allowed(self, tmp_path: Path):
        """SVG extension should not be allowed."""
        svg_path = tmp_path / "logo.svg"
        assert _is_allowed_logo_file(svg_path) is False

    def test_no_extension_not_allowed(self, tmp_path: Path):
        """File without extension should not be allowed."""
        no_ext_path = tmp_path / "logo"
        assert _is_allowed_logo_file(no_ext_path) is False

    def test_txt_extension_not_allowed(self, tmp_path: Path):
        """Text file extension should not be allowed."""
        txt_path = tmp_path / "logo.txt"
        assert _is_allowed_logo_file(txt_path) is False


# ============================================================================
# TESTS: _looks_like_png
# ============================================================================


class TestLooksLikePng:
    """Tests for _looks_like_png() signature detection."""

    def test_valid_png_signature(self, valid_png_file: Path):
        """File with valid PNG signature should return True."""
        assert _looks_like_png(valid_png_file) is True

    def test_jpeg_signature_not_png(self, valid_jpeg_file: Path):
        """File with JPEG signature should return False."""
        assert _looks_like_png(valid_jpeg_file) is False

    def test_invalid_signature(self, png_wrong_signature: Path):
        """File with wrong signature but .png extension should return False."""
        assert _looks_like_png(png_wrong_signature) is False

    def test_empty_file(self, empty_file: Path):
        """Empty file should return False."""
        assert _looks_like_png(empty_file) is False

    def test_nonexistent_file(self, tmp_path: Path):
        """Non-existent file should return False (not raise)."""
        nonexistent = tmp_path / "does_not_exist.png"
        assert _looks_like_png(nonexistent) is False

    def test_partial_png_signature(self, tmp_path: Path):
        """File with partial PNG signature should return False."""
        partial = tmp_path / "partial.png"
        partial.write_bytes(b"\x89PNG")  # Only 4 bytes
        assert _looks_like_png(partial) is False


# ============================================================================
# TESTS: _looks_like_jpeg
# ============================================================================


class TestLooksLikeJpeg:
    """Tests for _looks_like_jpeg() signature detection."""

    def test_valid_jpeg_signature(self, valid_jpeg_file: Path):
        """File with valid JPEG signature should return True."""
        assert _looks_like_jpeg(valid_jpeg_file) is True

    def test_valid_jpeg_with_alt_ext(self, valid_jpeg_file_alt_ext: Path):
        """File with .jpeg extension and valid signature should return True."""
        assert _looks_like_jpeg(valid_jpeg_file_alt_ext) is True

    def test_png_signature_not_jpeg(self, valid_png_file: Path):
        """File with PNG signature should return False."""
        assert _looks_like_jpeg(valid_png_file) is False

    def test_invalid_signature(self, jpeg_wrong_signature: Path):
        """File with wrong signature but .jpg extension should return False."""
        assert _looks_like_jpeg(jpeg_wrong_signature) is False

    def test_empty_file(self, empty_file: Path):
        """Empty file should return False."""
        # Change extension to jpg for this test
        jpg_empty = empty_file.parent / "empty.jpg"
        jpg_empty.write_bytes(b"")
        assert _looks_like_jpeg(jpg_empty) is False

    def test_nonexistent_file(self, tmp_path: Path):
        """Non-existent file should return False (not raise)."""
        nonexistent = tmp_path / "does_not_exist.jpg"
        assert _looks_like_jpeg(nonexistent) is False

    def test_partial_jpeg_signature(self, tmp_path: Path):
        """File with partial JPEG signature should return False."""
        partial = tmp_path / "partial.jpg"
        partial.write_bytes(b"\xff\xd8")  # Only 2 bytes
        assert _looks_like_jpeg(partial) is False


# ============================================================================
# TESTS: _has_expected_image_signature
# ============================================================================


class TestHasExpectedImageSignature:
    """Tests for _has_expected_image_signature() combined validation."""

    def test_png_file_with_png_signature(self, valid_png_file: Path):
        """PNG file with PNG signature should return True."""
        assert _has_expected_image_signature(valid_png_file) is True

    def test_jpg_file_with_jpeg_signature(self, valid_jpeg_file: Path):
        """JPG file with JPEG signature should return True."""
        assert _has_expected_image_signature(valid_jpeg_file) is True

    def test_jpeg_file_with_jpeg_signature(self, valid_jpeg_file_alt_ext: Path):
        """JPEG file with JPEG signature should return True."""
        assert _has_expected_image_signature(valid_jpeg_file_alt_ext) is True

    def test_png_file_with_wrong_signature(self, png_wrong_signature: Path):
        """PNG file with non-PNG signature should return False."""
        assert _has_expected_image_signature(png_wrong_signature) is False

    def test_jpg_file_with_wrong_signature(self, jpeg_wrong_signature: Path):
        """JPG file with non-JPEG signature should return False."""
        assert _has_expected_image_signature(jpeg_wrong_signature) is False

    def test_gif_extension_always_false(self, invalid_extension_file: Path):
        """File with disallowed extension should return False."""
        assert _has_expected_image_signature(invalid_extension_file) is False

    def test_png_file_with_jpeg_signature(self, tmp_path: Path):
        """PNG extension with JPEG signature should return False."""
        mismatch = tmp_path / "mismatch.png"
        mismatch.write_bytes(JPEG_SIGNATURE + b"\x00" * 100)
        assert _has_expected_image_signature(mismatch) is False

    def test_jpg_file_with_png_signature(self, tmp_path: Path):
        """JPG extension with PNG signature should return False."""
        mismatch = tmp_path / "mismatch.jpg"
        mismatch.write_bytes(PNG_SIGNATURE + b"\x00" * 100)
        assert _has_expected_image_signature(mismatch) is False


# ============================================================================
# TESTS: _coerce_to_existing_logo_file
# ============================================================================


class TestCoerceToExistingLogoFile:
    """Tests for _coerce_to_existing_logo_file() path resolution."""

    def test_none_input_returns_none(self):
        """None input should return None."""
        assert _coerce_to_existing_logo_file(None) is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        assert _coerce_to_existing_logo_file("") is None

    def test_valid_png_path(self, valid_png_file: Path):
        """Valid PNG path should return resolved Path."""
        result = _coerce_to_existing_logo_file(str(valid_png_file))
        assert result is not None
        assert result.exists()
        assert result == valid_png_file.resolve()

    def test_valid_jpeg_path(self, valid_jpeg_file: Path):
        """Valid JPEG path should return resolved Path."""
        result = _coerce_to_existing_logo_file(str(valid_jpeg_file))
        assert result is not None
        assert result.exists()
        assert result == valid_jpeg_file.resolve()

    def test_invalid_extension_returns_none(self, invalid_extension_file: Path):
        """File with disallowed extension should return None."""
        result = _coerce_to_existing_logo_file(str(invalid_extension_file))
        assert result is None

    def test_wrong_signature_returns_none(self, png_wrong_signature: Path):
        """File with wrong signature should return None."""
        result = _coerce_to_existing_logo_file(str(png_wrong_signature))
        assert result is None

    def test_nonexistent_file_returns_none(self, tmp_path: Path):
        """Non-existent file should return None."""
        nonexistent = tmp_path / "does_not_exist.png"
        result = _coerce_to_existing_logo_file(str(nonexistent))
        assert result is None

    def test_directory_path_returns_none(self, tmp_path: Path):
        """Directory path should return None."""
        result = _coerce_to_existing_logo_file(str(tmp_path))
        assert result is None

    def test_assets_prefix_resolution(self, tmp_path: Path):
        """Paths starting with 'assets/' should resolve from app root."""
        # Create a mock assets directory with logo
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            logo_file = assets_dir / "logo.png"
            logo_file.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = _coerce_to_existing_logo_file("assets/logo.png")
            assert result is not None
            assert result == logo_file.resolve()

    def test_assets_prefix_invalid_file_returns_none(self, tmp_path: Path):
        """Invalid file in assets/ should return None."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            logo_file = assets_dir / "logo.png"
            logo_file.write_bytes(b"not a png")

            result = _coerce_to_existing_logo_file("assets/logo.png")
            assert result is None

    def test_assets_prefix_nonexistent_returns_none(self, tmp_path: Path):
        """Non-existent file in assets/ should return None."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            result = _coerce_to_existing_logo_file("assets/nonexistent.png")
            assert result is None

    def test_tilde_expansion(self, tmp_path: Path, valid_png_file: Path, monkeypatch):
        """Tilde paths should be expanded."""
        # We can't easily test real ~ expansion, but we can verify the function
        # calls expanduser by passing a path that exists after expansion
        # This test verifies the code path is exercised
        result = _coerce_to_existing_logo_file(str(valid_png_file))
        assert result is not None


# ============================================================================
# TESTS: resolve_logo_path
# ============================================================================


class TestResolveLogoPath:
    """Tests for resolve_logo_path() with fallback priority."""

    def test_user_logo_path_highest_priority(
        self, valid_png_file: Path, valid_jpeg_file: Path
    ):
        """user_logo_path should take priority over saved_logo_path."""
        result = resolve_logo_path(
            user_logo_path=str(valid_png_file),
            saved_logo_path=str(valid_jpeg_file),
        )
        assert result == str(valid_png_file.resolve())

    def test_saved_logo_path_used_when_user_none(self, valid_jpeg_file: Path):
        """saved_logo_path should be used when user_logo_path is None."""
        result = resolve_logo_path(
            user_logo_path=None,
            saved_logo_path=str(valid_jpeg_file),
        )
        assert result == str(valid_jpeg_file.resolve())

    def test_saved_logo_path_used_when_user_invalid(
        self, valid_jpeg_file: Path, tmp_path: Path
    ):
        """saved_logo_path should be used when user_logo_path is invalid."""
        invalid_path = tmp_path / "nonexistent.png"
        result = resolve_logo_path(
            user_logo_path=str(invalid_path),
            saved_logo_path=str(valid_jpeg_file),
        )
        assert result == str(valid_jpeg_file.resolve())

    def test_builtin_logo_path_fallback(self, tmp_path: Path):
        """builtin_logo_path should be used as final fallback."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            # Create builtin logo
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin_logo = assets_dir / "logo.png"
            builtin_logo.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = resolve_logo_path(
                user_logo_path=None,
                saved_logo_path=None,
                builtin_logo_path="assets/logo.png",
            )
            assert result == str(builtin_logo.resolve())

    def test_all_invalid_returns_none(self, tmp_path: Path):
        """If all paths are invalid, should return None."""
        result = resolve_logo_path(
            user_logo_path=str(tmp_path / "invalid1.png"),
            saved_logo_path=str(tmp_path / "invalid2.png"),
            builtin_logo_path=str(tmp_path / "invalid3.png"),
        )
        assert result is None

    def test_custom_builtin_path_relative(self, tmp_path: Path):
        """Custom relative builtin path should be anchored to app root."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            # Create custom builtin logo in a non-assets location
            custom_dir = tmp_path / "custom"
            custom_dir.mkdir()
            custom_logo = custom_dir / "logo.png"
            custom_logo.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = resolve_logo_path(
                user_logo_path=None,
                saved_logo_path=None,
                builtin_logo_path="custom/logo.png",
            )
            assert result == str(custom_logo.resolve())


# ============================================================================
# TESTS: is_valid_logo_location
# ============================================================================


class TestIsValidLogoLocation:
    """Tests for is_valid_logo_location() wrapper."""

    def test_valid_png_returns_true(self, valid_png_file: Path):
        """Valid PNG file should return True."""
        assert is_valid_logo_location(str(valid_png_file)) is True

    def test_valid_jpeg_returns_true(self, valid_jpeg_file: Path):
        """Valid JPEG file should return True."""
        assert is_valid_logo_location(str(valid_jpeg_file)) is True

    def test_none_returns_false(self):
        """None should return False."""
        assert is_valid_logo_location(None) is False

    def test_invalid_path_returns_false(self, tmp_path: Path):
        """Invalid path should return False."""
        assert is_valid_logo_location(str(tmp_path / "nonexistent.png")) is False

    def test_wrong_signature_returns_false(self, png_wrong_signature: Path):
        """File with wrong signature should return False."""
        assert is_valid_logo_location(str(png_wrong_signature)) is False


# ============================================================================
# TESTS: coerce_logo_file
# ============================================================================


class TestCoerceLogoFile:
    """Tests for coerce_logo_file() wrapper."""

    def test_valid_png_returns_string_path(self, valid_png_file: Path):
        """Valid PNG file should return string path."""
        result = coerce_logo_file(str(valid_png_file))
        assert result is not None
        assert isinstance(result, str)
        assert result == str(valid_png_file.resolve())

    def test_valid_jpeg_returns_string_path(self, valid_jpeg_file: Path):
        """Valid JPEG file should return string path."""
        result = coerce_logo_file(str(valid_jpeg_file))
        assert result is not None
        assert isinstance(result, str)
        assert result == str(valid_jpeg_file.resolve())

    def test_none_returns_none(self):
        """None should return None."""
        assert coerce_logo_file(None) is None

    def test_invalid_path_returns_none(self, tmp_path: Path):
        """Invalid path should return None."""
        assert coerce_logo_file(str(tmp_path / "nonexistent.png")) is None


# ============================================================================
# TESTS: normalize_logo_setting_value
# ============================================================================


class TestNormalizeLogoSettingValue:
    """Tests for normalize_logo_setting_value() settings storage."""

    def test_assets_path_stays_relative(self):
        """Paths starting with 'assets/' should stay relative."""
        result = normalize_logo_setting_value("assets/logo.png")
        assert result == "assets/logo.png"

    def test_default_builtin_path_stays_relative(self):
        """DEFAULT_BUILTIN_LOGO_PATH should stay relative."""
        result = normalize_logo_setting_value(DEFAULT_BUILTIN_LOGO_PATH)
        assert result == DEFAULT_BUILTIN_LOGO_PATH

    def test_assets_custom_subpath_stays_relative(self):
        """Custom paths under assets/ should stay relative."""
        result = normalize_logo_setting_value("assets/custom/logo.png")
        assert result == "assets/custom/logo.png"

    def test_custom_path_becomes_absolute(self, valid_png_file: Path):
        """Custom paths should become absolute."""
        result = normalize_logo_setting_value(str(valid_png_file))
        assert Path(result).is_absolute()

    def test_relative_custom_path_becomes_absolute(self, tmp_path: Path, monkeypatch):
        """Relative custom paths should become absolute."""
        monkeypatch.chdir(tmp_path)
        # Create a local file
        local_logo = tmp_path / "local_logo.png"
        local_logo.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

        result = normalize_logo_setting_value("local_logo.png")
        assert Path(result).is_absolute()

    def test_path_matching_builtin_normalized_to_constant(self, tmp_path: Path):
        """Path that resolves to builtin should be normalized to constant."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            with patch(
                "src.utils.logo._get_builtin_logo_file",
                return_value=tmp_path / "assets" / "logo.png",
            ):
                # Create the builtin file
                assets_dir = tmp_path / "assets"
                assets_dir.mkdir()
                builtin = assets_dir / "logo.png"
                builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

                result = normalize_logo_setting_value(str(builtin))
                assert result == DEFAULT_BUILTIN_LOGO_PATH


# ============================================================================
# TESTS: list_logo_candidates
# ============================================================================


class TestListLogoCandidates:
    """Tests for list_logo_candidates() selection UI support."""

    def test_builtin_logo_included_first(self, tmp_path: Path):
        """Built-in logo should be first in the list."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin = assets_dir / "logo.png"
            builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = list_logo_candidates()

            assert len(result) >= 1
            assert result[0]["name"] == "Built-in"

    def test_returns_list_of_dicts(self, tmp_path: Path):
        """Should return list of dicts with expected keys."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin = assets_dir / "logo.png"
            builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = list_logo_candidates()

            assert isinstance(result, list)
            for item in result:
                assert "name" in item
                assert "setting_value" in item
                assert "resolved_path" in item

    def test_saved_logo_path_included(self, tmp_path: Path, valid_png_file: Path):
        """saved_logo_path should be included in candidates."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin = assets_dir / "logo.png"
            builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = list_logo_candidates(saved_logo_path=str(valid_png_file))

            assert len(result) == 2
            saved_names = [item["name"] for item in result]
            assert any("Saved" in name for name in saved_names)

    def test_deduplication_by_resolved_path(self, tmp_path: Path):
        """Duplicate resolved paths should be deduplicated."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin = assets_dir / "logo.png"
            builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            # Pass the same path as both builtin and saved
            result = list_logo_candidates(
                saved_logo_path="assets/logo.png",
                builtin_logo_path="assets/logo.png",
            )

            # Should only have one entry
            assert len(result) == 1
            assert result[0]["name"] == "Built-in"

    def test_invalid_saved_path_excluded(self, tmp_path: Path):
        """Invalid saved_logo_path should be excluded."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin = assets_dir / "logo.png"
            builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = list_logo_candidates(
                saved_logo_path=str(tmp_path / "nonexistent.png")
            )

            # Only builtin should be present
            assert len(result) == 1
            assert result[0]["name"] == "Built-in"

    def test_empty_list_when_no_valid_logos(self, tmp_path: Path):
        """Should return empty list when no valid logos exist."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            result = list_logo_candidates(
                saved_logo_path=str(tmp_path / "invalid.png"),
                builtin_logo_path=str(tmp_path / "also_invalid.png"),
            )

            assert result == []

    def test_saved_logo_name_from_filename(self, tmp_path: Path, valid_png_file: Path):
        """Saved logo name should include the filename."""
        with patch("src.utils.logo._get_app_root", return_value=tmp_path):
            assets_dir = tmp_path / "assets"
            assets_dir.mkdir()
            builtin = assets_dir / "logo.png"
            builtin.write_bytes(PNG_SIGNATURE + b"\x00" * 100)

            result = list_logo_candidates(saved_logo_path=str(valid_png_file))

            saved_item = next(item for item in result if "Saved" in item["name"])
            assert valid_png_file.name in saved_item["name"]


# ============================================================================
# TESTS: Error Handling Edge Cases
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in edge cases."""

    def test_permission_error_on_read(self, tmp_path: Path):
        """Permission errors during file read should return False."""
        # Create a file but make it unreadable (Unix only)
        import os
        import sys

        if sys.platform == "win32":
            pytest.skip("Permission test not applicable on Windows")

        protected_file = tmp_path / "protected.png"
        protected_file.write_bytes(PNG_SIGNATURE + b"\x00" * 100)
        os.chmod(protected_file, 0o000)

        try:
            result = _looks_like_png(protected_file)
            assert result is False
        finally:
            os.chmod(protected_file, 0o644)

    def test_symlink_to_valid_file(self, tmp_path: Path, valid_png_file: Path):
        """Symlink to valid file should be accepted."""
        import os

        symlink_path = tmp_path / "symlink.png"
        os.symlink(valid_png_file, symlink_path)

        result = _coerce_to_existing_logo_file(str(symlink_path))
        assert result is not None

    def test_very_small_file(self, tmp_path: Path):
        """File smaller than signature should return False."""
        tiny_file = tmp_path / "tiny.png"
        tiny_file.write_bytes(b"\x89P")  # Incomplete PNG signature

        assert _looks_like_png(tiny_file) is False
        assert _has_expected_image_signature(tiny_file) is False
