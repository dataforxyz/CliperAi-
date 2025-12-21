# Configuration

**Module:** `config/content_presets.py`

**Function:** `get_preset(content_type: str) -> Dict[str, Any]`
- **Purpose:** Gets configuration preset for content type
- **Inputs:** `content_type: str` ("podcast", "tutorial", "livestream", "documentary", "short_form")
- **Outputs:**
  ```python
  {
    "name": str,
    "description": str,
    "icon": str,
    "transcription": {
      "model_size": str,
      "enable_diarization": bool,
      "language": Optional[str]
    },
    "clips": {
      "method": str,
      "min_duration": int,
      "max_duration": int,
      "prefer_speaker_changes": bool
    },
    "use_case": str
  }
  ```

**Function:** `list_presets() -> Dict[str, str]`
- **Purpose:** Lists all available presets
- **Inputs:** None
- **Outputs:** `Dict[str, str]` (mapping key → "icon name")

**Function:** `get_preset_description(content_type: str) -> str`
- **Purpose:** Gets description for a preset
- **Inputs:** `content_type: str`
- **Outputs:** `str` (description)
- **Used By:** CLI prompts for adding/processing videos to suggest transcription model sizes, diarization flags, clip durations, and hybrid/fixed-time fallbacks (e.g., livestream preset enables fixed-time fallback).
