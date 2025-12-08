# CLIPER Architecture

## System Overview

CLIPER is a production-grade agentic AI pipeline that transforms long-form video into publication-ready social media clips. It's not a collection of separate tools—it's an integrated system where each stage informs the next.

```
Long-Form Video
      ↓
   Transcription & Analysis
      ↓
   Semantic Understanding
      ↓
   Intelligent Segmentation
      ↓
   Agentic Caption Generation
      ↓
   Quality Validation
      ↓
   Computer Vision Optimization
      ↓
   Video Engineering & Export
      ↓
Publication-Ready Clips
```

---

## Stage 1: Transcription & Analysis

**Technology:** WhisperX (runs locally)

CLIPER transcribes video with precision word-level timing, enabling accurate subtitle synchronization. This foundation supports all downstream operations.

**Why This Matters:**
- Word-level timestamps enable perfect subtitle sync
- No generic transcription—accuracy directly impacts caption quality
- Local processing means no audio uploaded to external services

**Key Features:**
- Multiple model sizes (tiny → large)
- Language auto-detection
- Temporal precision for subtitle alignment

---

## Stage 2: Semantic Understanding

**Technology:** LLM-based analysis

Rather than fixed-duration chunks, CLIPER analyzes narrative structure to identify:
- Topic boundaries
- Thematic shifts
- Key insight moments
- Natural story arcs

**Result:** Clips that feel intentional, not algorithmic.

---

## Stage 3: Intelligent Segmentation

**Technology:** ClipsAI (runs locally)

Using semantic analysis, CLIPER identifies optimal clip boundaries. Each generated clip is a self-contained narrative unit, not a random time-based cut.

**Key Characteristics:**
- Topic-aware segmentation
- Natural narrative boundaries
- Respects MIN/MAX duration constraints
- Avoids cutting through important moments

---

## Stage 4: Agentic Caption Generation

**Technology:** LangGraph + Google Gemini

This is where CLIPER's AI sophistication shines. Rather than templates, it uses an agentic reasoning system:

1. **Classify** - Analyzes clip narrative context and optimal style
2. **Reason** - Determines caption style to maximize engagement
3. **Generate** - Creates contextually appropriate captions
4. **Validate** - Checks against brand guidelines
5. **Refine** - Improves outputs that don't meet standards

**Caption Styles:**
- **Viral** - Hook-driven, high-engagement language
- **Educational** - Value-focused, informative
- **Storytelling** - Narrative-driven, emotional appeal
- **Auto** - Lets AI decide based on content

**Multi-Step Reasoning:**
Each caption goes through multiple LLM passes, with the system reasoning about optimal wording, tone, and hooks. This produces captions that are simultaneously:
- On-brand
- Engaging
- Contextually appropriate
- Platform-optimized

---

## Stage 5: Quality Validation

**Technology:** Pydantic-based validation engine

Every output is validated against brand and content guidelines:

- Brand compliance (required hashtags, terminology)
- Length constraints (platform-specific)
- Content appropriateness
- Call-to-action presence
- Engagement potential

**Philosophy:** Better to publish 27 excellent clips than 30 mediocre ones.

---

## Stage 6: Computer Vision & ML-Based Reframing

**Technology:** Real-time object detection + frame analysis

Converting horizontal video to vertical without naive cropping. CLIPER uses ML to:

1. **Detect** - Identify key visual elements (faces, subjects, focal points)
2. **Analyze** - Understand frame composition and optimal framing
3. **Predict** - Anticipate subject movement
4. **Optimize** - Dynamically adjust crop windows throughout clip

**Why This Matters:**
- Static center-crop fails: cuts off speakers, wastes space, looks unprofessional
- ML-based approach maintains professional framing
- Keeps subjects centered and adapts to movement
- Represents actual computer vision, not heuristic shortcuts

---

## Stage 7: Video Engineering & Export

**Technology:** FFmpeg + professional codec optimization

The final stage combines all previous analysis into complete video engineering:

- **Temporal Precision** - Frame-accurate cutting
- **Aspect Ratio Optimization** - Perfect vertical formatting
- **Subtitle Synchronization** - Word-level timing
- **Audio Balancing** - Professional audio levels
- **Codec Optimization** - Platform-specific delivery

---

## Technology Stack

### Local Processing (Privacy-First)

- **WhisperX** - Local speech recognition with temporal precision
- **ClipsAI** - Local semantic segmentation
- **FFmpeg** - Professional video processing
- **OpenCV/MediaPipe** - Computer vision and frame analysis

### Cloud APIs (Strategic Use)

- **Google Gemini** - Agentic reasoning for captions and quality validation
- Cost-optimized: ~$0.02 per video (99 clips) with Gemini 2.0 Flash

### Architecture Patterns

- **Agentic AI** - Multi-step reasoning with state management via LangGraph
- **Pydantic Validation** - Type-safe configuration and output validation
- **Graceful Degradation** - If some stages fail, system continues
- **Resume Capability** - Interrupted processing can resume from last stage
- **Batch Processing** - 30+ clips simultaneously without cascading failures

---

## Key Design Principles

### Local-First Intelligence
Core ML models run locally for privacy and cost efficiency. Only strategic reasoning tasks use cloud APIs.

### Graceful Degradation
If captions don't meet validation standards, they're improved or skipped. Better 27 excellent clips than 30 mediocre ones.

### Modular Architecture
Each stage can be updated or configured independently without affecting the pipeline.

### Production Resilience
- Handles edge cases
- Supports partial failures
- Resume from any stage if interrupted
- Comprehensive logging and observability

### Intelligent Quality Gates
- Automatic validation against brand rules
- Rejection of low-quality outputs
- Iterative refinement through agentic reasoning

---

## Processing Flow

```
Input (YouTube URL or local file)
    ↓
[Download & Validation]
    ↓
[Transcription] → word-level timestamps
    ↓
[Semantic Analysis] → topic boundaries
    ↓
[Segmentation] → clip ranges
    ↓
[Caption Generation] → multiple agentic passes
    ↓
[Quality Validation] → brand compliance check
    ↓
[CV Reframing] → intelligent crop optimization
    ↓
[Video Export] → final clip files
    ↓
Output (organized by caption style)
```

---

## State Management

CLIPER maintains complete visibility into processing state:

- **Video Level**: Original file metadata, transcription, segments
- **Clip Level**: Timings, captions, style, validation results
- **Stage Results**: Success/failure status for each processing stage
- **Resume Info**: Allows continuing from any stage

This enables:
- Progress monitoring
- Debugging failed clips
- Reprocessing specific stages
- Production observability

---

## Performance Characteristics

- **Single Video**: 5-30 minutes depending on length and Whisper model
- **Batch Processing**: 30+ clips in parallel
- **GPU Acceleration**: Optional for transcription and CV stages
- **Memory Usage**: 4-8GB for typical processing

---

## Extensibility

CLIPER's modular design enables:

- Custom validation rules
- Brand-specific caption templates
- Specialized CV models
- Custom export formats
- Integration with external systems

Each component is independently configurable and replaceable.

---

## Error Handling & Resilience

- **Transient Failures**: Automatic retry with exponential backoff
- **Validation Failures**: Logged and skipped (no cascade failures)
- **Partial Completion**: Process can resume from last successful stage
- **Monitoring**: Comprehensive logging at each stage

---

## Production Deployment

For production systems:

1. **Environment Isolation** - Use `.env.production`
2. **Resource Management** - Configure batch sizes and GPU usage
3. **Monitoring** - Enable detailed logging
4. **Storage** - Separate input/output directories
5. **Docker** - Reproducible containerized deployment

See deployment guides in the main documentation.

---

**Need More Details?** Check the implementation in `cliper.py` for the full system architecture.
