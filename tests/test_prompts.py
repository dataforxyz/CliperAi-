# -*- coding: utf-8 -*-
"""
Comprehensive pytest tests for src/prompts module.

Tests all prompt templates, getter functions, and the style selection registry.
"""
import pytest

from src.prompts import (
    get_prompt_for_style,
    get_available_styles,
    build_base_system_prompt,
    SYSTEM_PROMPT,
    JSON_FORMAT_INSTRUCTIONS,
    get_viral_prompt,
    get_educational_prompt,
    get_storytelling_prompt,
)
from src.prompts.classifier_prompt import (
    get_classifier_prompt,
    CLASSIFIER_PROMPT,
    CLASSIFICATION_SCHEMA,
)
from src.prompts.viral_prompt import VIRAL_STYLE_PROMPT
from src.prompts.educational_prompt import EDUCATIONAL_STYLE_PROMPT
from src.prompts.storytelling_prompt import STORYTELLING_STYLE_PROMPT


# ============================================================================
# SYSTEM_PROMPT AND JSON_FORMAT_INSTRUCTIONS TESTS
# ============================================================================

class TestBasePromptConstants:
    """Tests for SYSTEM_PROMPT and JSON_FORMAT_INSTRUCTIONS constants."""

    def test_system_prompt_is_non_empty_string(self):
        """SYSTEM_PROMPT should be a non-empty string."""
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_expected_keywords(self):
        """SYSTEM_PROMPT should contain key instructions."""
        assert "TikTok" in SYSTEM_PROMPT or "Reels" in SYSTEM_PROMPT
        assert "copy" in SYSTEM_PROMPT.lower()
        assert "metadata" in SYSTEM_PROMPT.lower()
        assert "150" in SYSTEM_PROMPT  # character limit

    def test_system_prompt_contains_aicdmx_requirement(self):
        """SYSTEM_PROMPT should mandate #AICDMX hashtag."""
        assert "#AICDMX" in SYSTEM_PROMPT

    def test_system_prompt_contains_json_instruction(self):
        """SYSTEM_PROMPT should instruct to respond with JSON."""
        assert "JSON" in SYSTEM_PROMPT

    def test_json_format_instructions_is_non_empty_string(self):
        """JSON_FORMAT_INSTRUCTIONS should be a non-empty string."""
        assert isinstance(JSON_FORMAT_INSTRUCTIONS, str)
        assert len(JSON_FORMAT_INSTRUCTIONS) > 0

    def test_json_format_instructions_contains_expected_structure(self):
        """JSON_FORMAT_INSTRUCTIONS should define expected JSON structure."""
        assert "clips" in JSON_FORMAT_INSTRUCTIONS
        assert "clip_id" in JSON_FORMAT_INSTRUCTIONS
        assert "copy" in JSON_FORMAT_INSTRUCTIONS
        assert "metadata" in JSON_FORMAT_INSTRUCTIONS


# ============================================================================
# build_base_system_prompt() TESTS
# ============================================================================

class TestBuildBaseSystemPrompt:
    """Tests for build_base_system_prompt() function."""

    def test_returns_string(self):
        """build_base_system_prompt should return a string."""
        result = build_base_system_prompt()
        assert isinstance(result, str)

    def test_without_format_instructions(self):
        """build_base_system_prompt(include_format=False) returns only SYSTEM_PROMPT."""
        result = build_base_system_prompt(include_format=False)
        assert result == SYSTEM_PROMPT
        assert JSON_FORMAT_INSTRUCTIONS not in result

    def test_with_format_instructions(self):
        """build_base_system_prompt(include_format=True) includes both prompts."""
        result = build_base_system_prompt(include_format=True)
        assert SYSTEM_PROMPT in result
        assert JSON_FORMAT_INSTRUCTIONS in result

    def test_default_includes_format_instructions(self):
        """build_base_system_prompt() defaults to including format instructions."""
        result = build_base_system_prompt()
        assert JSON_FORMAT_INSTRUCTIONS in result

    def test_combined_prompt_properly_formatted(self):
        """Combined prompt should have proper separation between sections."""
        result = build_base_system_prompt(include_format=True)
        # Should contain both sections with some separation
        assert len(result) > len(SYSTEM_PROMPT)
        assert len(result) > len(JSON_FORMAT_INSTRUCTIONS)


# ============================================================================
# STYLE PROMPT GETTER TESTS
# ============================================================================

class TestViralPrompt:
    """Tests for get_viral_prompt() and VIRAL_STYLE_PROMPT."""

    def test_viral_prompt_constant_is_non_empty_string(self):
        """VIRAL_STYLE_PROMPT should be a non-empty string."""
        assert isinstance(VIRAL_STYLE_PROMPT, str)
        assert len(VIRAL_STYLE_PROMPT) > 0

    def test_get_viral_prompt_returns_constant(self):
        """get_viral_prompt() should return VIRAL_STYLE_PROMPT."""
        assert get_viral_prompt() == VIRAL_STYLE_PROMPT

    def test_viral_prompt_contains_style_keywords(self):
        """Viral prompt should contain viral-specific keywords."""
        prompt = get_viral_prompt()
        assert "VIRAL" in prompt.upper()
        assert "hook" in prompt.lower()
        # Viral style focuses on attention-grabbing
        assert "attention" in prompt.lower() or "provocativ" in prompt.lower()

    def test_viral_prompt_contains_aicdmx(self):
        """Viral prompt should reference #AICDMX hashtag requirement."""
        prompt = get_viral_prompt()
        assert "#AICDMX" in prompt


class TestEducationalPrompt:
    """Tests for get_educational_prompt() and EDUCATIONAL_STYLE_PROMPT."""

    def test_educational_prompt_constant_is_non_empty_string(self):
        """EDUCATIONAL_STYLE_PROMPT should be a non-empty string."""
        assert isinstance(EDUCATIONAL_STYLE_PROMPT, str)
        assert len(EDUCATIONAL_STYLE_PROMPT) > 0

    def test_get_educational_prompt_returns_constant(self):
        """get_educational_prompt() should return EDUCATIONAL_STYLE_PROMPT."""
        assert get_educational_prompt() == EDUCATIONAL_STYLE_PROMPT

    def test_educational_prompt_contains_style_keywords(self):
        """Educational prompt should contain educational-specific keywords."""
        prompt = get_educational_prompt()
        assert "EDUCATIONAL" in prompt.upper()
        assert "valor" in prompt.lower() or "value" in prompt.lower()
        # Educational style focuses on learning
        assert "aprendizaje" in prompt.lower() or "learn" in prompt.lower()

    def test_educational_prompt_contains_aicdmx(self):
        """Educational prompt should reference #AICDMX hashtag requirement."""
        prompt = get_educational_prompt()
        assert "#AICDMX" in prompt


class TestStorytellingPrompt:
    """Tests for get_storytelling_prompt() and STORYTELLING_STYLE_PROMPT."""

    def test_storytelling_prompt_constant_is_non_empty_string(self):
        """STORYTELLING_STYLE_PROMPT should be a non-empty string."""
        assert isinstance(STORYTELLING_STYLE_PROMPT, str)
        assert len(STORYTELLING_STYLE_PROMPT) > 0

    def test_get_storytelling_prompt_returns_constant(self):
        """get_storytelling_prompt() should return STORYTELLING_STYLE_PROMPT."""
        assert get_storytelling_prompt() == STORYTELLING_STYLE_PROMPT

    def test_storytelling_prompt_contains_style_keywords(self):
        """Storytelling prompt should contain storytelling-specific keywords."""
        prompt = get_storytelling_prompt()
        assert "STORYTELLING" in prompt.upper()
        # Storytelling focuses on narrative and personal stories
        assert "historia" in prompt.lower() or "story" in prompt.lower()
        assert "journey" in prompt.lower() or "narrativa" in prompt.lower()

    def test_storytelling_prompt_contains_aicdmx(self):
        """Storytelling prompt should reference #AICDMX hashtag requirement."""
        prompt = get_storytelling_prompt()
        assert "#AICDMX" in prompt


# ============================================================================
# CLASSIFIER PROMPT TESTS
# ============================================================================

class TestClassifierPrompt:
    """Tests for get_classifier_prompt() and CLASSIFIER_PROMPT."""

    def test_classifier_prompt_constant_is_non_empty_string(self):
        """CLASSIFIER_PROMPT should be a non-empty string."""
        assert isinstance(CLASSIFIER_PROMPT, str)
        assert len(CLASSIFIER_PROMPT) > 0

    def test_get_classifier_prompt_returns_constant(self):
        """get_classifier_prompt() should return CLASSIFIER_PROMPT."""
        assert get_classifier_prompt() == CLASSIFIER_PROMPT

    def test_classifier_prompt_contains_classification_keywords(self):
        """Classifier prompt should contain classification-related keywords."""
        prompt = get_classifier_prompt()
        assert "clasificar" in prompt.lower() or "classif" in prompt.lower()
        # Should mention all three styles
        assert "viral" in prompt.lower()
        assert "educational" in prompt.lower()
        assert "storytelling" in prompt.lower()

    def test_classifier_prompt_defines_style_criteria(self):
        """Classifier prompt should define criteria for each style."""
        prompt = get_classifier_prompt()
        # Should have sections for each style
        assert "ESTILOS DISPONIBLES" in prompt or "styles" in prompt.lower()

    def test_classifier_prompt_specifies_json_output(self):
        """Classifier prompt should specify JSON output format."""
        prompt = get_classifier_prompt()
        assert "JSON" in prompt
        assert "classifications" in prompt


class TestClassificationSchema:
    """Tests for CLASSIFICATION_SCHEMA dictionary."""

    def test_classification_schema_is_dict(self):
        """CLASSIFICATION_SCHEMA should be a dictionary."""
        assert isinstance(CLASSIFICATION_SCHEMA, dict)

    def test_classification_schema_has_type(self):
        """CLASSIFICATION_SCHEMA should have 'type' key."""
        assert "type" in CLASSIFICATION_SCHEMA
        assert CLASSIFICATION_SCHEMA["type"] == "object"

    def test_classification_schema_has_properties(self):
        """CLASSIFICATION_SCHEMA should have 'properties' key."""
        assert "properties" in CLASSIFICATION_SCHEMA

    def test_classification_schema_has_required(self):
        """CLASSIFICATION_SCHEMA should have 'required' key."""
        assert "required" in CLASSIFICATION_SCHEMA
        assert "classifications" in CLASSIFICATION_SCHEMA["required"]

    def test_classification_schema_defines_classifications_array(self):
        """CLASSIFICATION_SCHEMA should define classifications as array."""
        props = CLASSIFICATION_SCHEMA["properties"]
        assert "classifications" in props
        assert props["classifications"]["type"] == "array"

    def test_classification_schema_item_properties(self):
        """Classification items should have required properties."""
        items = CLASSIFICATION_SCHEMA["properties"]["classifications"]["items"]
        item_props = items["properties"]

        assert "clip_id" in item_props
        assert "style" in item_props
        assert "confidence" in item_props
        assert "reason" in item_props

    def test_classification_schema_style_enum(self):
        """Style property should enumerate valid styles."""
        items = CLASSIFICATION_SCHEMA["properties"]["classifications"]["items"]
        style_def = items["properties"]["style"]

        assert "enum" in style_def
        assert "viral" in style_def["enum"]
        assert "educational" in style_def["enum"]
        assert "storytelling" in style_def["enum"]


# ============================================================================
# get_available_styles() TESTS
# ============================================================================

class TestGetAvailableStyles:
    """Tests for get_available_styles() function."""

    def test_returns_list(self):
        """get_available_styles should return a list."""
        result = get_available_styles()
        assert isinstance(result, list)

    def test_returns_expected_styles(self):
        """get_available_styles should return exactly the three styles."""
        result = get_available_styles()
        assert result == ["viral", "educational", "storytelling"]

    def test_returns_three_styles(self):
        """get_available_styles should return exactly 3 styles."""
        result = get_available_styles()
        assert len(result) == 3

    def test_all_styles_are_strings(self):
        """All returned styles should be strings."""
        result = get_available_styles()
        for style in result:
            assert isinstance(style, str)

    def test_styles_are_lowercase(self):
        """All styles should be lowercase."""
        result = get_available_styles()
        for style in result:
            assert style == style.lower()


# ============================================================================
# get_prompt_for_style() TESTS
# ============================================================================

class TestGetPromptForStyle:
    """Tests for get_prompt_for_style() function."""

    def test_returns_string(self):
        """get_prompt_for_style should return a string."""
        result = get_prompt_for_style("viral")
        assert isinstance(result, str)

    def test_viral_style_returns_combined_prompt(self):
        """get_prompt_for_style('viral') should combine base and viral prompts."""
        result = get_prompt_for_style("viral")
        # Should contain base system prompt content
        assert "TikTok" in result or "Reels" in result
        # Should contain viral style content
        assert "VIRAL" in result.upper()

    def test_educational_style_returns_combined_prompt(self):
        """get_prompt_for_style('educational') combines base and educational prompts."""
        result = get_prompt_for_style("educational")
        # Should contain base system prompt content
        assert "JSON" in result
        # Should contain educational style content
        assert "EDUCATIONAL" in result.upper()

    def test_storytelling_style_returns_combined_prompt(self):
        """get_prompt_for_style('storytelling') combines base and storytelling prompts."""
        result = get_prompt_for_style("storytelling")
        # Should contain base system prompt content
        assert "metadata" in result.lower()
        # Should contain storytelling style content
        assert "STORYTELLING" in result.upper()

    def test_default_style_is_viral(self):
        """get_prompt_for_style() without args should default to viral."""
        default_result = get_prompt_for_style()
        viral_result = get_prompt_for_style("viral")
        assert default_result == viral_result

    def test_invalid_style_raises_value_error(self):
        """get_prompt_for_style with invalid style should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_prompt_for_style("nonexistent_style")

        error_message = str(exc_info.value)
        assert "nonexistent_style" in error_message
        # Should mention valid options
        assert "viral" in error_message or "Opciones" in error_message

    def test_invalid_style_error_message_contains_options(self):
        """ValueError for invalid style should list available options."""
        with pytest.raises(ValueError) as exc_info:
            get_prompt_for_style("invalid")

        error_message = str(exc_info.value)
        # Should list valid styles
        assert "viral" in error_message
        assert "educational" in error_message
        assert "storytelling" in error_message

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_all_valid_styles_work(self, style):
        """All valid styles should return non-empty prompts."""
        result = get_prompt_for_style(style)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_all_styles_include_base_prompt(self, style):
        """All style prompts should include base system prompt content."""
        result = get_prompt_for_style(style)
        # Base prompt always includes character limit and JSON requirement
        assert "150" in result
        assert "JSON" in result

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_all_styles_include_format_instructions(self, style):
        """All style prompts should include JSON format instructions."""
        result = get_prompt_for_style(style)
        # Format instructions define the clips array structure
        assert "clips" in result.lower()

    def test_prompt_length_is_substantial(self):
        """Generated prompts should be substantial (not just a few lines)."""
        for style in ["viral", "educational", "storytelling"]:
            result = get_prompt_for_style(style)
            # Each full prompt should be at least 1000 characters
            assert len(result) > 1000


# ============================================================================
# AICDMX HASHTAG REQUIREMENT TESTS
# ============================================================================

class TestAicdmxHashtagRequirement:
    """Tests verifying #AICDMX is mandated across all prompts."""

    def test_system_prompt_requires_aicdmx(self):
        """SYSTEM_PROMPT should require #AICDMX hashtag."""
        assert "#AICDMX" in SYSTEM_PROMPT
        # Should emphasize it's obligatory
        assert "obligatori" in SYSTEM_PROMPT.lower()

    def test_viral_prompt_references_aicdmx(self):
        """Viral prompt should reference #AICDMX in examples."""
        prompt = get_viral_prompt()
        # Count occurrences to ensure it's emphasized
        count = prompt.count("#AICDMX")
        assert count >= 5  # Should appear in multiple examples

    def test_educational_prompt_references_aicdmx(self):
        """Educational prompt should reference #AICDMX in examples."""
        prompt = get_educational_prompt()
        count = prompt.count("#AICDMX")
        assert count >= 5

    def test_storytelling_prompt_references_aicdmx(self):
        """Storytelling prompt should reference #AICDMX in examples."""
        prompt = get_storytelling_prompt()
        count = prompt.count("#AICDMX")
        assert count >= 5

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_full_prompt_contains_aicdmx_multiple_times(self, style):
        """Full prompts for all styles should emphasize #AICDMX."""
        result = get_prompt_for_style(style)
        count = result.count("#AICDMX")
        # Should appear many times (base prompt + style prompt)
        assert count >= 10


# ============================================================================
# PROMPT OUTPUT VALIDITY TESTS
# ============================================================================

class TestPromptOutputValidity:
    """Tests verifying rendered prompts produce valid output strings."""

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_prompts_are_valid_utf8(self, style):
        """All prompts should be valid UTF-8 strings."""
        result = get_prompt_for_style(style)
        # Should encode/decode cleanly
        encoded = result.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert result == decoded

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_prompts_have_no_format_string_placeholders(self, style):
        """Prompts should not have unfilled format string placeholders."""
        result = get_prompt_for_style(style)
        # Check for common unfilled placeholders
        assert "{" not in result or "}" not in result or \
               result.count("{") == result.count("}")

    def test_classifier_prompt_is_valid_utf8(self):
        """Classifier prompt should be valid UTF-8."""
        result = get_classifier_prompt()
        encoded = result.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert result == decoded

    @pytest.mark.parametrize("style", ["viral", "educational", "storytelling"])
    def test_prompts_contain_emoji_for_style_indication(self, style):
        """Each style prompt should include emoji for visual distinction."""
        result = get_prompt_for_style(style)
        # Common emoji patterns used in prompts
        emoji_patterns = ["🔥", "📚", "📖", "✅", "❌", "🚀", "😱", "🤔", "💀"]
        has_emoji = any(emoji in result for emoji in emoji_patterns)
        assert has_emoji

    def test_build_base_system_prompt_is_idempotent(self):
        """Calling build_base_system_prompt multiple times returns same result."""
        result1 = build_base_system_prompt(include_format=True)
        result2 = build_base_system_prompt(include_format=True)
        assert result1 == result2

    def test_style_getter_functions_are_idempotent(self):
        """Style getter functions should return same result on multiple calls."""
        assert get_viral_prompt() == get_viral_prompt()
        assert get_educational_prompt() == get_educational_prompt()
        assert get_storytelling_prompt() == get_storytelling_prompt()
        assert get_classifier_prompt() == get_classifier_prompt()
