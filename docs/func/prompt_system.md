# Prompt System Architecture

**Module:** `src/prompts/`

The prompt system is a sophisticated multi-layered architecture that generates AI copies for clips using Google Gemini. It consists of base prompts, style-specific prompts, and a classifier prompt that work together to create optimized captions for TikTok/Reels/Shorts.

## Architecture Overview

**Prompt Composition:**
```
Final Prompt = BASE_SYSTEM_PROMPT + STYLE_PROMPT + JSON_FORMAT_INSTRUCTIONS
```

The system uses a **two-stage approach**:
1. **Classification Stage:** Classifier analyzes all clips and assigns each one a style (viral/educational/storytelling)
2. **Generation Stage:** Clips are grouped by style and processed with style-specific prompts

## Core Components

### 1. Base System Prompt (`base_prompts.py`)

**Origin:** Handcrafted prompt engineering based on TikTok/Reels best practices

**Purpose:** Defines the fundamental "contract" for how Gemini should behave across ALL styles

**Key Rules Defined:**
- **Character Limit:** Strict 150-character maximum (TikTok limit)
- **Required Hashtag:** ALL copies MUST include #AICDMX (branding)
- **Code-Switching:** Natural Spanish + English mix for Latino tech audience
  - Structure in Spanish: "¿Sabías que...", "Cuando tu..."
  - Technical terms in English: "React hooks", "API", "debugging"
- **Emoji Usage:** 1-2 relevant emojis maximum
- **Hashtag Integration:** Mix hashtags naturally into copy, NOT at end
- **Metadata Requirements:** 7 required fields (sentiment, engagement_score, viral_potential, etc.)

**Constants:**
- `SYSTEM_PROMPT` - The main system instructions
- `JSON_FORMAT_INSTRUCTIONS` - Required output format specification

**Function:** `build_base_system_prompt(include_format: bool = True) -> str`
- Builds the base prompt with optional JSON format instructions
- Used by style prompts to compose final prompt

**Example Rules from Base Prompt:**
```
✅ CORRECT (148 chars):
"¿Cansado de Q&As dominados? 🎤 Este truco asegura que TODAS las preguntas se respondan #TechEvents #AICDMX"

❌ WRONG (165 chars - TOO LONG):
"¿Estás cansado de que los Q&A sessions sean dominados por una sola persona? Este increíble truco..."

✅ CORRECT (code-switching):
"Cuando tu code funciona en local pero no en prod 💀 #DevLife #AICDMX"

❌ WRONG (all English, no #AICDMX):
"When your code works locally but not in production"
```

### 2. Classifier Prompt (`classifier_prompt.py`)

**Origin:** Expert-designed classification criteria based on content analysis patterns

**Purpose:** Automatically detects the optimal style for each clip based on transcript content

**Function:** `get_classifier_prompt() -> str`
- Returns the classification prompt
- Used in `CopysGenerator.classify_clips_node()`

**Classification Criteria:**

**Viral Style (🔥)** - Assigned when clip contains:
- Surprising/counterintuitive data
- Provocative or controversial moments
- High-curiosity questions
- Relatable humor/frustration
- "Hot takes" or polarizing opinions
- Keywords: "sorprendente", "nadie habla de", "el 90% de..."

**Educational Style (📚)** - Assigned when clip contains:
- Technical concept explanations
- Tutorials or "how to" content
- Technical comparisons (X vs Y)
- Best practices or design patterns
- Problem-solving demonstrations
- Keywords: "cómo...", "qué es...", "diferencia entre..."

**Storytelling Style (📖)** - Assigned when clip contains:
- Personal experiences from speaker
- Journey or transformation narratives
- Anecdotes with lessons learned
- Emotional/vulnerable moments
- Career decisions or personal stories
- Keywords: "yo...", "mi...", "hace X años...", "el día que..."

**Output Format:**
```json
{
  "classifications": [
    {
      "clip_id": 1,
      "style": "viral",
      "confidence": 0.95,
      "reason": "Contains provocative question about common developer mistakes"
    }
  ]
}
```

**How It's Modified:**
- The classifier prompt is static and defined in `classifier_prompt.py`
- It receives dynamic input: list of clips with their transcripts
- Gemini processes and returns style classifications
- These classifications determine which style prompt to use for generation

### 3. Style-Specific Prompts

Each style has its own prompt file that extends the base prompt with style-specific instructions.

#### Viral Prompt (`viral_prompt.py`)

**Origin:** Optimized for maximum engagement using viral content formulas

**Constant:** `VIRAL_STYLE_PROMPT`

**Function:** `get_viral_prompt() -> str`
- Returns the viral-specific instructions
- Combined with base prompt by `get_prompt_for_style("viral")`

**Characteristics:**
- **Hook Formulas:**
  - Provocative questions: "¿Sabías que el 90% de devs hacen esto mal? 😱"
  - Contradictions: "Todos usan Docker, pero esto es más rápido 🚀"
  - Surprising data: "Este bug afectó a 3M usuarios y nadie lo notó 🤯"
  - Relatable moments: "POV: Llevas 6h debuggeando y el error era un typo"

- **Emotional Priorities:**
  - Extreme curiosity (sentiment_score > 0.8)
  - Surprise
  - Controlled controversy
  - FOMO (fear of missing out)

- **Expected Metrics:**
  - Hook strength: 80% should be "very_high" or "high"
  - Viral potential: Average 7.5+, identify clips with 9+ potential

- **Hashtag Strategy:** Trending + niche (e.g., #AICDMX #TechTwitter)

#### Educational Prompt (`educational_prompt.py`)

**Origin:** Designed for clear, value-focused educational content

**Constant:** `EDUCATIONAL_STYLE_PROMPT`

**Function:** `get_educational_prompt() -> str`

**Characteristics:**
- **Hook Formulas:**
  - Value promises: "3 React hooks que todo senior debe conocer"
  - Problem-solution: "Cómo debuggear memory leaks en 5 minutos"
  - Comparison: "async/await vs Promises: ¿cuál usar?"

- **Tone:**
  - Clear and direct
  - Less provocative, more informative
  - Focus on actionable learning

- **Expected Metrics:**
  - Engagement score: 7-9 range
  - Sentiment: "educational" or "curious_educational"
  - Hook strength: "high" or "medium" (doesn't need "very_high")

- **Hashtag Strategy:** Niche technical hashtags (e.g., #AICDMX #ReactJS)

#### Storytelling Prompt (`storytelling_prompt.py`)

**Origin:** Crafted for personal narrative and emotional connection

**Constant:** `STORYTELLING_STYLE_PROMPT`

**Function:** `get_storytelling_prompt() -> str`

**Characteristics:**
- **Hook Formulas:**
  - Personal vulnerability: "Mi breakup casi destruye mi project 💔"
  - Journey narrative: "Hace 2 años no sabía programar, hoy trabajo en Google"
  - Lesson learned: "El día que mi CTO me dijo que mi código era un desastre"

- **Tone:**
  - First-person perspective
  - Emotional authenticity
  - Relatable struggles and growth

- **Expected Metrics:**
  - Sentiment: "storytelling", "relatable", or "inspirational"
  - Engagement score: 7-9 range
  - Viral potential: 6-8 (connection over virality)

- **Hashtag Strategy:** Personal/career hashtags (e.g., #AICDMX #DevJourney)

### 4. Prompt Composition System (`__init__.py`)

**Module:** `src/prompts/__init__.py`

**Function:** `get_prompt_for_style(style: str = "viral") -> str`
- **Purpose:** Composes the complete prompt for a specific style
- **Process:**
  1. Validates style is valid ("viral", "educational", "storytelling")
  2. Builds base prompt using `build_base_system_prompt(include_format=True)`
  3. Gets style-specific prompt using style_prompts map
  4. Combines: `base_prompt + "\n\n" + style_prompt`
- **Returns:** Complete prompt ready to send to Gemini
- **Used By:** `CopysGenerator._generate_copies_for_style()`

**Function:** `get_available_styles() -> list[str]`
- Returns: `["viral", "educational", "storytelling"]`
- Used for validation and CLI display

## How Prompts Are Modified

**1. Static Base (No Runtime Modification):**
- Base prompts (`SYSTEM_PROMPT`, `VIRAL_STYLE_PROMPT`, etc.) are **hardcoded strings**
- These are **NOT modified** at runtime
- Changes require editing the source files

**2. Dynamic Composition:**
Prompts are composed dynamically by combining static pieces:
```python
# In CopysGenerator._generate_copies_for_style()
full_prompt = get_prompt_for_style(style)  # "viral", "educational", or "storytelling"

# This internally does:
# base_prompt = build_base_system_prompt(include_format=True)
# style_prompt = get_viral_prompt()  # or educational/storytelling
# return base_prompt + "\n\n" + style_prompt
```

**3. Dynamic Input Data:**
The composed prompt is sent to Gemini along with **dynamic clip data**:
```python
messages = [
    {"role": "user", "content": full_prompt},  # Static composed prompt
    {"role": "user", "content": json.dumps({    # Dynamic clip data
        "clips": [
            {
                "clip_id": 1,
                "text": "Transcript of clip 1...",
                "duration": 45.2
            },
            # ... more clips
        ]
    })}
]
```

**4. How to Customize Prompts:**

To modify prompt behavior, edit the source files:

- **Change base rules:** Edit `src/prompts/base_prompts.py` → `SYSTEM_PROMPT`
- **Change viral style:** Edit `src/prompts/viral_prompt.py` → `VIRAL_STYLE_PROMPT`
- **Change educational style:** Edit `src/prompts/educational_prompt.py` → `EDUCATIONAL_STYLE_PROMPT`
- **Change storytelling style:** Edit `src/prompts/storytelling_prompt.py` → `STORYTELLING_STYLE_PROMPT`
- **Change classification criteria:** Edit `src/prompts/classifier_prompt.py` → `CLASSIFIER_PROMPT`

**Example: Adding a new rule to base prompt:**
```python
# In base_prompts.py
SYSTEM_PROMPT = """Eres un experto en crear copies virales...

## Reglas CRÍTICAS:

### Formato del Copy:
- **CRÍTICO: MAX 150 CARACTERES**
- **NEW RULE: Always mention the speaker's name if available**  # ← ADD HERE
...
"""
```

## Integration with CopysGenerator

The prompt system integrates into the LangGraph workflow:

**Step 1: Classification** (`classify_clips_node`)
```python
prompt = get_classifier_prompt()  # From classifier_prompt.py
# Send to Gemini with clip transcripts
# Gemini returns: {clip_id: 1, style: "viral", confidence: 0.95, ...}
```

**Step 2: Grouping** (`group_by_style_node`)
```python
# Group clips by classified style
# viral_clips = [clip_1, clip_5, ...]
# educational_clips = [clip_2, clip_3, ...]
# storytelling_clips = [clip_4, ...]
```

**Step 3: Generation** (`generate_viral_node`, `generate_educational_node`, `generate_storytelling_node`)
```python
# In _generate_copies_for_style(clips, style="viral")
full_prompt = get_prompt_for_style("viral")  # Composed base + viral
# Send to Gemini with viral clips
# Returns copies optimized for viral engagement
```

**Step 4: Validation** (`validate_structure_node`)
```python
# Validates all copies meet requirements:
# - Character limit <= 150
# - Contains #AICDMX hashtag
# - All metadata fields present
# - Valid sentiment values
```

## Prompt Source Attribution

**Where Prompts Come From:**

1. **Base Prompt:** Expert-designed based on:
   - TikTok/Reels content creation best practices
   - Character limits and platform constraints
   - Code-switching patterns for Latino tech audience
   - Trial-and-error optimization with real content

2. **Style Prompts:** Derived from:
   - Analysis of successful viral/educational/storytelling content
   - Hook formulas that maximize engagement
   - Platform-specific trending patterns
   - Content creator expertise in each style

3. **Classifier Prompt:** Based on:
   - Content analysis patterns from thousands of tech videos
   - Natural language indicators for each style
   - Machine learning classification principles adapted to LLM prompting

**Prompt Evolution:**
- Prompts are **version controlled** in the codebase
- Changes are made through code edits and testing
- No runtime modification or learning
- Future enhancement: Could add prompt versioning/A-B testing system
