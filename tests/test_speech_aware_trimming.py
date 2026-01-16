
import json

from src.speech_edge_clip import compute_speech_aware_boundaries


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
    transcript_path = _write_transcript(
        tmp_path, [{"word": "hi", "start": 0.5, "end": 0.7}]
    )
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
    transcript_path = _write_transcript(
        tmp_path, [{"word": "hi", "start": 2.0, "end": 2.2}]
    )
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
    transcript_path = _write_transcript(
        tmp_path, [{"word": "hi", "start": 1.0, "end": 2.0}]
    )
    start, end = compute_speech_aware_boundaries(
        transcript_path=transcript_path,
        clip_start=1.5,
        clip_end=10.0,
        trim_ms_start=1000,
        trim_ms_end=1000,
    )
    assert start == 1.5
    assert end == 3.0
