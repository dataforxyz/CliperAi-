# -*- coding: utf-8 -*-

import json

import pytest

from src.speech_edge_clip import (
    SpeechEdgeTrimConfig,
    clip_speech_edges,
    compute_speech_aware_boundaries,
    find_speech_boundaries,
    load_transcript_segments,
)


def _write_transcript(tmp_path, words):
    transcript_path = tmp_path / "transcript.json"
    data = {
        "segments": [
            {
                "start": 0.0,
                "end": 100.0,
                "text": "",
                "words": words,
            }
        ],
        "word_segments": [],
    }
    transcript_path.write_text(json.dumps(data), encoding="utf-8")
    return str(transcript_path)


def test_speech_aware_trimming_keeps_silence_within_buffer(tmp_path):
    transcript_path = _write_transcript(tmp_path, [{"word": "hi", "start": 0.5, "end": 0.7}])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=0.0,
        clip_end=10.0,
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 0.0  # leading silence 0.5s < 1s buffer
    assert end == 1.7  # trailing silence 9.3s > 1s buffer => 1s after speech end


def test_speech_aware_trimming_trims_to_buffer(tmp_path):
    transcript_path = _write_transcript(tmp_path, [{"word": "hi", "start": 2.0, "end": 2.2}])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=0.0,
        clip_end=10.0,
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 1.0  # 1s before speech
    assert end == 3.2  # 1s after speech


def test_speech_aware_trimming_no_speech_noop(tmp_path):
    transcript_path = _write_transcript(tmp_path, [])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=5.0,
        clip_end=9.0,
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 5.0
    assert end == 9.0


def test_speech_aware_trimming_does_not_trim_into_overlapping_word(tmp_path):
    # Word overlaps clip start, so speech is "already happening" at clip_start.
    transcript_path = _write_transcript(tmp_path, [{"word": "hi", "start": 1.0, "end": 2.0}])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=1.5,
        clip_end=10.0,
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 1.5
    assert end == 3.0


# ============================================================================
# SpeechEdgeTrimConfig Tests
# ============================================================================


def test_speech_edge_trim_config_default_values():
    config = SpeechEdgeTrimConfig()
    assert config.trim_ms_start == 0
    assert config.trim_ms_end == 0


def test_speech_edge_trim_config_custom_values():
    config = SpeechEdgeTrimConfig(trim_ms_start=500, trim_ms_end=250)
    assert config.trim_ms_start == 500
    assert config.trim_ms_end == 250


def test_speech_edge_trim_config_is_frozen():
    config = SpeechEdgeTrimConfig(trim_ms_start=100, trim_ms_end=200)
    with pytest.raises(AttributeError):
        config.trim_ms_start = 300


# ============================================================================
# load_transcript_segments Tests
# ============================================================================


def test_load_transcript_segments_valid_file(tmp_path):
    transcript_path = tmp_path / "transcript.json"
    data = {
        "segments": [{"start": 0.0, "end": 1.0, "text": "hi", "words": []}],
        "word_segments": [{"word": "hi", "start": 0.0, "end": 0.5}],
    }
    transcript_path.write_text(json.dumps(data), encoding="utf-8")

    segments, word_segments = load_transcript_segments(str(transcript_path))
    assert len(segments) == 1
    assert segments[0]["text"] == "hi"
    assert len(word_segments) == 1
    assert word_segments[0]["word"] == "hi"


def test_load_transcript_segments_file_not_found():
    with pytest.raises(FileNotFoundError, match="Transcript not found"):
        load_transcript_segments("/nonexistent/path/transcript.json")


def test_load_transcript_segments_missing_keys_fallback(tmp_path):
    transcript_path = tmp_path / "transcript.json"
    data = {"other_key": "value"}
    transcript_path.write_text(json.dumps(data), encoding="utf-8")

    segments, word_segments = load_transcript_segments(str(transcript_path))
    assert segments == []
    assert word_segments == []


def test_load_transcript_segments_non_list_fallback(tmp_path):
    transcript_path = tmp_path / "transcript.json"
    data = {"segments": "not_a_list", "word_segments": 123}
    transcript_path.write_text(json.dumps(data), encoding="utf-8")

    segments, word_segments = load_transcript_segments(str(transcript_path))
    assert segments == []
    assert word_segments == []


# ============================================================================
# find_speech_boundaries Tests
# ============================================================================


def test_find_speech_boundaries_words_within_window():
    segments = [
        {
            "words": [
                {"word": "hello", "start": 2.0, "end": 2.5},
                {"word": "world", "start": 3.0, "end": 3.5},
            ]
        }
    ]
    result = find_speech_boundaries(segments, clip_start=0.0, clip_end=10.0)
    assert result == (2.0, 3.5)


def test_find_speech_boundaries_no_overlapping_words():
    segments = [
        {
            "words": [
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 1.0, "end": 1.5},
            ]
        }
    ]
    result = find_speech_boundaries(segments, clip_start=5.0, clip_end=10.0)
    assert result is None


def test_find_speech_boundaries_invalid_clip_range():
    segments = [{"words": [{"word": "hi", "start": 0.5, "end": 1.0}]}]
    result = find_speech_boundaries(segments, clip_start=10.0, clip_end=5.0)
    assert result is None


def test_find_speech_boundaries_clip_end_equals_clip_start():
    segments = [{"words": [{"word": "hi", "start": 5.0, "end": 5.5}]}]
    result = find_speech_boundaries(segments, clip_start=5.0, clip_end=5.0)
    assert result is None


def test_find_speech_boundaries_words_with_missing_timestamps():
    segments = [
        {
            "words": [
                {"word": "hi"},  # missing start/end
                {"word": "hello", "start": 2.0, "end": 2.5},
                {"word": "missing_end", "start": 3.0},  # missing end
                {"word": "missing_start", "end": 4.0},  # missing start
            ]
        }
    ]
    result = find_speech_boundaries(segments, clip_start=0.0, clip_end=10.0)
    assert result == (2.0, 2.5)  # Only valid word is used


def test_find_speech_boundaries_invalid_word_timestamps():
    segments = [
        {
            "words": [
                {"word": "invalid", "start": 5.0, "end": 4.0},  # end <= start
                {"word": "valid", "start": 2.0, "end": 2.5},
            ]
        }
    ]
    result = find_speech_boundaries(segments, clip_start=0.0, clip_end=10.0)
    assert result == (2.0, 2.5)


def test_find_speech_boundaries_word_overlaps_clip_start():
    segments = [{"words": [{"word": "hi", "start": 1.0, "end": 3.0}]}]
    result = find_speech_boundaries(segments, clip_start=2.0, clip_end=10.0)
    assert result == (2.0, 3.0)  # effective_start clamped to clip_start


def test_find_speech_boundaries_word_overlaps_clip_end():
    segments = [{"words": [{"word": "hi", "start": 8.0, "end": 12.0}]}]
    result = find_speech_boundaries(segments, clip_start=0.0, clip_end=10.0)
    assert result == (8.0, 10.0)  # effective_end clamped to clip_end


def test_find_speech_boundaries_with_word_segments():
    segments = [{"words": [{"word": "seg", "start": 2.0, "end": 2.5}]}]
    word_segments = [{"word": "extra", "start": 3.0, "end": 3.5}]
    result = find_speech_boundaries(segments, clip_start=0.0, clip_end=10.0, word_segments=word_segments)
    assert result == (2.0, 3.5)


def test_find_speech_boundaries_empty_segments():
    result = find_speech_boundaries([], clip_start=0.0, clip_end=10.0)
    assert result is None


# ============================================================================
# clip_speech_edges Tests
# ============================================================================


def test_clip_speech_edges_basic_trim():
    start, end = clip_speech_edges(
        start_time=0.0,
        end_time=10.0,
        trim_ms_start=500,
        trim_ms_end=500,
    )
    assert start == 0.5
    assert end == 9.5


def test_clip_speech_edges_zero_trim():
    start, end = clip_speech_edges(
        start_time=5.0,
        end_time=15.0,
        trim_ms_start=0,
        trim_ms_end=0,
    )
    assert start == 5.0
    assert end == 15.0


def test_clip_speech_edges_negative_trim_clamping():
    start, end = clip_speech_edges(
        start_time=0.0,
        end_time=10.0,
        trim_ms_start=-500,  # Negative should be treated as 0
        trim_ms_end=-500,
    )
    assert start == 0.0
    assert end == 10.0


def test_clip_speech_edges_over_trim_clamping():
    start, end = clip_speech_edges(
        start_time=0.0,
        end_time=1.0,  # 1 second duration
        trim_ms_start=2000,  # 2s > duration
        trim_ms_end=2000,
    )
    # Over-trim should clamp so that new_start doesn't exceed end
    assert start == 1.0
    assert end == 1.0


def test_clip_speech_edges_invalid_range():
    start, end = clip_speech_edges(
        start_time=10.0,
        end_time=5.0,  # Invalid: end < start
        trim_ms_start=100,
        trim_ms_end=100,
    )
    assert start == 10.0
    assert end == 10.0


def test_clip_speech_edges_zero_duration():
    start, end = clip_speech_edges(
        start_time=5.0,
        end_time=5.0,  # Zero duration
        trim_ms_start=100,
        trim_ms_end=100,
    )
    assert start == 5.0
    assert end == 5.0


def test_clip_speech_edges_trim_exceeds_midpoint():
    # Trim amounts exceed half the duration each
    start, end = clip_speech_edges(
        start_time=0.0,
        end_time=1.0,
        trim_ms_start=600,  # 0.6s
        trim_ms_end=600,  # 0.6s - total 1.2s > 1.0s duration
    )
    # Should clamp appropriately
    assert start == 0.6
    assert end == 0.6


# ============================================================================
# compute_speech_aware_boundaries Edge Case Tests
# ============================================================================


def test_compute_speech_aware_boundaries_zero_length_clip(tmp_path):
    transcript_path = _write_transcript(tmp_path, [{"word": "hi", "start": 5.0, "end": 5.5}])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=5.0,
        clip_end=5.0,  # Zero length
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 5.0
    assert end == 5.0


def test_compute_speech_aware_boundaries_both_trims_disabled(tmp_path):
    transcript_path = _write_transcript(tmp_path, [{"word": "hi", "start": 2.0, "end": 2.5}])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=0.0,
        clip_end=10.0,
        trim_ms_start=0,  # Disabled
        trim_ms_end=0,  # Disabled
    )
    # No trimming should occur
    assert start == 0.0
    assert end == 10.0


def test_compute_speech_aware_boundaries_missing_transcript(tmp_path):
    start, end = compute_speech_aware_boundaries(
        transcript_path=str(tmp_path / "nonexistent.json"),
        clip_start=0.0,
        clip_end=10.0,
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    # Should gracefully return original boundaries
    assert start == 0.0
    assert end == 10.0


def test_compute_speech_aware_boundaries_negative_clip_range(tmp_path):
    transcript_path = _write_transcript(tmp_path, [{"word": "hi", "start": 5.0, "end": 5.5}])
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=10.0,
        clip_end=5.0,  # Invalid: end < start
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 10.0
    assert end == 5.0

