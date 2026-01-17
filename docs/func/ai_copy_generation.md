# AI Copy Generation

**Module:** `src/copys_generator.py`

### Class: `CopysGenerator`

**Function:** `__init__(video_id: str, model: Literal["gemini-2.0-flash-exp", "gemini-1.5-pro"] = "gemini-2.0-flash-exp", max_attempts: int = 3)`
- **Purpose:** Initialize AI copy generator with LangGraph workflow
- **Inputs:**
  - `video_id: str`
  - `model: str` (Gemini model name)
  - `max_attempts: int` (retry attempts if quality < 7.5)
- **Outputs:** None (initializes LangGraph workflow)

**Function:** `generate() -> Dict`
- **Purpose:** Executes full LangGraph workflow: classify → generate → validate → save
- **Inputs:** None (uses `video_id` from `__init__`)
- **Outputs:**
  ```python
  {
    "success": bool,
    "error": Optional[str],
    "output_file": Optional[str],  # path to clips_copys.json
    "metrics": {
      "total_copies": int,
      "total_classified": int,
      "average_engagement": float,  # 1-10
      "average_viral_potential": float,  # 1-10
      "distribution": {
        "viral": int,
        "educational": int,
        "storytelling": int
      }
    },
    "logs": List[str]  # process logs
  }
  ```
- **Side Effects:**
  - Reads `temp/{video_id}_clips.json`
  - Creates `output/{video_id}/copys/clips_copys.json`
- **Pipeline (LangGraph nodes):**
  - Loads clips metadata → classifies clips into styles → groups clips per style.
  - Generates copies per style (viral/educational/storytelling) using Gemini.
  - Validates structure + analyzes quality; auto-retries up to `max_attempts` if quality < 7.5.
  - Saves results/metrics and returns step-by-step logs for the UI.
- **Output File Format:**
  ```json
  {
    "video_id": "video_abc123",
    "generated_at": "2025-01-15T10:30:00",
    "model": "gemini-2.0-flash-exp",
    "total_clips": 10,
    "style": "auto-classified",
    "average_engagement": 8.5,
    "average_viral_potential": 7.2,
    "clips": [
      {
        "clip_id": 1,
        "copy": "Amazing content 🤯 #AI #Tech #AICDMX",
        "metadata": {
          "sentiment": "educational",
          "sentiment_score": 0.75,
          "engagement_score": 8.5,
          "suggested_thumbnail_timestamp": 12.5,
          "primary_topics": ["AI", "tech", "innovation"],
          "hook_strength": "high",
          "viral_potential": 7.8
        }
      }
    ],
    "classification_metadata": {
      "classifications": [
        {
          "clip_id": 1,
          "style": "viral",
          "confidence": 0.9,
          "reason": "..."
        }
      ],
      "distribution": {...}
    }
  }
  ```
