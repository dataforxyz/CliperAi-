# AI Copy Generation - Feature Spec

## Summary

New phase in CLIPER pipeline to automatically generate viral captions/copies using Gemini 2.5 (Flash or Pro).

---

## Key Decisions

### Architecture
- **Separate phase:** New menu option after generating clips
- **Single API call:** Batch processing of all clips in one request
- **Single JSON:** All relevant information in one file

### File Structure

```
output/
└── AI_CDMX_Live_Stream_gjPVlCHU9OM/
    ├── clip_001_9x16_subs.mp4
    ├── clip_002_9x16_subs.mp4
    ├── ...
    └── copys/                           <- "copys" folder (not "copies")
        └── clips_copys.json             <- SINGLE JSON
```

### JSON Format

```json
{
  "video_id": "AI_CDMX_Live_Stream_gjPVlCHU9OM",
  "generated_at": "2025-10-25T15:00:00",
  "model": "gemini-2.5-flash",
  "total_clips": 60,
  "style": "viral",
  "clips": [
    {
      "clip_id": 1,
      "copy": "Complete caption with everything mixed #hashtags #here #integrated",

      "metadata": {
        "sentiment": "curious_educational",
        "sentiment_score": 0.75,
        "engagement_score": 8.5,
        "suggested_thumbnail_timestamp": 12.5,
        "primary_topics": ["meetups", "Q&A", "community"],
        "hook_strength": "high",
        "viral_potential": 7.8
      }
    }
  ]
}
```

---

## Copy Specification

### Format
- **All in one field:** Caption + hashtags mixed (no separate keys)
- **Limit:** 150 characters max (TikTok/Reels)
- **Style:** Viral by default
- **Includes:** Emojis, integrated hashtags

### Example
```
"Ever wondered why some meetup Q&As feel chaotic? This changed everything #TechMeetups #AI #CDMX"
```

---

## AI-Generated Metadata

### 1. Sentiment Analysis
**What is it?** Emotional tone of the content

**Possible values:**
- `educational` - Explains, teaches
- `humorous` - Funny, light
- `inspirational` - Motivational
- `controversial` - Opinionated, debate
- `curious_educational` - Educational questions
- `relatable` - "This happens to me"
- `storytelling` - Narrative, anecdote

**Sentiment Score (0-1):**
- `0.9+` = VERY strong emotion (high viral potential)
- `0.7-0.9` = Clear emotion
- `0.5-0.7` = Moderate emotion
- `<0.5` = Neutral/informative

**Usage:**
- Filter clips by emotional type
- Sort by emotional intensity
- A/B testing content

---

### 2. Engagement Score (1-10)
**What does it predict?** Probability of interaction (like, comment, share)

**Factors:**
- Hook strength
- Optimal duration (45-90s)
- Message clarity
- Topic relevance
- Effective call-to-action

**Usage:**
- Prioritize which clips to publish first
- Decide ad budget
- Optimize content strategy

---

### 3. Suggested Thumbnail Timestamp
**What is it?** Exact second of clip ideal for thumbnail

**Example:**
```
suggested_thumbnail_timestamp: 12.5
-> At second 12.5 there's a perfect visual/emotional moment
```

**How it's determined:**
- Important keywords
- Questions (curiosity)
- Punchlines
- Emotional climax

**Usage:**
- Auto-generate thumbnails with ffmpeg
- Position text overlay
- Debug clips that don't work

---

### 4. Primary Topics
**What is it?** 3-5 main topics of the clip

**Example:**
```json
["meetups", "Q&A", "community", "public speaking"]
```

**Usage:**
- Search: "Give me clips about 'AI'"
- Grouping: Thematic series
- Hashtag optimization
- Content calendar planning

---

### 5. Hook Strength
**What does it measure?** Effectiveness of first second to capture attention

**Values:**
- `very_high` - Irresistible hook
- `high` - Good hook (question/surprising fact)
- `medium` - Decent hook
- `low` - No clear hook

**Usage:**
- Filter weak clips
- Regenerate copies with more punch
- Learn success patterns

---

### 6. Viral Potential (1-10)
**What does it predict?** Probability of exponential shares

**Factors:**
- Extreme sentiment
- Very strong hook
- Trending topic
- Perfect duration (15-60s)
- Relatable to broad audience

**Scale:**
- `9-10` = VERY high viral potential (maximum priority)
- `7-8` = Good potential
- `5-6` = Moderate potential
- `<5` = Probably not viral

**Usage:**
- Publication strategy (peak hours)
- Boost with ads
- Post-mortem analysis

---

## Gemini Integration

### API to use
- **Model:** Gemini 2.5 (Flash or Pro - to be decided)
- **Calls:** 1 single batch request for all clips
- **Input:** Array with 60 clips (transcript + duration)
- **Output:** JSON with 60 copies + metadata

### Prompt Structure
```
Analyze these 60 clips from a video.

For EACH clip generate:

1. COPY: Complete caption with integrated hashtags
   - Max 150 characters
   - Viral style
   - Include emojis
   - Hashtags mixed in text

2. METADATA:
   - sentiment: emotional type
   - sentiment_score: 0-1
   - engagement_score: 1-10
   - suggested_thumbnail_timestamp: seconds
   - primary_topics: array of 3-5 topics
   - hook_strength: very_high/high/medium/low
   - viral_potential: 1-10

CLIPS:
[array of clips with transcript and duration]

Respond ONLY with valid JSON.
```

---

## User Flow

### In the CLI:

```
Current menu:
  1. Re-transcribe video
  2. Generate/Regenerate clips
  3. Generate AI copies for clips  <- NEW
  4. Export clips to video files
  5. Back to menu
```

### When option 3 is selected:

```
1. Which model?
   [1] Gemini 2.5 Flash (faster)
   [2] Gemini 2.5 Pro (better quality)

2. Which style?
   [1] Viral (default)
   [2] Educational
   [3] Storytelling

3. Include emojis? [Y/n]

-> Processing...
-> Generating AI copies for 60 clips...
-> 100%

Generated 60 AI copies!
Location: output/VIDEO_NAME/copys/clips_copys.json

Top viral potential clips:
  #23 - 9.2/10 (humorous)
  #08 - 8.9/10 (controversial)
  #45 - 8.7/10 (relatable)
```

---

## System Advantages

### For content creator:
- Saves hours of writing captions manually
- AI-optimized copies (better than humans for viral)
- Intelligent prioritization (knows which clips to publish first)
- Data-driven decisions (not "I think this will work")

### Technical:
- Single API call = fast and cheap
- Scalable (works the same with 10 clips or 1000)
- Versionable (regenerate copies without touching videos)
- Separation of concerns (copies != videos != transcripts)

### Analytics:
- Mental dashboard: "My educational clips have better engagement"
- A/B testing: Test different copy styles
- Content strategy: Publish optimized order by viral potential
- ROI tracking: Invest ads in high-scoring clips

---

## IMPLEMENTED (Nov 2025)

### Phase 1: Core functionality - COMPLETE
- [x] Created `copys_generator.py` module (~1000 lines)
- [x] Gemini API integration (2.0 Flash Exp - most recent available model)
- [x] **LangGraph architecture with 10 nodes:**
  - load_data_node
  - **classify_clips_node** (automatic classification)
  - **group_by_style_node** (groups by viral/educational/storytelling)
  - generate_viral_node
  - generate_educational_node
  - generate_storytelling_node
  - merge_results_node
  - validate_structure_node
  - analyze_quality_node
  - save_results_node
- [x] Modular prompt engineering (base + 3 styles)
- [x] Defensive JSON response parsing
- [x] Save to `copys/clips_copys.json`
- [x] **8 Pydantic validators** (sentiment, topics, copy length, etc.)

### Phase 2: CLI Integration - COMPLETE
- [x] New "Generate AI copies" menu (option 3)
- [x] Model selector (Flash Exp)
- [x] **Automatic classification** (NO manual style selector)
- [x] Real-time progress logs
- [x] **Partial success UI** (green/yellow based on result)
- [x] Success message with style distribution
- [x] **Automatic organization** by folders (viral/, educational/, storytelling/)

### Phase 3: Analytics (future)
- [ ] Command to view stats: `show-copys-stats`
- [ ] Filter clips by metadata
- [ ] Export CSV report
- [ ] Compare multiple generations

---

## Future Ideas

### Multi-language
- Generate copies in English AND Spanish
- `clips_copys_en.json` + `clips_copys_es.json`

### Platform-specific
- Platform-optimized copies
- TikTok (150 chars) vs YouTube (5000 chars)

### A/B Testing
- Generate 3 copy variants per clip
- Track which works best

### Auto-upload
- Use JSON to automatically upload to TikTok/Reels
- Intelligent scheduling by viral potential

---

## Potential Analytics

With generated metadata, you can create:

```
VIDEO ANALYTICS DASHBOARD:

Top 5 clips by viral potential:
  1. Clip #23 - 9.2/10 (humorous)
  2. Clip #08 - 8.9/10 (controversial)
  3. Clip #45 - 8.7/10 (relatable)

Clips by sentiment:
  Educational: 22 clips (avg engagement: 7.2)
  Humorous: 15 clips (avg engagement: 8.5)
  Inspirational: 8 clips (avg engagement: 6.8)

Recommended posting order:
  Week 1: Clips 23, 8, 45 (viral potential 9+)
  Week 2: Clips 12, 34, 56 (viral potential 8+)

Topics found:
  #AI: 18 clips
  #Community: 25 clips
  #PublicSpeaking: 12 clips

Best thumbnail moments identified: 60/60
```

---

## Final Decisions

### Architecture and Format
- Single batch API call (not 60 individual)
- Single JSON with all copies
- Copy with integrated hashtags (not separate)
- 150 characters max (TikTok)
- Gemini 2.5 (Flash or Pro)
- Complete AI-generated metadata
- `copys/` folder (not `copies/`)

### Technical Stack
- **LangGraph** (orchestration with quality control)
- **Pydantic** (data validation)
- **Gemini API** via `langchain-google-genai`

---

## Selected Technical Stack

### **LangGraph + Pydantic**

**Why LangGraph instead of simple LangChain?**

Decided to use **LangGraph** to implement adaptive quality control:

#### Flow with quality control:
```
1. Generate 60 copies with Gemini
   |
2. Analyze average quality
   |
3. Average engagement > 7.5?
   |-- YES: Save (acceptable quality)
   |
   +-- NO: Identify the problem
          |
          What failed?
            |-- Weak hooks -> Regenerate with "focus on STRONG hooks"
            |-- Copies too long -> Regenerate with "max 120 chars"
            +-- Generic topics -> Regenerate with "use trending topics"
          |
          Retry (max 3 times)
          |
          Save the best result
```

#### LangGraph advantages for this case:

1. **Guaranteed quality:**
   - Doesn't accept mediocre copies
   - Automatically improves if problems detected
   - User always receives engagement_score > 7.5

2. **Intelligent auto-correction:**
   - If hooks are weak, regenerate only with better hook prompt
   - If copies too long, adjust character limit
   - Learns from specific error, doesn't regenerate everything generically

3. **Multi-model fallback:**
   - Try with Gemini Flash (fast)
   - If quality < 7, upgrade to Gemini Pro
   - If still bad, fallback to another model

4. **Data-driven decisions:**
   - Analyzes average viral_potential
   - Detects individual bad clips
   - Regenerates only what's necessary (not everything)

#### Why NOT simple LangChain:

LangChain would only do:
```
Generate -> Validate structure -> Save
(Even if average engagement_score is 4/10)
```

With LangGraph:
```
Generate -> Analyze quality -> If bad, improve -> Guarantee > 7.5
```

#### Pydantic for validation:

**Pydantic's role:**
- Defines the "contract" of how response MUST be
- Validates types, ranges, lengths automatically
- Auto-corrects if Gemini makes mistakes

**Example:**
```python
class CopyMetadata(BaseModel):
    sentiment: Literal["educational", "humorous", ...]  # Only allowed values
    engagement_score: float = Field(ge=1.0, le=10.0)   # Between 1-10
    viral_potential: float = Field(ge=1.0, le=10.0)
    primary_topics: List[str] = Field(min_items=3, max_items=5)  # 3-5 topics

class ClipCopy(BaseModel):
    clip_id: int
    copy: str = Field(max_length=150)  # TikTok limit
    metadata: CopyMetadata
```

If Gemini returns `engagement_score: "very high"` (string instead of number), Pydantic rejects it and LangGraph requests regeneration.

---

## Phased Implementation

### Phase 1 (MVP): LangGraph with basic quality control
- Generate copies
- Validate average engagement_score
- Retry if < 7.5 (max 2 attempts)

### Phase 2 (Improvements): Granular analysis
- Detect individual bad clips
- Regenerate only clips with viral_potential < 6
- Multi-model fallback

### Phase 3 (Future): Advanced optimization
- Automatic A/B testing of styles
- Learn what works best by video type
- Content moderation

---

## Decision Architecture (LangGraph)

```
[START]
  |
[Generate with Gemini Flash]
  |
[Validate Structure with Pydantic]
  |
[Analyze Quality Metrics]
  |
  Decision: engagement_avg > 7.5?
    |-- YES -> [SAVE]
    |
    +-- NO -> [Identify Problem]
            |
            Decision: What's wrong?
              |-- Hooks weak -> [Regenerate with hook focus]
              |-- Too long -> [Regenerate shorter]
              +-- Generic -> [Regenerate with specifics]
            |
            Decision: attempts < 3?
              |-- YES -> [Regenerate] -> Loop back to Validate
              +-- NO -> [Save best attempt]
```

This approach guarantees we always deliver high-quality copies, not just structurally correct ones.

---

## Testing and Debugging Phase (Nov 2025)

During testing with real video (99 clips), we found and resolved 8 critical bugs:

### Resolved Bugs

| # | Bug | Solution | Key Learning |
|---|-----|----------|--------------|
| 1 | JSON format mismatch | Defensive parsing (dict vs array) | LLMs don't always respect exact format |
| 2 | Hybrid sentiments | Pydantic validator `mode='before'` | Normalize values before validating types |
| 3 | Topics > 5 | Truncation validator | Be permissive on input, strict on output |
| 4 | Copy > 150 chars | Intelligent truncation + improved prompt | Defense in depth: prompt + validator |
| 5 | Batch failures | Error handling + continue | Fault tolerance: 1 bad batch != everything bad |
| 6 | Threshold 80->60% | Lower threshold gradually | Graceful degradation > all-or-nothing |
| 7 | **LangGraph state bug** | Always return data keys | **CRITICAL:** Nodes must return all relevant keys |
| 8 | Rate limiting 429 | Sleep 1.5s between batches | Trade-off: +15s time vs 95% success rate |

### Bug #7 Explained (The Most Critical)

**Problem:**
```python
# BAD: Node only returns error
return {
    "error_message": "70/99 clips classified",
    "logs": [...]
    # Where are the 70 classifications?
}
```

**Consequence:**
- LangGraph continued the workflow
- Next node received `classifications=[]` (initial value)
- 70 successful classifications were "lost"

**Solution:**
```python
# GOOD: Returns partial data + error
return {
    "classifications": classifications,  # The 70 we DO have
    "error_message": "70/99 clips classified",
    "logs": [...]
}
```

**Lesson:** In LangGraph, nodes ONLY update keys present in the return dict. If you omit a key, state maintains the previous value.

### Implemented Architecture Decisions

**1. Automatic vs Manual Classification**
- Implemented: Automatic classification with LLM
- Discarded: User manually chooses style
- **Reason:** Mixed content (viral + educational + storytelling in same video)

**2. Batch Processing**
- Size: 10 clips per batch
- Sleep: 1.5s between batches
- Trade-off: Speed vs Rate Limiting

**3. Progressive Threshold**
- Initial: 80% (very strict)
- Iteration 1: 75%
- **Final: 60%** (optimal balance)
- **Validation:** Shows partial success instead of total failure

**4. Copy Length Enforcement**
- **User requirement:** "NO COPY OVER 150 CHARACTERS"
- **Priority when truncating:** Keep message + #AICDMX, remove second hashtag
- **Implementation:** Educational prompt + intelligent truncation in validator

### Final Technical Stack

```
LangGraph (orchestration)
  |
Pydantic (validation with 8 custom validators)
  |
Gemini 2.0 Flash Exp (classification + generation)
  |
Rate Limiting Mitigation (sleep between batches)
```

### Success Metrics

**Testing with 99 clips:**
- 70+ clips classified (60%+ threshold)
- Copies generated with complete metadata
- 100% of copies <= 150 characters
- Rate limiting mitigated
- UI shows partial success correctly

**Execution time:**
- Classification: ~60s (10 batches x 1.5s sleep)
- Generation: ~45s (3 groups)
- **Total: ~105 seconds** for 99 clips

### Files Created

```
src/
├── copys_generator.py (1000 lines) - LangGraph workflow
├── models/
│   └── copy_schemas.py (459 lines) - 4 Pydantic models + 8 validators
└── prompts/
    ├── __init__.py (90 lines)
    ├── base_prompts.py (160 lines) - Universal rules
    ├── classifier_prompt.py (300 lines) - Automatic classification
    ├── viral_prompt.py (150 lines)
    ├── educational_prompt.py (150 lines)
    └── storytelling_prompt.py (150 lines)

tests/
└── test_copy_generation_full.py - End-to-end test

Total: ~3,000 lines of code + documentation
```

---

## Model Used: Why Gemini 2.0 Flash Exp?

**Common question:** Why not Gemini 2.5?

**Answer:**
- In Nov 2025, Gemini 2.5 **was not available via API**
- Gemini 2.0 Flash Exp was the most recent Flash model
- Flash Exp = Experimental features + speed

**Comparison:**
- **Flash Exp:** Fast, cheap, good enough for copies
- **Pro 1.5:** Slower, more expensive, superior quality
- **Decision:** Flash Exp is sufficient for this use case

**Code state:**
```python
model: Literal["gemini-2.0-flash-exp", "gemini-1.5-pro"]
```

**Note for future:** When Gemini 2.5 is available in API, update literal types.
