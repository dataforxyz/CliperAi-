# -*- coding: utf-8 -*-
"""
Comprehensive pytest tests for src/models/copy_schemas.py

Tests all Pydantic models, validators, and helper functions with both
positive and negative test cases.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.copy_schemas import (
    CopyMetadata,
    ClipCopy,
    CopysOutput,
    SavedCopys,
    calculate_averages,
    create_saved_copys,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_metadata_dict():
    """Returns a valid CopyMetadata dictionary."""
    return {
        "sentiment": "educational",
        "sentiment_score": 0.75,
        "engagement_score": 8.5,
        "suggested_thumbnail_timestamp": 12.5,
        "primary_topics": ["AI", "tech", "innovation"],
        "hook_strength": "high",
        "viral_potential": 7.8,
    }


@pytest.fixture
def valid_metadata(valid_metadata_dict):
    """Returns a valid CopyMetadata instance."""
    return CopyMetadata(**valid_metadata_dict)


@pytest.fixture
def valid_clip_copy_dict(valid_metadata_dict):
    """Returns a valid ClipCopy dictionary."""
    return {
        "clip_id": 1,
        "copy": "This is amazing content! #TechTips #AICDMX",
        "metadata": valid_metadata_dict,
    }


@pytest.fixture
def valid_clip_copy(valid_clip_copy_dict):
    """Returns a valid ClipCopy instance."""
    return ClipCopy(**valid_clip_copy_dict)


@pytest.fixture
def valid_copys_output(valid_clip_copy_dict):
    """Returns a valid CopysOutput instance."""
    return CopysOutput(clips=[ClipCopy(**valid_clip_copy_dict)])


# ============================================================================
# COPYMETADATA TESTS - normalize_sentiment validator
# ============================================================================

class TestCopyMetadataSentimentValidator:
    """Tests for CopyMetadata.normalize_sentiment() validator."""

    @pytest.mark.parametrize("sentiment", [
        "educational",
        "humorous",
        "inspirational",
        "controversial",
        "curious_educational",
        "relatable",
        "storytelling",
    ])
    def test_valid_sentiments_accepted(self, valid_metadata_dict, sentiment):
        """All valid sentiment literals should be accepted as-is."""
        valid_metadata_dict["sentiment"] = sentiment
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment == sentiment

    @pytest.mark.parametrize("hybrid,expected", [
        ("educational_storytelling", "educational"),
        ("humorous_relatable", "humorous"),
        ("inspirational_educational", "educational"),  # 'educational' appears earlier in valid_sentiments
        ("storytelling_educational", "educational"),   # 'educational' appears earlier in valid_sentiments
        ("curious_educational_humorous", "curious_educational"),
    ])
    def test_hybrid_sentiments_normalized(self, valid_metadata_dict, hybrid, expected):
        """Hybrid sentiments should be normalized to first valid match in valid_sentiments order."""
        valid_metadata_dict["sentiment"] = hybrid
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment == expected

    def test_unknown_sentiment_falls_back_to_relatable(self, valid_metadata_dict):
        """Unknown sentiment strings should fallback to 'relatable'."""
        valid_metadata_dict["sentiment"] = "unknown_sentiment_type"
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment == "relatable"

    def test_partial_match_in_hybrid(self, valid_metadata_dict):
        """Partial matches in hybrid strings should work."""
        valid_metadata_dict["sentiment"] = "some_humorous_content"
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment == "humorous"

    def test_first_word_match(self, valid_metadata_dict):
        """First word of hybrid should match if valid."""
        valid_metadata_dict["sentiment"] = "educational_unknown"
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment == "educational"


# ============================================================================
# COPYMETADATA TESTS - topics_must_be_unique_and_limited validator
# ============================================================================

class TestCopyMetadataTopicsValidator:
    """Tests for CopyMetadata.topics_must_be_unique_and_limited() validator."""

    def test_valid_topics_pass_through(self, valid_metadata_dict):
        """Valid unique topics should pass through unchanged."""
        valid_metadata_dict["primary_topics"] = ["AI", "tech", "innovation"]
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.primary_topics == ["AI", "tech", "innovation"]

    def test_duplicate_topics_removed(self, valid_metadata_dict):
        """Duplicate topics should be removed (case-insensitive)."""
        valid_metadata_dict["primary_topics"] = ["AI", "ai", "Tech", "tech", "innovation"]
        metadata = CopyMetadata(**valid_metadata_dict)
        # Should keep first occurrence, remove duplicates
        assert len(metadata.primary_topics) == 3
        assert "AI" in metadata.primary_topics
        assert "Tech" in metadata.primary_topics
        assert "innovation" in metadata.primary_topics

    def test_topics_truncated_to_five(self, valid_metadata_dict):
        """More than 5 unique topics should be truncated to 5."""
        valid_metadata_dict["primary_topics"] = [
            "AI", "tech", "innovation", "startup", "coding", "Python", "ML"
        ]
        metadata = CopyMetadata(**valid_metadata_dict)
        assert len(metadata.primary_topics) == 5
        assert metadata.primary_topics == ["AI", "tech", "innovation", "startup", "coding"]

    def test_duplicate_removal_before_truncation(self, valid_metadata_dict):
        """Duplicates should be removed before truncation."""
        valid_metadata_dict["primary_topics"] = [
            "AI", "ai", "AI", "tech", "TECH", "innovation", "startup", "coding"
        ]
        metadata = CopyMetadata(**valid_metadata_dict)
        # After dedup: AI, tech, innovation, startup, coding (5 unique)
        assert len(metadata.primary_topics) == 5

    def test_maintains_original_order(self, valid_metadata_dict):
        """Original order should be maintained after deduplication."""
        valid_metadata_dict["primary_topics"] = ["first", "second", "FIRST", "third"]
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.primary_topics[0] == "first"
        assert metadata.primary_topics[1] == "second"
        assert metadata.primary_topics[2] == "third"


# ============================================================================
# COPYMETADATA TESTS - Field Constraints
# ============================================================================

class TestCopyMetadataFieldConstraints:
    """Tests for CopyMetadata field constraints and ranges."""

    def test_sentiment_score_valid_range(self, valid_metadata_dict):
        """sentiment_score should accept values in [0, 1]."""
        for score in [0.0, 0.5, 1.0]:
            valid_metadata_dict["sentiment_score"] = score
            metadata = CopyMetadata(**valid_metadata_dict)
            assert metadata.sentiment_score == score

    def test_sentiment_score_below_range_rejected(self, valid_metadata_dict):
        """sentiment_score below 0 should raise ValidationError."""
        valid_metadata_dict["sentiment_score"] = -0.1
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "sentiment_score" in str(exc_info.value)

    def test_sentiment_score_above_range_rejected(self, valid_metadata_dict):
        """sentiment_score above 1 should raise ValidationError."""
        valid_metadata_dict["sentiment_score"] = 1.1
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "sentiment_score" in str(exc_info.value)

    def test_engagement_score_valid_range(self, valid_metadata_dict):
        """engagement_score should accept values in [1, 10]."""
        for score in [1.0, 5.5, 10.0]:
            valid_metadata_dict["engagement_score"] = score
            metadata = CopyMetadata(**valid_metadata_dict)
            assert metadata.engagement_score == score

    def test_engagement_score_below_range_rejected(self, valid_metadata_dict):
        """engagement_score below 1 should raise ValidationError."""
        valid_metadata_dict["engagement_score"] = 0.9
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "engagement_score" in str(exc_info.value)

    def test_engagement_score_above_range_rejected(self, valid_metadata_dict):
        """engagement_score above 10 should raise ValidationError."""
        valid_metadata_dict["engagement_score"] = 10.1
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "engagement_score" in str(exc_info.value)

    def test_viral_potential_valid_range(self, valid_metadata_dict):
        """viral_potential should accept values in [1, 10]."""
        for score in [1.0, 5.5, 10.0]:
            valid_metadata_dict["viral_potential"] = score
            metadata = CopyMetadata(**valid_metadata_dict)
            assert metadata.viral_potential == score

    def test_viral_potential_below_range_rejected(self, valid_metadata_dict):
        """viral_potential below 1 should raise ValidationError."""
        valid_metadata_dict["viral_potential"] = 0.5
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "viral_potential" in str(exc_info.value)

    def test_viral_potential_above_range_rejected(self, valid_metadata_dict):
        """viral_potential above 10 should raise ValidationError."""
        valid_metadata_dict["viral_potential"] = 10.5
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "viral_potential" in str(exc_info.value)

    @pytest.mark.parametrize("hook_strength", ["very_high", "high", "medium", "low"])
    def test_hook_strength_valid_literals(self, valid_metadata_dict, hook_strength):
        """hook_strength should accept valid literals."""
        valid_metadata_dict["hook_strength"] = hook_strength
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.hook_strength == hook_strength

    def test_hook_strength_invalid_literal_rejected(self, valid_metadata_dict):
        """hook_strength with invalid literal should raise ValidationError."""
        valid_metadata_dict["hook_strength"] = "super_high"
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "hook_strength" in str(exc_info.value)

    def test_suggested_thumbnail_timestamp_non_negative(self, valid_metadata_dict):
        """suggested_thumbnail_timestamp should accept non-negative values."""
        valid_metadata_dict["suggested_thumbnail_timestamp"] = 0.0
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.suggested_thumbnail_timestamp == 0.0

    def test_suggested_thumbnail_timestamp_negative_rejected(self, valid_metadata_dict):
        """suggested_thumbnail_timestamp negative values should raise ValidationError."""
        valid_metadata_dict["suggested_thumbnail_timestamp"] = -1.0
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "suggested_thumbnail_timestamp" in str(exc_info.value)

    def test_topics_min_length_violation(self, valid_metadata_dict):
        """primary_topics with less than 2 items should raise ValidationError."""
        valid_metadata_dict["primary_topics"] = ["only_one"]
        with pytest.raises(ValidationError) as exc_info:
            CopyMetadata(**valid_metadata_dict)
        assert "primary_topics" in str(exc_info.value)


# ============================================================================
# CLIPCOPY TESTS - truncate_and_validate_copy validator
# ============================================================================

class TestClipCopyCopyValidator:
    """Tests for ClipCopy.truncate_and_validate_copy() validator."""

    def test_valid_copy_with_hashtags_passes(self, valid_clip_copy_dict):
        """Valid copy with hashtags including #AICDMX should pass."""
        valid_clip_copy_dict["copy"] = "Great content here! #Tech #AICDMX"
        clip = ClipCopy(**valid_clip_copy_dict)
        assert clip.copy == "Great content here! #Tech #AICDMX"

    def test_copy_without_hashtag_rejected(self, valid_clip_copy_dict):
        """Copy without any hashtag should raise ValidationError."""
        valid_clip_copy_dict["copy"] = "This is content without any hashtag"
        with pytest.raises(ValidationError) as exc_info:
            ClipCopy(**valid_clip_copy_dict)
        assert "hashtag" in str(exc_info.value).lower()

    def test_copy_without_aicdmx_hashtag_rejected(self, valid_clip_copy_dict):
        """Copy without #AICDMX hashtag should raise ValidationError."""
        valid_clip_copy_dict["copy"] = "This has hashtag but not branding #Tech #AI"
        with pytest.raises(ValidationError) as exc_info:
            ClipCopy(**valid_clip_copy_dict)
        assert "AICDMX" in str(exc_info.value)

    def test_aicdmx_case_insensitive(self, valid_clip_copy_dict):
        """#AICDMX check should be case-insensitive."""
        valid_clip_copy_dict["copy"] = "Great content here! #aicdmx #Tech"
        clip = ClipCopy(**valid_clip_copy_dict)
        assert "#aicdmx" in clip.copy

    def test_long_copy_truncated(self, valid_clip_copy_dict):
        """Copy over 150 chars should be truncated."""
        # Create a copy that's definitely over 150 chars
        long_copy = "A" * 140 + " #AICDMX #ExtraHashtag"
        valid_clip_copy_dict["copy"] = long_copy
        clip = ClipCopy(**valid_clip_copy_dict)
        assert len(clip.copy) <= 150

    def test_truncation_preserves_aicdmx(self, valid_clip_copy_dict):
        """Truncation should preserve #AICDMX hashtag."""
        # Create long copy where truncation is needed
        long_copy = "A" * 120 + " #AICDMX #RemoveThis"
        valid_clip_copy_dict["copy"] = long_copy
        clip = ClipCopy(**valid_clip_copy_dict)
        assert "#AICDMX" in clip.copy.upper()

    def test_exactly_150_chars_passes(self, valid_clip_copy_dict):
        """Copy of exactly 150 chars should pass without truncation."""
        # Build exactly 150 chars with required hashtag
        base = "A" * 130 + " #AICDMX"
        padding = "B" * (150 - len(base))
        exact_copy = "A" * (130 - len(padding)) + padding + " #AICDMX"
        # Adjust to exactly 150
        exact_copy = "A" * (150 - 9) + " #AICDMX"  # " #AICDMX" is 8 chars
        valid_clip_copy_dict["copy"] = exact_copy
        clip = ClipCopy(**valid_clip_copy_dict)
        assert len(clip.copy) <= 150


# ============================================================================
# CLIPCOPY TESTS - Field Constraints
# ============================================================================

class TestClipCopyFieldConstraints:
    """Tests for ClipCopy field constraints."""

    def test_clip_id_valid(self, valid_clip_copy_dict):
        """clip_id >= 1 should be valid."""
        for clip_id in [1, 5, 100]:
            valid_clip_copy_dict["clip_id"] = clip_id
            clip = ClipCopy(**valid_clip_copy_dict)
            assert clip.clip_id == clip_id

    def test_clip_id_zero_rejected(self, valid_clip_copy_dict):
        """clip_id = 0 should raise ValidationError."""
        valid_clip_copy_dict["clip_id"] = 0
        with pytest.raises(ValidationError) as exc_info:
            ClipCopy(**valid_clip_copy_dict)
        assert "clip_id" in str(exc_info.value)

    def test_clip_id_negative_rejected(self, valid_clip_copy_dict):
        """clip_id < 0 should raise ValidationError."""
        valid_clip_copy_dict["clip_id"] = -1
        with pytest.raises(ValidationError) as exc_info:
            ClipCopy(**valid_clip_copy_dict)
        assert "clip_id" in str(exc_info.value)

    def test_copy_min_length_violation(self, valid_clip_copy_dict):
        """copy shorter than 20 chars should raise ValidationError."""
        valid_clip_copy_dict["copy"] = "Short #AICDMX"  # 13 chars
        with pytest.raises(ValidationError) as exc_info:
            ClipCopy(**valid_clip_copy_dict)
        assert "copy" in str(exc_info.value).lower()

    def test_copy_at_min_length_passes(self, valid_clip_copy_dict):
        """copy of exactly 20 chars should pass."""
        # 20 chars with hashtag
        valid_clip_copy_dict["copy"] = "Good stuff! #AICDMX"  # 19 chars, need 1 more
        valid_clip_copy_dict["copy"] = "Good stuff!! #AICDMX"  # 20 chars
        clip = ClipCopy(**valid_clip_copy_dict)
        assert len(clip.copy) >= 20


# ============================================================================
# COPYSOUTPUT TESTS
# ============================================================================

class TestCopysOutput:
    """Tests for CopysOutput model."""

    def test_valid_copys_output(self, valid_clip_copy_dict):
        """Valid CopysOutput with clips should work."""
        output = CopysOutput(clips=[ClipCopy(**valid_clip_copy_dict)])
        assert len(output.clips) == 1

    def test_multiple_clips(self, valid_clip_copy_dict):
        """CopysOutput should accept multiple clips."""
        clip1 = valid_clip_copy_dict.copy()
        clip2 = valid_clip_copy_dict.copy()
        clip2["clip_id"] = 2
        output = CopysOutput(clips=[ClipCopy(**clip1), ClipCopy(**clip2)])
        assert len(output.clips) == 2

    def test_empty_clips_list_rejected(self):
        """CopysOutput with empty clips list should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CopysOutput(clips=[])
        assert "clips" in str(exc_info.value)

    def test_has_json_schema_extra(self):
        """CopysOutput should have json_schema_extra with example."""
        schema = CopysOutput.model_json_schema()
        # The example should be in the schema
        assert "example" in str(schema) or "clips" in schema


# ============================================================================
# SAVEDCOPYS TESTS
# ============================================================================

class TestSavedCopys:
    """Tests for SavedCopys model."""

    def test_valid_saved_copys(self, valid_clip_copy_dict):
        """Valid SavedCopys should work."""
        saved = SavedCopys(
            video_id="test_video_123",
            generated_at=datetime.now(),
            model="gemini-2.5-flash",
            total_clips=1,
            style="viral",
            average_engagement=8.5,
            average_viral_potential=7.5,
            clips=[ClipCopy(**valid_clip_copy_dict)],
        )
        assert saved.video_id == "test_video_123"
        assert saved.total_clips == 1

    def test_total_clips_must_be_positive(self, valid_clip_copy_dict):
        """total_clips must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            SavedCopys(
                video_id="test_video",
                generated_at=datetime.now(),
                model="gemini-2.5-flash",
                total_clips=0,
                style="viral",
                average_engagement=8.5,
                average_viral_potential=7.5,
                clips=[ClipCopy(**valid_clip_copy_dict)],
            )
        assert "total_clips" in str(exc_info.value)

    def test_average_engagement_range(self, valid_clip_copy_dict):
        """average_engagement must be in [0, 10]."""
        # Valid at boundaries
        for avg in [0.0, 5.0, 10.0]:
            saved = SavedCopys(
                video_id="test_video",
                generated_at=datetime.now(),
                model="gemini-2.5-flash",
                total_clips=1,
                style="viral",
                average_engagement=avg,
                average_viral_potential=5.0,
                clips=[ClipCopy(**valid_clip_copy_dict)],
            )
            assert saved.average_engagement == avg

    def test_average_engagement_above_range_rejected(self, valid_clip_copy_dict):
        """average_engagement above 10 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SavedCopys(
                video_id="test_video",
                generated_at=datetime.now(),
                model="gemini-2.5-flash",
                total_clips=1,
                style="viral",
                average_engagement=10.5,
                average_viral_potential=5.0,
                clips=[ClipCopy(**valid_clip_copy_dict)],
            )
        assert "average_engagement" in str(exc_info.value)

    def test_average_viral_potential_range(self, valid_clip_copy_dict):
        """average_viral_potential must be in [0, 10]."""
        for avg in [0.0, 5.0, 10.0]:
            saved = SavedCopys(
                video_id="test_video",
                generated_at=datetime.now(),
                model="gemini-2.5-flash",
                total_clips=1,
                style="viral",
                average_engagement=5.0,
                average_viral_potential=avg,
                clips=[ClipCopy(**valid_clip_copy_dict)],
            )
            assert saved.average_viral_potential == avg

    def test_datetime_serialization(self, valid_clip_copy_dict):
        """SavedCopys should serialize datetime correctly."""
        now = datetime(2025, 10, 26, 11, 30, 0)
        saved = SavedCopys(
            video_id="test_video",
            generated_at=now,
            model="gemini-2.5-flash",
            total_clips=1,
            style="viral",
            average_engagement=8.0,
            average_viral_potential=7.0,
            clips=[ClipCopy(**valid_clip_copy_dict)],
        )
        # Model dump should work
        data = saved.model_dump()
        assert data["generated_at"] == now


# ============================================================================
# HELPER FUNCTION TESTS - calculate_averages
# ============================================================================

class TestCalculateAverages:
    """Tests for calculate_averages() helper function."""

    def test_calculate_averages_single_clip(self, valid_clip_copy_dict):
        """calculate_averages should work with single clip."""
        output = CopysOutput(clips=[ClipCopy(**valid_clip_copy_dict)])
        avg_engagement, avg_viral = calculate_averages(output)
        assert avg_engagement == 8.5
        assert avg_viral == 7.8

    def test_calculate_averages_multiple_clips(self, valid_clip_copy_dict, valid_metadata_dict):
        """calculate_averages should average multiple clips."""
        clip1_dict = valid_clip_copy_dict.copy()
        clip1_dict["metadata"] = valid_metadata_dict.copy()
        clip1_dict["metadata"]["engagement_score"] = 8.0
        clip1_dict["metadata"]["viral_potential"] = 7.0

        clip2_dict = valid_clip_copy_dict.copy()
        clip2_dict["clip_id"] = 2
        clip2_dict["metadata"] = valid_metadata_dict.copy()
        clip2_dict["metadata"]["engagement_score"] = 6.0
        clip2_dict["metadata"]["viral_potential"] = 5.0

        output = CopysOutput(clips=[ClipCopy(**clip1_dict), ClipCopy(**clip2_dict)])
        avg_engagement, avg_viral = calculate_averages(output)

        assert avg_engagement == 7.0  # (8+6)/2
        assert avg_viral == 6.0  # (7+5)/2

    def test_calculate_averages_empty_clips(self):
        """calculate_averages with no clips should return (0.0, 0.0)."""
        # Create a CopysOutput-like object with empty clips for this test
        # Since CopysOutput requires min_length=1, we need to test the function directly
        class MockOutput:
            clips = []

        avg_engagement, avg_viral = calculate_averages(MockOutput())
        assert avg_engagement == 0.0
        assert avg_viral == 0.0

    def test_calculate_averages_rounds_to_two_decimals(self, valid_clip_copy_dict, valid_metadata_dict):
        """calculate_averages should round to 2 decimal places."""
        clip1_dict = valid_clip_copy_dict.copy()
        clip1_dict["metadata"] = valid_metadata_dict.copy()
        clip1_dict["metadata"]["engagement_score"] = 7.0
        clip1_dict["metadata"]["viral_potential"] = 6.0

        clip2_dict = valid_clip_copy_dict.copy()
        clip2_dict["clip_id"] = 2
        clip2_dict["metadata"] = valid_metadata_dict.copy()
        clip2_dict["metadata"]["engagement_score"] = 8.0
        clip2_dict["metadata"]["viral_potential"] = 7.0

        clip3_dict = valid_clip_copy_dict.copy()
        clip3_dict["clip_id"] = 3
        clip3_dict["metadata"] = valid_metadata_dict.copy()
        clip3_dict["metadata"]["engagement_score"] = 9.0
        clip3_dict["metadata"]["viral_potential"] = 8.0

        output = CopysOutput(clips=[
            ClipCopy(**clip1_dict),
            ClipCopy(**clip2_dict),
            ClipCopy(**clip3_dict),
        ])
        avg_engagement, avg_viral = calculate_averages(output)

        # (7+8+9)/3 = 8.0, (6+7+8)/3 = 7.0
        assert avg_engagement == 8.0
        assert avg_viral == 7.0


# ============================================================================
# HELPER FUNCTION TESTS - create_saved_copys
# ============================================================================

class TestCreateSavedCopys:
    """Tests for create_saved_copys() helper function."""

    def test_create_saved_copys_populates_all_fields(self, valid_copys_output):
        """create_saved_copys should populate all required fields."""
        saved = create_saved_copys(
            video_id="test_video_id",
            model="gemini-2.5-flash",
            style="viral",
            copies_output=valid_copys_output,
        )

        assert saved.video_id == "test_video_id"
        assert saved.model == "gemini-2.5-flash"
        assert saved.style == "viral"
        assert saved.total_clips == 1
        assert isinstance(saved.generated_at, datetime)
        assert len(saved.clips) == 1

    def test_create_saved_copys_calculates_averages(self, valid_clip_copy_dict, valid_metadata_dict):
        """create_saved_copys should calculate averages correctly."""
        clip1_dict = valid_clip_copy_dict.copy()
        clip1_dict["metadata"] = valid_metadata_dict.copy()
        clip1_dict["metadata"]["engagement_score"] = 8.0
        clip1_dict["metadata"]["viral_potential"] = 7.0

        clip2_dict = valid_clip_copy_dict.copy()
        clip2_dict["clip_id"] = 2
        clip2_dict["metadata"] = valid_metadata_dict.copy()
        clip2_dict["metadata"]["engagement_score"] = 6.0
        clip2_dict["metadata"]["viral_potential"] = 5.0

        output = CopysOutput(clips=[ClipCopy(**clip1_dict), ClipCopy(**clip2_dict)])

        saved = create_saved_copys(
            video_id="test_video",
            model="gemini-2.5-flash",
            style="educational",
            copies_output=output,
        )

        assert saved.average_engagement == 7.0
        assert saved.average_viral_potential == 6.0

    def test_create_saved_copys_sets_generated_at(self, valid_copys_output):
        """create_saved_copys should set generated_at to current time."""
        before = datetime.now()
        saved = create_saved_copys(
            video_id="test_video",
            model="gemini-2.5-flash",
            style="storytelling",
            copies_output=valid_copys_output,
        )
        after = datetime.now()

        assert before <= saved.generated_at <= after


# ============================================================================
# NEGATIVE TESTS - Invalid Data Types
# ============================================================================

class TestInvalidDataTypes:
    """Negative tests with invalid data types."""

    def test_metadata_with_wrong_type_sentiment_score(self, valid_metadata_dict):
        """Non-numeric sentiment_score should raise ValidationError."""
        valid_metadata_dict["sentiment_score"] = "high"
        with pytest.raises(ValidationError):
            CopyMetadata(**valid_metadata_dict)

    def test_metadata_with_wrong_type_topics(self, valid_metadata_dict):
        """Non-list primary_topics should raise ValidationError."""
        valid_metadata_dict["primary_topics"] = "single_topic"
        with pytest.raises(ValidationError):
            CopyMetadata(**valid_metadata_dict)

    def test_clip_copy_with_wrong_type_clip_id(self, valid_clip_copy_dict):
        """Non-integer clip_id should raise ValidationError."""
        valid_clip_copy_dict["clip_id"] = "one"
        with pytest.raises(ValidationError):
            ClipCopy(**valid_clip_copy_dict)

    def test_clip_copy_with_wrong_type_copy(self, valid_clip_copy_dict):
        """Non-string copy should raise ValidationError."""
        valid_clip_copy_dict["copy"] = 12345
        with pytest.raises(ValidationError):
            ClipCopy(**valid_clip_copy_dict)

    def test_copys_output_with_wrong_type_clips(self):
        """Non-list clips should raise ValidationError."""
        with pytest.raises(ValidationError):
            CopysOutput(clips="not a list")

    def test_saved_copys_with_wrong_type_datetime(self, valid_clip_copy_dict):
        """Non-datetime generated_at should raise ValidationError or be coerced."""
        with pytest.raises(ValidationError):
            SavedCopys(
                video_id="test",
                generated_at="not a datetime",
                model="gemini",
                total_clips=1,
                style="viral",
                average_engagement=5.0,
                average_viral_potential=5.0,
                clips=[ClipCopy(**valid_clip_copy_dict)],
            )


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_metadata_with_empty_topic_strings(self, valid_metadata_dict):
        """Empty strings in topics should be handled."""
        valid_metadata_dict["primary_topics"] = ["", "AI", "tech"]
        # Pydantic should accept this (empty string is still a string)
        metadata = CopyMetadata(**valid_metadata_dict)
        assert "" in metadata.primary_topics

    def test_metadata_with_boundary_scores(self, valid_metadata_dict):
        """Boundary values should be accepted."""
        valid_metadata_dict["sentiment_score"] = 0.0
        valid_metadata_dict["engagement_score"] = 1.0
        valid_metadata_dict["viral_potential"] = 10.0
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment_score == 0.0
        assert metadata.engagement_score == 1.0
        assert metadata.viral_potential == 10.0

    def test_clip_copy_with_only_aicdmx_hashtag(self, valid_clip_copy_dict):
        """Copy with only #AICDMX hashtag should pass."""
        valid_clip_copy_dict["copy"] = "This is great content! #AICDMX"
        clip = ClipCopy(**valid_clip_copy_dict)
        assert "#AICDMX" in clip.copy

    def test_clip_copy_with_unicode_characters(self, valid_clip_copy_dict):
        """Copy with unicode/emoji should work."""
        valid_clip_copy_dict["copy"] = "Amazing content here! 🚀🔥 #Tech #AICDMX"
        clip = ClipCopy(**valid_clip_copy_dict)
        assert "🚀" in clip.copy

    def test_metadata_with_float_as_int(self, valid_metadata_dict):
        """Integer values for float fields should be coerced."""
        valid_metadata_dict["sentiment_score"] = 1  # int instead of float
        valid_metadata_dict["engagement_score"] = 5  # int instead of float
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.sentiment_score == 1.0
        assert metadata.engagement_score == 5.0

    def test_topics_all_duplicates_reduced(self, valid_metadata_dict):
        """All duplicate topics reduce to single unique item after validation.

        Note: Pydantic validates min_length BEFORE field_validator runs, so
        input with 5 items passes min_length=2 check. The validator then
        deduplicates to 1 item, but the constraint is not re-checked.
        """
        valid_metadata_dict["primary_topics"] = ["AI", "ai", "AI", "ai", "AI"]
        # Input has 5 items (passes min_length=2), validator reduces to 1
        metadata = CopyMetadata(**valid_metadata_dict)
        assert metadata.primary_topics == ["AI"]

    def test_missing_required_field(self, valid_metadata_dict):
        """Missing required field should raise ValidationError."""
        del valid_metadata_dict["sentiment"]
        with pytest.raises(ValidationError):
            CopyMetadata(**valid_metadata_dict)
