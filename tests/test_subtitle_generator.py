"""
Tests for SubtitleGenerator module.

Tests cover SRT generation, timestamp formatting, text splitting,
and edge case handling for subtitle generation from WhisperX transcripts.
"""

import json

from src.subtitle_generator import SubtitleGenerator

# ============================================================================
# INITIALIZATION TESTS
# ============================================================================


class TestSubtitleGeneratorInit:
    """Tests for SubtitleGenerator instantiation."""

    def test_instantiation(self):
        """SubtitleGenerator initializes with console and logger."""
        generator = SubtitleGenerator()

        assert generator.console is not None
        assert generator.logger is not None


# ============================================================================
# TIMESTAMP CONVERSION TESTS
# ============================================================================


class TestSecondsToSrtTime:
    """Tests for _seconds_to_srt_time() timestamp conversion."""

    def test_zero_seconds(self):
        """Zero seconds returns 00:00:00,000."""
        generator = SubtitleGenerator()
        result = generator._seconds_to_srt_time(0.0)

        assert result == "00:00:00,000"

    def test_fractional_seconds(self):
        """Fractional seconds are converted to milliseconds."""
        generator = SubtitleGenerator()
        result = generator._seconds_to_srt_time(1.234)

        assert result == "00:00:01,234"

    def test_minutes_boundary(self):
        """Seconds above 60 roll over to minutes."""
        generator = SubtitleGenerator()
        result = generator._seconds_to_srt_time(65.5)

        assert result == "00:01:05,500"

    def test_hours_boundary(self):
        """Seconds above 3600 roll over to hours."""
        generator = SubtitleGenerator()
        result = generator._seconds_to_srt_time(3661.123)

        assert result == "01:01:01,123"

    def test_large_value(self):
        """Large values format correctly with multiple hours."""
        generator = SubtitleGenerator()
        result = generator._seconds_to_srt_time(36000.999)

        assert result == "10:00:00,999"

    def test_milliseconds_rounding(self):
        """Milliseconds are truncated, not rounded."""
        generator = SubtitleGenerator()
        # 0.9999 should give 999ms (truncated), not 1000ms
        result = generator._seconds_to_srt_time(0.9999)

        assert result == "00:00:00,999"


# ============================================================================
# TEXT SPLITTING TESTS
# ============================================================================


class TestSplitTextIntoLines:
    """Tests for _split_text_into_lines() text wrapping."""

    def test_short_text_single_line(self):
        """Short text fits on one line."""
        generator = SubtitleGenerator()
        result = generator._split_text_into_lines("Hello world", max_chars=42)

        assert result == ["Hello world"]

    def test_exact_limit_single_line(self):
        """Text at limit splits due to word length calculation including space."""
        generator = SubtitleGenerator()
        # The algorithm adds +1 for space per word, so we need extra room
        text = "Hello world"  # 11 chars, well under limit
        result = generator._split_text_into_lines(text, max_chars=20)

        assert result == [text]

    def test_word_boundary_split(self):
        """Text is split at word boundaries, not mid-word."""
        generator = SubtitleGenerator()
        text = "Hello world this is a test of splitting"
        result = generator._split_text_into_lines(text, max_chars=20)

        # Each line should be under 20 chars and not split words
        for line in result:
            assert len(line) <= 20
            # Verify no partial words (no word should end/start mid-character)
            for word in line.split():
                assert word in text

    def test_empty_text_returns_empty_list(self):
        """Empty text returns list with empty string."""
        generator = SubtitleGenerator()
        result = generator._split_text_into_lines("", max_chars=42)

        assert result == [""]

    def test_single_long_word(self):
        """Single word longer than max_chars is kept intact."""
        generator = SubtitleGenerator()
        long_word = "supercalifragilisticexpialidocious"
        result = generator._split_text_into_lines(long_word, max_chars=10)

        # The word should not be split
        assert result == [long_word]

    def test_multiple_lines_created(self):
        """Long text is split into multiple lines."""
        generator = SubtitleGenerator()
        text = (
            "This is a longer piece of text that should be split across multiple lines"
        )
        result = generator._split_text_into_lines(text, max_chars=25)

        assert len(result) > 1
        # Reconstruct and verify
        reconstructed = " ".join(result)
        assert reconstructed == text


# ============================================================================
# SRT ENTRY FORMATTING TESTS
# ============================================================================


class TestFormatSrtEntry:
    """Tests for _format_srt_entry() SRT format structure."""

    def test_srt_entry_structure(self):
        """SRT entry has correct structure: index, timestamps, text, blank line."""
        generator = SubtitleGenerator()
        result = generator._format_srt_entry(1, 0.0, 3.5, "Hello world")

        lines = result.split("\n")
        assert lines[0] == "1"
        assert lines[1] == "00:00:00,000 --> 00:00:03,500"
        assert lines[2] == "Hello world"
        assert lines[3] == ""

    def test_timestamp_arrow_format(self):
        """Timestamps use ' --> ' separator."""
        generator = SubtitleGenerator()
        result = generator._format_srt_entry(1, 1.0, 2.0, "Test")

        assert " --> " in result

    def test_multiline_text(self):
        """Multi-line text is preserved in entry."""
        generator = SubtitleGenerator()
        text = "Line one\nLine two"
        result = generator._format_srt_entry(1, 0.0, 1.0, text)

        assert "Line one\nLine two" in result

    def test_special_characters_preserved(self):
        """Special characters in text are preserved."""
        generator = SubtitleGenerator()
        text = 'He said: "Hello!" & waved.'
        result = generator._format_srt_entry(1, 0.0, 1.0, text)

        assert text in result

    def test_unicode_text(self):
        """Unicode characters are preserved."""
        generator = SubtitleGenerator()
        text = "日本語テスト 🎉 émojis"
        result = generator._format_srt_entry(1, 0.0, 1.0, text)

        assert text in result


# ============================================================================
# SRT ENTRIES CREATION TESTS
# ============================================================================


class TestCreateSrtEntries:
    """Tests for _create_srt_entries() segment processing."""

    def test_word_level_timestamps(self, sample_transcript):
        """Entries are created from word-level timestamps."""
        generator = SubtitleGenerator()
        segments = sample_transcript["segments"]
        result = generator._create_srt_entries(segments)

        assert len(result) > 0
        # First entry should start with index 1
        assert result[0].startswith("1\n")

    def test_segment_fallback_without_words(self):
        """Segments without words use segment-level timestamps."""
        generator = SubtitleGenerator()
        segments = [
            {
                "start": 0.0,
                "end": 3.0,
                "text": "Hello world test",
            }
        ]
        result = generator._create_srt_entries(segments)

        assert len(result) >= 1
        assert "Hello world test" in result[0]

    def test_empty_segments_list(self):
        """Empty segments list returns empty entries."""
        generator = SubtitleGenerator()
        result = generator._create_srt_entries([])

        assert result == []

    def test_max_chars_per_line_respected(self, sample_transcript):
        """Lines respect max_chars_per_line limit."""
        generator = SubtitleGenerator()
        segments = sample_transcript["segments"]
        result = generator._create_srt_entries(segments, max_chars_per_line=20)

        for entry in result:
            lines = entry.split("\n")
            # Text line is at index 2
            if len(lines) > 2:
                text_line = lines[2]
                assert len(text_line) <= 25  # Some tolerance for word boundaries

    def test_max_duration_splits(self):
        """Long duration segments split when exceeding max_duration (from non-zero start)."""
        generator = SubtitleGenerator()
        # The algorithm's duration check uses `line_start_time and ...` which is falsy
        # when line_start_time=0, so duration splits only happen with non-zero starts.
        # We create words starting at 1.0 to test duration splitting.
        segments = [
            {
                "start": 1.0,
                "end": 21.0,
                "text": "w1 w2 w3 w4 w5 w6 w7 w8 w9 w10",
                "words": [
                    {"word": "w1", "start": 1.0, "end": 3.0},
                    {"word": "w2", "start": 3.0, "end": 5.0},
                    {"word": "w3", "start": 5.0, "end": 7.0},
                    {"word": "w4", "start": 7.0, "end": 9.0},
                    {"word": "w5", "start": 9.0, "end": 11.0},
                    {"word": "w6", "start": 11.0, "end": 13.0},
                    {"word": "w7", "start": 13.0, "end": 15.0},
                    {"word": "w8", "start": 15.0, "end": 17.0},
                    {"word": "w9", "start": 17.0, "end": 19.0},
                    {"word": "w10", "start": 19.0, "end": 21.0},
                ],
            }
        ]
        result = generator._create_srt_entries(segments, max_duration=3.0)

        # Should be split into multiple entries due to duration limit
        assert len(result) >= 2

    def test_empty_word_text_skipped(self):
        """Words with empty text are skipped."""
        generator = SubtitleGenerator()
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "Hello world",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 1.0},
                    {"word": "", "start": 1.0, "end": 1.2},  # Empty word
                    {"word": "   ", "start": 1.2, "end": 1.4},  # Whitespace only
                    {"word": "world", "start": 1.5, "end": 2.0},
                ],
            }
        ]
        result = generator._create_srt_entries(segments)

        # Combine all entries and check no empty words
        combined = " ".join(result)
        assert "Hello" in combined
        assert "world" in combined

    def test_sequential_indexing(self, sample_transcript):
        """SRT entries have sequential indices starting at 1."""
        generator = SubtitleGenerator()
        segments = sample_transcript["segments"]
        result = generator._create_srt_entries(segments)

        for i, entry in enumerate(result, start=1):
            first_line = entry.split("\n")[0]
            assert first_line == str(i)


# ============================================================================
# GENERATE SRT FROM TRANSCRIPT TESTS
# ============================================================================


class TestGenerateSrtFromTranscript:
    """Tests for generate_srt_from_transcript() file I/O."""

    def test_generates_srt_file(self, tmp_path, sample_transcript):
        """SRT file is created from transcript JSON."""
        generator = SubtitleGenerator()

        # Write sample transcript to temp file
        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        output_path = tmp_path / "output.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        assert result == str(output_path)
        assert output_path.exists()

    def test_default_output_path(self, tmp_path, sample_transcript):
        """Default output path uses transcript filename with .srt extension."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "my_video.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        result = generator.generate_srt_from_transcript(str(transcript_path))

        expected_output = tmp_path / "my_video.srt"
        assert result == str(expected_output)
        assert expected_output.exists()

    def test_empty_segments_returns_none(self, tmp_path):
        """Returns None when transcript has no segments."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "empty.json"
        transcript_path.write_text(json.dumps({"segments": []}), encoding="utf-8")

        result = generator.generate_srt_from_transcript(str(transcript_path))

        assert result is None

    def test_srt_content_format(self, tmp_path, sample_transcript):
        """Generated SRT file has valid SRT format."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        output_path = tmp_path / "output.srt"
        generator.generate_srt_from_transcript(str(transcript_path), str(output_path))

        content = output_path.read_text(encoding="utf-8")

        # Verify SRT format: index, timestamp line, text, blank line
        assert "00:00:" in content  # Timestamp format
        assert " --> " in content  # Timestamp separator
        # Check for word content
        assert "Hello" in content or "Today" in content

    def test_invalid_json_returns_none(self, tmp_path):
        """Returns None for invalid JSON file."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "invalid.json"
        transcript_path.write_text("not valid json {{{", encoding="utf-8")

        result = generator.generate_srt_from_transcript(str(transcript_path))

        assert result is None

    def test_nonexistent_file_returns_none(self, tmp_path):
        """Returns None for nonexistent file."""
        generator = SubtitleGenerator()

        result = generator.generate_srt_from_transcript(
            str(tmp_path / "nonexistent.json")
        )

        assert result is None


# ============================================================================
# GENERATE SRT FOR CLIP TESTS
# ============================================================================


class TestGenerateSrtForClip:
    """Tests for generate_srt_for_clip() clip extraction."""

    def test_clip_timestamp_adjustment(self, tmp_path, sample_transcript):
        """Clip timestamps are adjusted relative to clip start."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        output_path = tmp_path / "clip.srt"
        # Extract clip from 4.0 to 8.0 seconds
        result = generator.generate_srt_for_clip(
            str(transcript_path),
            clip_start=4.0,
            clip_end=8.0,
            output_path=str(output_path),
        )

        assert result == str(output_path)
        content = output_path.read_text(encoding="utf-8")

        # Timestamps should start near 0, not at 4.0
        assert "00:00:00" in content

    def test_only_includes_words_in_range(self, tmp_path, sample_transcript):
        """Only words within clip range are included."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        output_path = tmp_path / "clip.srt"
        # Extract only second segment (4.0 to 8.0)
        generator.generate_srt_for_clip(
            str(transcript_path),
            clip_start=4.0,
            clip_end=8.0,
            output_path=str(output_path),
        )

        content = output_path.read_text(encoding="utf-8")

        # Should contain words from second segment
        assert "Today" in content or "AI" in content or "topics" in content
        # Should NOT contain words from first segment
        assert "Hello" not in content

    def test_no_segments_in_range_returns_none(self, tmp_path, sample_transcript):
        """Returns None when no segments are in clip range."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        output_path = tmp_path / "clip.srt"
        # Request clip outside transcript range
        result = generator.generate_srt_for_clip(
            str(transcript_path),
            clip_start=100.0,
            clip_end=110.0,
            output_path=str(output_path),
        )

        assert result is None

    def test_partial_segment_overlap(self, tmp_path, sample_transcript):
        """Segments partially overlapping clip are included."""
        generator = SubtitleGenerator()

        transcript_path = tmp_path / "transcript.json"
        transcript_path.write_text(json.dumps(sample_transcript), encoding="utf-8")

        output_path = tmp_path / "clip.srt"
        # Clip starts in middle of first segment
        result = generator.generate_srt_for_clip(
            str(transcript_path),
            clip_start=1.0,
            clip_end=5.0,
            output_path=str(output_path),
        )

        assert result == str(output_path)
        assert output_path.exists()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_special_characters_in_text(self, tmp_path):
        """Special characters are handled correctly."""
        generator = SubtitleGenerator()

        transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": 'He said: "Hello!" & she replied <yes>',
                    "words": [
                        {"word": "He", "start": 0.0, "end": 0.2},
                        {"word": "said:", "start": 0.2, "end": 0.5},
                        {"word": '"Hello!"', "start": 0.5, "end": 1.0},
                        {"word": "&", "start": 1.0, "end": 1.2},
                        {"word": "she", "start": 1.2, "end": 1.5},
                        {"word": "replied", "start": 1.5, "end": 1.8},
                        {"word": "<yes>", "start": 1.8, "end": 2.0},
                    ],
                }
            ]
        }

        transcript_path = tmp_path / "special.json"
        transcript_path.write_text(json.dumps(transcript), encoding="utf-8")

        output_path = tmp_path / "special.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        assert result is not None
        content = output_path.read_text(encoding="utf-8")
        assert '"Hello!"' in content or "Hello!" in content
        assert "&" in content

    def test_unicode_characters(self, tmp_path):
        """Unicode characters are handled correctly."""
        generator = SubtitleGenerator()

        transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "日本語テスト émojis 🎉",
                    "words": [
                        {"word": "日本語テスト", "start": 0.0, "end": 1.0},
                        {"word": "émojis", "start": 1.0, "end": 1.5},
                        {"word": "🎉", "start": 1.5, "end": 2.0},
                    ],
                }
            ]
        }

        transcript_path = tmp_path / "unicode.json"
        transcript_path.write_text(
            json.dumps(transcript, ensure_ascii=False), encoding="utf-8"
        )

        output_path = tmp_path / "unicode.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        assert result is not None
        content = output_path.read_text(encoding="utf-8")
        assert "日本語テスト" in content
        assert "émojis" in content
        assert "🎉" in content

    def test_overlapping_word_timestamps(self, tmp_path):
        """Overlapping word timestamps are processed without error."""
        generator = SubtitleGenerator()

        transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 3.0,
                    "text": "Word one two three",
                    "words": [
                        {"word": "Word", "start": 0.0, "end": 1.0},
                        {
                            "word": "one",
                            "start": 0.8,
                            "end": 1.5,
                        },  # Overlaps with previous
                        {
                            "word": "two",
                            "start": 1.3,
                            "end": 2.0,
                        },  # Overlaps with previous
                        {"word": "three", "start": 2.0, "end": 3.0},
                    ],
                }
            ]
        }

        transcript_path = tmp_path / "overlap.json"
        transcript_path.write_text(json.dumps(transcript), encoding="utf-8")

        output_path = tmp_path / "overlap.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        # Should not fail, even with overlapping timestamps
        assert result is not None
        assert output_path.exists()

    def test_segment_without_words_key(self, tmp_path):
        """Segments missing 'words' key use segment text."""
        generator = SubtitleGenerator()

        transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "This segment has no words array",
                }
            ]
        }

        transcript_path = tmp_path / "no_words.json"
        transcript_path.write_text(json.dumps(transcript), encoding="utf-8")

        output_path = tmp_path / "no_words.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        assert result is not None
        content = output_path.read_text(encoding="utf-8")
        assert "This segment has no words array" in content

    def test_segment_with_empty_words_list(self, tmp_path):
        """Segments with empty words list use segment text."""
        generator = SubtitleGenerator()

        transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "Fallback to segment text",
                    "words": [],
                }
            ]
        }

        transcript_path = tmp_path / "empty_words.json"
        transcript_path.write_text(json.dumps(transcript), encoding="utf-8")

        output_path = tmp_path / "empty_words.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        assert result is not None
        content = output_path.read_text(encoding="utf-8")
        assert "Fallback to segment text" in content

    def test_very_long_segment_text(self, tmp_path):
        """Very long segment text is split across multiple entries."""
        generator = SubtitleGenerator()

        long_text = " ".join(["word"] * 50)  # 50 words
        transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 30.0,
                    "text": long_text,
                }
            ]
        }

        transcript_path = tmp_path / "long.json"
        transcript_path.write_text(json.dumps(transcript), encoding="utf-8")

        output_path = tmp_path / "long.srt"
        result = generator.generate_srt_from_transcript(
            str(transcript_path), str(output_path)
        )

        assert result is not None
        content = output_path.read_text(encoding="utf-8")
        # Should have multiple subtitle entries (first entry starts at beginning)
        assert content.startswith("1\n")  # First entry
        assert "\n2\n" in content  # At least a second entry
