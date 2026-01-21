"""
Comprehensive pytest tests for src/copys_generator.py

Tests the 10-node LangGraph caption generation workflow:
1. load_data_node - Load clips metadata
2. classify_clips_node - Classify clips by style (viral/educational/storytelling)
3. group_by_style_node - Group clips by detected style
4. generate_viral_node - Generate viral copies
5. generate_educational_node - Generate educational copies
6. generate_storytelling_node - Generate storytelling copies
7. merge_results_node - Combine all copies
8. validate_structure_node - Validate #AICDMX and copy length
9. analyze_quality_node - Calculate quality metrics
10. save_results_node - Save to JSON file

Uses mock_gemini_client fixture for deterministic testing without API calls.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.models.copy_schemas import ClipCopy, CopyMetadata

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_clips_data():
    """
    Returns list of clip dicts with clip_id, transcript, duration.
    Simulates the clips_metadata.json structure.
    """
    return [
        {
            "clip_id": 1,
            "start_time": 0.0,
            "end_time": 30.0,
            "duration": 30.0,
            "transcript": "El 90% de los desarrolladores hacen esto mal cuando trabajan con APIs. Hoy te voy a enseñar cómo evitar este error común.",
        },
        {
            "clip_id": 2,
            "start_time": 30.0,
            "end_time": 60.0,
            "duration": 30.0,
            "transcript": "Cómo optimizar React hooks paso a paso. Primero necesitas entender cómo funciona el ciclo de vida de los componentes.",
        },
        {
            "clip_id": 3,
            "start_time": 60.0,
            "end_time": 90.0,
            "duration": 30.0,
            "transcript": "Mi primer bug en producción afectó a 10 mil usuarios. Fue el día más difícil de mi carrera, pero aprendí mucho.",
        },
        {
            "clip_id": 4,
            "start_time": 90.0,
            "end_time": 120.0,
            "duration": 30.0,
            "transcript": "¿Qué es la inteligencia artificial? Es una rama de la computación que permite a las máquinas aprender de datos.",
        },
        {
            "clip_id": 5,
            "start_time": 120.0,
            "end_time": 150.0,
            "duration": 30.0,
            "transcript": "Nadie habla de este problema en tech. El burnout está afectando a más del 60% de los desarrolladores.",
        },
    ]


@pytest.fixture
def mock_classification_response():
    """
    Returns JSON string with classifications array for sample clips.
    Covers all three styles: viral, educational, storytelling.
    """
    return json.dumps(
        {
            "classifications": [
                {
                    "clip_id": 1,
                    "style": "viral",
                    "confidence": 0.92,
                    "reason": "Dato provocativo '90% lo hace mal' genera curiosidad",
                },
                {
                    "clip_id": 2,
                    "style": "educational",
                    "confidence": 0.88,
                    "reason": "Tutorial paso a paso sobre React hooks",
                },
                {
                    "clip_id": 3,
                    "style": "storytelling",
                    "confidence": 0.95,
                    "reason": "Experiencia personal con journey emocional",
                },
                {
                    "clip_id": 4,
                    "style": "educational",
                    "confidence": 0.85,
                    "reason": "Explicación de concepto técnico (qué es IA)",
                },
                {
                    "clip_id": 5,
                    "style": "viral",
                    "confidence": 0.90,
                    "reason": "Tema controversial sobre burnout en tech",
                },
            ]
        }
    )


@pytest.fixture
def mock_copy_response_viral():
    """
    Returns JSON string with valid CopysOutput for viral clips.
    Includes #AICDMX hashtag as required by validators.
    """
    return json.dumps(
        {
            "clips": [
                {
                    "clip_id": 1,
                    "copy": "El 90% de los devs cometen este error fatal con APIs 💀 #AICDMX #Tech",
                    "metadata": {
                        "sentiment": "controversial",
                        "sentiment_score": 0.85,
                        "engagement_score": 8.5,
                        "suggested_thumbnail_timestamp": 5.0,
                        "primary_topics": ["APIs", "desarrollo", "errores"],
                        "hook_strength": "very_high",
                        "viral_potential": 8.8,
                    },
                },
                {
                    "clip_id": 5,
                    "copy": "Nadie habla de ESTO en tech... el burnout nos está destruyendo 😤 #AICDMX #DevLife",
                    "metadata": {
                        "sentiment": "controversial",
                        "sentiment_score": 0.90,
                        "engagement_score": 8.0,
                        "suggested_thumbnail_timestamp": 8.0,
                        "primary_topics": ["burnout", "tech", "salud mental"],
                        "hook_strength": "high",
                        "viral_potential": 8.2,
                    },
                },
            ]
        }
    )


@pytest.fixture
def mock_copy_response_educational():
    """
    Returns JSON string with valid CopysOutput for educational clips.
    """
    return json.dumps(
        {
            "clips": [
                {
                    "clip_id": 2,
                    "copy": "React Hooks: La guía que NECESITAS para optimizarlos correctamente 📚 #AICDMX #React",
                    "metadata": {
                        "sentiment": "educational",
                        "sentiment_score": 0.75,
                        "engagement_score": 7.8,
                        "suggested_thumbnail_timestamp": 3.0,
                        "primary_topics": ["React", "hooks", "optimización"],
                        "hook_strength": "high",
                        "viral_potential": 7.0,
                    },
                },
                {
                    "clip_id": 4,
                    "copy": "¿Qué es la IA? Te explico en 30 segundos lo que necesitas saber 🤖 #AICDMX #AI",
                    "metadata": {
                        "sentiment": "educational",
                        "sentiment_score": 0.70,
                        "engagement_score": 7.5,
                        "suggested_thumbnail_timestamp": 2.0,
                        "primary_topics": [
                            "inteligencia artificial",
                            "tech",
                            "educación",
                        ],
                        "hook_strength": "medium",
                        "viral_potential": 7.2,
                    },
                },
            ]
        }
    )


@pytest.fixture
def mock_copy_response_storytelling():
    """
    Returns JSON string with valid CopysOutput for storytelling clips.
    """
    return json.dumps(
        {
            "clips": [
                {
                    "clip_id": 3,
                    "copy": "Mi primer bug afectó a 10K usuarios... y así sobreviví 😰 #AICDMX #DevStories",
                    "metadata": {
                        "sentiment": "storytelling",
                        "sentiment_score": 0.88,
                        "engagement_score": 8.2,
                        "suggested_thumbnail_timestamp": 10.0,
                        "primary_topics": ["bugs", "carrera", "aprendizaje"],
                        "hook_strength": "very_high",
                        "viral_potential": 8.5,
                    },
                }
            ]
        }
    )


@pytest.fixture
def sample_clip_copies():
    """
    Returns list of ClipCopy objects for testing merge and validation nodes.
    """
    return [
        ClipCopy(
            clip_id=1,
            copy="El 90% de los devs cometen este error fatal con APIs 💀 #AICDMX #Tech",
            metadata=CopyMetadata(
                sentiment="controversial",
                sentiment_score=0.85,
                engagement_score=8.5,
                suggested_thumbnail_timestamp=5.0,
                primary_topics=["APIs", "desarrollo", "errores"],
                hook_strength="very_high",
                viral_potential=8.8,
            ),
        ),
        ClipCopy(
            clip_id=2,
            copy="React Hooks: La guía que NECESITAS para optimizarlos correctamente 📚 #AICDMX #React",
            metadata=CopyMetadata(
                sentiment="educational",
                sentiment_score=0.75,
                engagement_score=7.8,
                suggested_thumbnail_timestamp=3.0,
                primary_topics=["React", "hooks", "optimización"],
                hook_strength="high",
                viral_potential=7.0,
            ),
        ),
        ClipCopy(
            clip_id=3,
            copy="Mi primer bug afectó a 10K usuarios... y así sobreviví 😰 #AICDMX #DevStories",
            metadata=CopyMetadata(
                sentiment="storytelling",
                sentiment_score=0.88,
                engagement_score=8.2,
                suggested_thumbnail_timestamp=10.0,
                primary_topics=["bugs", "carrera", "aprendizaje"],
                hook_strength="very_high",
                viral_potential=8.5,
            ),
        ),
    ]


@pytest.fixture
def clips_metadata_file(tmp_path, sample_clips_data):
    """
    Creates a temporary clips metadata JSON file.
    Returns the path and temp directory.
    """
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    video_id = "test_video_123"
    clips_file = temp_dir / f"{video_id}_clips.json"

    # Convert sample_clips_data to the expected format with full_text
    clips_with_full_text = []
    for clip in sample_clips_data:
        clips_with_full_text.append(
            {
                "clip_id": clip["clip_id"],
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "duration": clip["duration"],
                "full_text": clip["transcript"],
            }
        )

    clips_file.write_text(
        json.dumps({"clips": clips_with_full_text}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {"path": clips_file, "temp_dir": temp_dir, "video_id": video_id}


# ============================================================================
# TEST: CopysGenerator INITIALIZATION
# ============================================================================


class TestCopysGeneratorInitialization:
    """Tests for CopysGenerator class initialization."""

    def test_copys_generator_initialization_default_model(self, monkeypatch):
        """Verify default model and path setup."""
        # Patch the ChatGoogleGenerativeAI to avoid API calls
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        assert generator.video_id == "test_video"
        assert generator.model == "gemini-2.0-flash-exp"
        assert generator.max_attempts == 3
        assert generator.temp_dir == Path("temp")
        assert generator.output_dir == Path("output") / "test_video"
        assert generator.copys_dir == Path("output") / "test_video" / "copys"

    def test_copys_generator_initialization_custom_model(self, monkeypatch):
        """Verify custom model configuration."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(
            video_id="custom_video", model="gemini-1.5-pro", max_attempts=5
        )

        assert generator.model == "gemini-1.5-pro"
        assert generator.max_attempts == 5

    def test_copys_generator_graph_building(self, monkeypatch):
        """Verify that the graph is built with all nodes."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Graph should be compiled (not None)
        assert generator.graph is not None


# ============================================================================
# TEST: LOAD_DATA_NODE
# ============================================================================


class TestLoadDataNode:
    """Tests for load_data_node."""

    def test_load_data_node_success(self, monkeypatch, clips_metadata_file):
        """Verify successful loading of clips metadata."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id=clips_metadata_file["video_id"])
        generator.temp_dir = clips_metadata_file["temp_dir"]

        state = {
            "video_id": clips_metadata_file["video_id"],
            "clips_data": [],
            "logs": [],
        }

        result = generator.load_data_node(state)

        assert "clips_data" in result
        assert len(result["clips_data"]) == 5
        assert result["clips_data"][0]["clip_id"] == 1
        assert "transcript" in result["clips_data"][0]
        assert "Cargados 5 clips" in result["logs"][0]

    def test_load_data_node_file_not_found(self, monkeypatch, tmp_path):
        """Verify error handling when clips file doesn't exist."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="nonexistent_video")
        generator.temp_dir = tmp_path / "temp"

        state = {"video_id": "nonexistent_video", "clips_data": [], "logs": []}

        result = generator.load_data_node(state)

        assert "error_message" in result
        assert "Archivo no encontrado" in result["error_message"]


# ============================================================================
# TEST: CLASSIFY_CLIPS_NODE
# ============================================================================


class TestClassifyClipsNode:
    """Tests for classify_clips_node."""

    def test_classify_clips_node_success(
        self, monkeypatch, sample_clips_data, mock_classification_response
    ):
        """Verify successful classification of clips with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = mock_classification_response

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"clips_data": sample_clips_data, "logs": []}

        result = generator.classify_clips_node(state)

        assert "classifications" in result
        assert len(result["classifications"]) == 5

        # Check that all styles are present
        styles = [c["style"] for c in result["classifications"]]
        assert "viral" in styles
        assert "educational" in styles
        assert "storytelling" in styles

    def test_classify_clips_node_partial_success(self, monkeypatch, sample_clips_data):
        """Verify graceful degradation with >60% classification success."""
        # Only return classifications for 4 out of 5 clips (80%)
        partial_response = json.dumps(
            {
                "classifications": [
                    {
                        "clip_id": 1,
                        "style": "viral",
                        "confidence": 0.9,
                        "reason": "Test",
                    },
                    {
                        "clip_id": 2,
                        "style": "educational",
                        "confidence": 0.85,
                        "reason": "Test",
                    },
                    {
                        "clip_id": 3,
                        "style": "storytelling",
                        "confidence": 0.92,
                        "reason": "Test",
                    },
                    {
                        "clip_id": 4,
                        "style": "educational",
                        "confidence": 0.88,
                        "reason": "Test",
                    },
                    # clip_id 5 is missing
                ]
            }
        )

        mock_response = MagicMock()
        mock_response.content = partial_response

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"clips_data": sample_clips_data, "logs": []}

        result = generator.classify_clips_node(state)

        # Should succeed since 4/5 = 80% > 60% threshold
        assert "error_message" not in result
        assert len(result["classifications"]) == 4

    def test_classify_clips_node_insufficient_classifications(
        self, monkeypatch, sample_clips_data
    ):
        """Verify failure when <60% clips are classified."""
        # Only return classifications for 2 out of 5 clips (40%)
        insufficient_response = json.dumps(
            {
                "classifications": [
                    {
                        "clip_id": 1,
                        "style": "viral",
                        "confidence": 0.9,
                        "reason": "Test",
                    },
                    {
                        "clip_id": 2,
                        "style": "educational",
                        "confidence": 0.85,
                        "reason": "Test",
                    },
                ]
            }
        )

        mock_response = MagicMock()
        mock_response.content = insufficient_response

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"clips_data": sample_clips_data, "logs": []}

        result = generator.classify_clips_node(state)

        # Should fail since 2/5 = 40% < 60% threshold
        assert "error_message" in result
        assert "2/5" in result["error_message"]

    def test_classify_clips_node_handles_markdown_json(
        self, monkeypatch, sample_clips_data
    ):
        """Verify that ```json markdown wrapping is cleaned."""
        wrapped_response = """```json
{
    "classifications": [
        {"clip_id": 1, "style": "viral", "confidence": 0.9, "reason": "Test"},
        {"clip_id": 2, "style": "educational", "confidence": 0.85, "reason": "Test"},
        {"clip_id": 3, "style": "storytelling", "confidence": 0.92, "reason": "Test"},
        {"clip_id": 4, "style": "educational", "confidence": 0.88, "reason": "Test"},
        {"clip_id": 5, "style": "viral", "confidence": 0.87, "reason": "Test"}
    ]
}
```"""

        mock_response = MagicMock()
        mock_response.content = wrapped_response

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"clips_data": sample_clips_data, "logs": []}

        result = generator.classify_clips_node(state)

        assert "classifications" in result
        assert len(result["classifications"]) == 5

    def test_classify_clips_node_handles_list_format(
        self, monkeypatch, sample_clips_data
    ):
        """Verify handling when Gemini returns array instead of {classifications: [...]}."""
        # Gemini sometimes returns just the array
        list_response = json.dumps(
            [
                {"clip_id": 1, "style": "viral", "confidence": 0.9, "reason": "Test"},
                {
                    "clip_id": 2,
                    "style": "educational",
                    "confidence": 0.85,
                    "reason": "Test",
                },
                {
                    "clip_id": 3,
                    "style": "storytelling",
                    "confidence": 0.92,
                    "reason": "Test",
                },
                {
                    "clip_id": 4,
                    "style": "educational",
                    "confidence": 0.88,
                    "reason": "Test",
                },
                {"clip_id": 5, "style": "viral", "confidence": 0.87, "reason": "Test"},
            ]
        )

        mock_response = MagicMock()
        mock_response.content = list_response

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"clips_data": sample_clips_data, "logs": []}

        result = generator.classify_clips_node(state)

        assert "classifications" in result
        assert len(result["classifications"]) == 5


# ============================================================================
# TEST: GROUP_BY_STYLE_NODE
# ============================================================================


class TestGroupByStyleNode:
    """Tests for group_by_style_node."""

    def test_group_by_style_node(self, monkeypatch, sample_clips_data):
        """Verify clips are grouped correctly into viral/educational/storytelling."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        classifications = [
            {"clip_id": 1, "style": "viral", "confidence": 0.9, "reason": "Test"},
            {
                "clip_id": 2,
                "style": "educational",
                "confidence": 0.85,
                "reason": "Test",
            },
            {
                "clip_id": 3,
                "style": "storytelling",
                "confidence": 0.92,
                "reason": "Test",
            },
            {
                "clip_id": 4,
                "style": "educational",
                "confidence": 0.88,
                "reason": "Test",
            },
            {"clip_id": 5, "style": "viral", "confidence": 0.87, "reason": "Test"},
        ]

        state = {
            "clips_data": sample_clips_data,
            "classifications": classifications,
            "logs": [],
        }

        result = generator.group_by_style_node(state)

        assert "grouped_clips" in result
        grouped = result["grouped_clips"]

        assert len(grouped["viral"]) == 2
        assert len(grouped["educational"]) == 2
        assert len(grouped["storytelling"]) == 1

        # Verify clip_ids are in correct groups
        viral_ids = [c["clip_id"] for c in grouped["viral"]]
        assert 1 in viral_ids
        assert 5 in viral_ids

        educational_ids = [c["clip_id"] for c in grouped["educational"]]
        assert 2 in educational_ids
        assert 4 in educational_ids

    def test_group_by_style_node_skips_missing_clips(
        self, monkeypatch, sample_clips_data
    ):
        """Verify that classifications for non-existent clips are skipped."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Include a classification for non-existent clip_id 99
        classifications = [
            {"clip_id": 1, "style": "viral", "confidence": 0.9, "reason": "Test"},
            {
                "clip_id": 99,
                "style": "viral",
                "confidence": 0.9,
                "reason": "Should be skipped",
            },
        ]

        state = {
            "clips_data": sample_clips_data,
            "classifications": classifications,
            "logs": [],
        }

        result = generator.group_by_style_node(state)

        # Only clip_id 1 should be in viral group
        assert len(result["grouped_clips"]["viral"]) == 1
        assert result["grouped_clips"]["viral"][0]["clip_id"] == 1


# ============================================================================
# TEST: GENERATE_*_NODE (viral, educational, storytelling)
# ============================================================================


class TestGenerateNodes:
    """Tests for generate_viral_node, generate_educational_node, generate_storytelling_node."""

    def test_generate_viral_node(
        self, monkeypatch, sample_clips_data, mock_copy_response_viral
    ):
        """Verify viral copy generation with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = mock_copy_response_viral

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        viral_clips = [
            {**sample_clips_data[0], "classification": {"style": "viral"}},
            {**sample_clips_data[4], "classification": {"style": "viral"}},
        ]

        state = {
            "grouped_clips": {
                "viral": viral_clips,
                "educational": [],
                "storytelling": [],
            },
            "logs": [],
        }

        result = generator.generate_viral_node(state)

        assert "viral_copies" in result
        assert len(result["viral_copies"]) == 2
        assert result["viral_copies"][0].clip_id == 1
        assert "#AICDMX" in result["viral_copies"][0].copy_text.upper()

    def test_generate_educational_node(
        self, monkeypatch, sample_clips_data, mock_copy_response_educational
    ):
        """Verify educational copy generation with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = mock_copy_response_educational

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        educational_clips = [
            {**sample_clips_data[1], "classification": {"style": "educational"}},
            {**sample_clips_data[3], "classification": {"style": "educational"}},
        ]

        state = {
            "grouped_clips": {
                "viral": [],
                "educational": educational_clips,
                "storytelling": [],
            },
            "logs": [],
        }

        result = generator.generate_educational_node(state)

        assert "educational_copies" in result
        assert len(result["educational_copies"]) == 2
        assert result["educational_copies"][0].clip_id == 2

    def test_generate_storytelling_node(
        self, monkeypatch, sample_clips_data, mock_copy_response_storytelling
    ):
        """Verify storytelling copy generation with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = mock_copy_response_storytelling

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        storytelling_clips = [
            {**sample_clips_data[2], "classification": {"style": "storytelling"}}
        ]

        state = {
            "grouped_clips": {
                "viral": [],
                "educational": [],
                "storytelling": storytelling_clips,
            },
            "logs": [],
        }

        result = generator.generate_storytelling_node(state)

        assert "storytelling_copies" in result
        assert len(result["storytelling_copies"]) == 1
        assert result["storytelling_copies"][0].clip_id == 3

    def test_generate_copies_empty_group(self, monkeypatch):
        """Verify empty group returns empty list."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {
            "grouped_clips": {"viral": [], "educational": [], "storytelling": []},
            "logs": [],
        }

        result = generator.generate_viral_node(state)

        assert result["viral_copies"] == []
        assert "Sin clips virales" in result["logs"][0]


# ============================================================================
# TEST: MERGE_RESULTS_NODE
# ============================================================================


class TestMergeResultsNode:
    """Tests for merge_results_node."""

    def test_merge_results_node(
        self, monkeypatch, sample_clips_data, sample_clip_copies
    ):
        """Verify all copies are combined and sorted by clip_id."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Split copies into groups
        viral = [sample_clip_copies[0]]  # clip_id 1
        educational = [sample_clip_copies[1]]  # clip_id 2
        storytelling = [sample_clip_copies[2]]  # clip_id 3

        state = {
            "clips_data": sample_clips_data[:3],  # Only 3 clips
            "viral_copies": viral,
            "educational_copies": educational,
            "storytelling_copies": storytelling,
            "logs": [],
        }

        result = generator.merge_results_node(state)

        assert "all_copies" in result
        assert len(result["all_copies"]) == 3

        # Verify sorted by clip_id
        ids = [c.clip_id for c in result["all_copies"]]
        assert ids == [1, 2, 3]

    def test_merge_results_node_partial_copies(
        self, monkeypatch, sample_clips_data, sample_clip_copies
    ):
        """Verify warning when not all clips have copies."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Only 2 copies for 5 clips
        state = {
            "clips_data": sample_clips_data,  # 5 clips
            "viral_copies": [sample_clip_copies[0]],  # 1 copy
            "educational_copies": [sample_clip_copies[1]],  # 1 copy
            "storytelling_copies": [],
            "logs": [],
        }

        result = generator.merge_results_node(state)

        # Should still return the copies we have (graceful degradation)
        assert len(result["all_copies"]) == 2
        # Should have warning in logs
        assert any("Generación parcial" in log for log in result["logs"])


# ============================================================================
# TEST: VALIDATE_STRUCTURE_NODE
# ============================================================================


class TestValidateStructureNode:
    """Tests for validate_structure_node."""

    def test_validate_structure_node_success(self, monkeypatch, sample_clip_copies):
        """Verify validation passes for valid copies with #AICDMX."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"all_copies": sample_clip_copies, "logs": []}

        result = generator.validate_structure_node(state)

        assert "error_message" not in result
        assert "Validación exitosa" in result["logs"][0]

    def test_validate_structure_node_missing_hashtag(self, monkeypatch):
        """Verify detection of missing #AICDMX hashtag."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Create copy without #AICDMX (bypass Pydantic validator by modifying after creation)
        copy_obj = ClipCopy(
            clip_id=1,
            copy="Test copy with #AICDMX hashtag here",
            metadata=CopyMetadata(
                sentiment="educational",
                sentiment_score=0.75,
                engagement_score=7.5,
                suggested_thumbnail_timestamp=5.0,
                primary_topics=["test", "topics", "here"],
                hook_strength="medium",
                viral_potential=7.0,
            ),
        )
        # Manually override copy_text to remove hashtag (simulating bad data)
        object.__setattr__(copy_obj, "copy_text", "Test copy without branding hashtag")

        state = {"all_copies": [copy_obj], "logs": []}

        result = generator.validate_structure_node(state)

        assert "error_message" in result
        assert "falta #AICDMX" in result["error_message"]

    def test_validate_structure_node_short_copy(self, monkeypatch):
        """Verify detection of copy too short (<20 chars)."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Create copy with short text (bypass validator)
        copy_obj = ClipCopy(
            clip_id=1,
            copy="Short copy #AICDMX that is valid length",
            metadata=CopyMetadata(
                sentiment="educational",
                sentiment_score=0.75,
                engagement_score=7.5,
                suggested_thumbnail_timestamp=5.0,
                primary_topics=["test", "topics", "here"],
                hook_strength="medium",
                viral_potential=7.0,
            ),
        )
        # Manually override copy_text to be too short
        object.__setattr__(copy_obj, "copy_text", "Short #AICDMX")  # 13 chars

        state = {"all_copies": [copy_obj], "logs": []}

        result = generator.validate_structure_node(state)

        assert "error_message" in result
        assert "copy muy corto" in result["error_message"]


# ============================================================================
# TEST: ANALYZE_QUALITY_NODE
# ============================================================================


class TestAnalyzeQualityNode:
    """Tests for analyze_quality_node."""

    def test_analyze_quality_node(
        self, monkeypatch, sample_clips_data, sample_clip_copies
    ):
        """Verify engagement/viral averages and low_quality_clips calculation."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {
            "clips_data": sample_clips_data[:3],  # 3 clips
            "all_copies": sample_clip_copies,  # 3 copies
            "logs": [],
        }

        result = generator.analyze_quality_node(state)

        assert "average_engagement" in result
        assert "average_viral_potential" in result
        assert "low_quality_clips" in result

        # Calculate expected averages: (8.5 + 7.8 + 8.2) / 3 = 8.17
        expected_engagement = round((8.5 + 7.8 + 8.2) / 3, 2)
        assert result["average_engagement"] == expected_engagement

    def test_analyze_quality_node_no_copies(self, monkeypatch, sample_clips_data):
        """Verify error when no copies were generated."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {"clips_data": sample_clips_data, "all_copies": [], "logs": []}

        result = generator.analyze_quality_node(state)

        assert "error_message" in result
        assert "No se generaron copies" in result["error_message"]

    def test_analyze_quality_node_insufficient_success_rate(
        self, monkeypatch, sample_clips_data, sample_clip_copies
    ):
        """Verify failure when success rate < 60%."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Only 2 copies for 5 clips = 40% < 60%
        state = {
            "clips_data": sample_clips_data,  # 5 clips
            "all_copies": sample_clip_copies[:2],  # 2 copies
            "logs": [],
        }

        result = generator.analyze_quality_node(state)

        assert "error_message" in result
        assert "Generación insuficiente" in result["error_message"]

    def test_analyze_quality_node_identifies_low_quality(
        self, monkeypatch, sample_clips_data
    ):
        """Verify clips with engagement < 6.5 are flagged as low quality."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Create copies with low engagement
        copies = [
            ClipCopy(
                clip_id=1,
                copy="High engagement copy with #AICDMX",
                metadata=CopyMetadata(
                    sentiment="educational",
                    sentiment_score=0.75,
                    engagement_score=8.0,  # High
                    suggested_thumbnail_timestamp=5.0,
                    primary_topics=["test", "topics", "here"],
                    hook_strength="high",
                    viral_potential=7.5,
                ),
            ),
            ClipCopy(
                clip_id=2,
                copy="Low engagement copy with #AICDMX hashtag",
                metadata=CopyMetadata(
                    sentiment="educational",
                    sentiment_score=0.50,
                    engagement_score=5.0,  # Low < 6.5
                    suggested_thumbnail_timestamp=5.0,
                    primary_topics=["test", "topics", "here"],
                    hook_strength="low",
                    viral_potential=5.0,
                ),
            ),
        ]

        state = {"clips_data": sample_clips_data[:2], "all_copies": copies, "logs": []}

        result = generator.analyze_quality_node(state)

        assert 2 in result["low_quality_clips"]
        assert 1 not in result["low_quality_clips"]


# ============================================================================
# TEST: SHOULD_RETRY_OR_SAVE CONDITIONAL EDGE
# ============================================================================


class TestShouldRetryOrSave:
    """Tests for should_retry_or_save conditional edge routing."""

    def test_should_retry_or_save_save_high_engagement(self, monkeypatch):
        """Verify 'save' is returned when engagement >= 7.5."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {
            "average_engagement": 8.0,
            "attempts": 1,
            "max_attempts": 3,
            "error_message": "",
        }

        result = generator.should_retry_or_save(state)

        assert result == "save"

    def test_should_retry_or_save_retry_low_engagement(self, monkeypatch):
        """Verify 'retry' is returned when engagement < 7.5 and attempts < max."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {
            "average_engagement": 6.5,  # Below threshold
            "attempts": 1,
            "max_attempts": 3,
            "error_message": "",
        }

        result = generator.should_retry_or_save(state)

        assert result == "retry"

    def test_should_retry_or_save_save_max_attempts(self, monkeypatch):
        """Verify 'save' is returned when max_attempts reached even with low engagement."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {
            "average_engagement": 6.5,  # Below threshold
            "attempts": 3,
            "max_attempts": 3,  # Max reached
            "error_message": "",
        }

        result = generator.should_retry_or_save(state)

        assert result == "save"

    def test_should_retry_or_save_end_on_error(self, monkeypatch):
        """Verify 'end' is returned when error_message is present."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        state = {
            "average_engagement": 8.0,
            "attempts": 1,
            "max_attempts": 3,
            "error_message": "Some error occurred",
        }

        result = generator.should_retry_or_save(state)

        assert result == "end"


# ============================================================================
# TEST: SAVE_RESULTS_NODE
# ============================================================================


class TestSaveResultsNode:
    """Tests for save_results_node."""

    def test_save_results_node(
        self, monkeypatch, tmp_path, sample_clips_data, sample_clip_copies
    ):
        """Verify JSON file is written with correct structure."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Override output paths to use temp directory
        generator.output_dir = tmp_path / "output" / "test_video"
        generator.copys_dir = generator.output_dir / "copys"
        generator.copys_file = generator.copys_dir / "clips_copys.json"

        classifications = [
            {"clip_id": 1, "style": "viral", "confidence": 0.9, "reason": "Test"},
            {
                "clip_id": 2,
                "style": "educational",
                "confidence": 0.85,
                "reason": "Test",
            },
            {
                "clip_id": 3,
                "style": "storytelling",
                "confidence": 0.92,
                "reason": "Test",
            },
        ]

        state = {
            "clips_data": sample_clips_data[:3],
            "all_copies": sample_clip_copies,
            "classifications": classifications,
            "grouped_clips": {
                "viral": [{"clip_id": 1}],
                "educational": [{"clip_id": 2}],
                "storytelling": [{"clip_id": 3}],
            },
            "average_engagement": 8.17,
            "average_viral_potential": 8.1,
            "logs": [],
        }

        result = generator.save_results_node(state)

        # Verify file was created
        assert generator.copys_file.exists()

        # Verify content
        with open(generator.copys_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["video_id"] == "test_video"
        assert saved_data["total_clips"] == 3
        assert len(saved_data["clips"]) == 3
        assert "classification_metadata" in saved_data
        assert "Guardado" in result["logs"][0]

    def test_save_results_node_incomplete_generation(
        self, monkeypatch, tmp_path, sample_clips_data, sample_clip_copies
    ):
        """Verify incomplete generation metadata is saved."""
        mock_llm = MagicMock()
        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id="test_video")

        # Override output paths
        generator.output_dir = tmp_path / "output" / "test_video"
        generator.copys_dir = generator.output_dir / "copys"
        generator.copys_file = generator.copys_dir / "clips_copys.json"

        # 5 clips but only 3 copies (incomplete)
        state = {
            "clips_data": sample_clips_data,  # 5 clips
            "all_copies": sample_clip_copies,  # 3 copies
            "classifications": [
                {"clip_id": i, "style": "viral", "confidence": 0.9, "reason": "Test"}
                for i in range(1, 6)
            ],
            "grouped_clips": {
                "viral": [{"clip_id": 1}, {"clip_id": 5}],
                "educational": [{"clip_id": 2}, {"clip_id": 4}],
                "storytelling": [{"clip_id": 3}],
            },
            "average_engagement": 8.17,
            "average_viral_potential": 8.1,
            "logs": [],
        }

        generator.save_results_node(state)

        with open(generator.copys_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["generation_metadata"]["incomplete"] is True
        assert saved_data["generation_metadata"]["total_clips"] == 5
        assert saved_data["generation_metadata"]["generated_clips"] == 3
        assert 4 in saved_data["generation_metadata"]["missing_clips"]
        assert 5 in saved_data["generation_metadata"]["missing_clips"]


# ============================================================================
# TEST: FULL WORKFLOW INTEGRATION
# ============================================================================


class TestFullWorkflowIntegration:
    """Integration test running the entire graph with mocked LLM."""

    def test_full_workflow_integration(
        self,
        monkeypatch,
        tmp_path,
        clips_metadata_file,
        mock_classification_response,
        mock_copy_response_viral,
        mock_copy_response_educational,
        mock_copy_response_storytelling,
    ):
        """Run the entire LangGraph workflow end-to-end with mocked responses."""
        # Track which call we're on to return appropriate response
        call_count = [0]

        def get_mock_response(*args, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()

            if call_count[0] == 1:
                # First call: classification
                mock_response.content = mock_classification_response
            elif call_count[0] == 2:
                # Second call: viral copies
                mock_response.content = mock_copy_response_viral
            elif call_count[0] == 3:
                # Third call: educational copies
                mock_response.content = mock_copy_response_educational
            else:
                # Fourth call: storytelling copies
                mock_response.content = mock_copy_response_storytelling

            return mock_response

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = get_mock_response

        mock_class = MagicMock(return_value=mock_llm)
        monkeypatch.setattr("src.copys_generator.ChatGoogleGenerativeAI", mock_class)

        from src.copys_generator import CopysGenerator

        generator = CopysGenerator(video_id=clips_metadata_file["video_id"])
        generator.temp_dir = clips_metadata_file["temp_dir"]

        # Override output paths
        generator.output_dir = tmp_path / "output" / clips_metadata_file["video_id"]
        generator.copys_dir = generator.output_dir / "copys"
        generator.copys_file = generator.copys_dir / "clips_copys.json"

        # Run the full workflow
        result = generator.generate()

        # Verify success
        assert result["success"] is True
        assert result["error"] is None or result["error"] == ""

        # Verify metrics
        assert result["metrics"]["total_copies"] == 5
        assert result["metrics"]["distribution"]["viral"] == 2
        assert result["metrics"]["distribution"]["educational"] == 2
        assert result["metrics"]["distribution"]["storytelling"] == 1

        # Verify output file exists
        assert generator.copys_file.exists()

        # Verify file content
        with open(generator.copys_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert len(saved_data["clips"]) == 5
        assert saved_data["style"] == "auto-classified"


# ============================================================================
# TEST: PYDANTIC VALIDATORS
# ============================================================================


class TestPydanticValidators:
    """Tests for Pydantic model validators in copy_schemas."""

    def test_copy_requires_aicdmx_hashtag(self):
        """Verify #AICDMX hashtag is required."""
        with pytest.raises(ValueError, match="must include #AICDMX"):
            ClipCopy(
                clip_id=1,
                copy="Test copy without required hashtag #Tech",
                metadata=CopyMetadata(
                    sentiment="educational",
                    sentiment_score=0.75,
                    engagement_score=7.5,
                    suggested_thumbnail_timestamp=5.0,
                    primary_topics=["test", "topics", "here"],
                    hook_strength="medium",
                    viral_potential=7.0,
                ),
            )

    def test_copy_requires_at_least_one_hashtag(self):
        """Verify at least one hashtag is required."""
        with pytest.raises(ValueError, match="must contain at least one hashtag"):
            ClipCopy(
                clip_id=1,
                copy="Test copy without any hashtags at all",
                metadata=CopyMetadata(
                    sentiment="educational",
                    sentiment_score=0.75,
                    engagement_score=7.5,
                    suggested_thumbnail_timestamp=5.0,
                    primary_topics=["test", "topics", "here"],
                    hook_strength="medium",
                    viral_potential=7.0,
                ),
            )

    def test_copy_truncation_preserves_aicdmx(self):
        """Verify long copies are truncated but #AICDMX is preserved."""
        long_copy = "A" * 140 + " #AICDMX #ExtraHashtag"  # Over 150 chars

        clip = ClipCopy(
            clip_id=1,
            copy=long_copy,
            metadata=CopyMetadata(
                sentiment="educational",
                sentiment_score=0.75,
                engagement_score=7.5,
                suggested_thumbnail_timestamp=5.0,
                primary_topics=["test", "topics", "here"],
                hook_strength="medium",
                viral_potential=7.0,
            ),
        )

        assert len(clip.copy_text) <= 150
        assert "#AICDMX" in clip.copy_text.upper()

    def test_sentiment_normalization(self):
        """Verify hybrid sentiments are normalized."""
        metadata = CopyMetadata(
            sentiment="educational_storytelling",  # Invalid hybrid
            sentiment_score=0.75,
            engagement_score=7.5,
            suggested_thumbnail_timestamp=5.0,
            primary_topics=["test", "topics", "here"],
            hook_strength="medium",
            viral_potential=7.0,
        )

        # Should be normalized to a valid sentiment
        assert metadata.sentiment in [
            "educational",
            "humorous",
            "inspirational",
            "controversial",
            "curious_educational",
            "relatable",
            "storytelling",
        ]

    def test_topics_deduplication(self):
        """Verify duplicate topics are removed."""
        metadata = CopyMetadata(
            sentiment="educational",
            sentiment_score=0.75,
            engagement_score=7.5,
            suggested_thumbnail_timestamp=5.0,
            primary_topics=["AI", "ai", "Tech", "tech", "AI"],  # Duplicates
            hook_strength="medium",
            viral_potential=7.0,
        )

        # Should have duplicates removed (case-insensitive)
        assert len(metadata.primary_topics) == 2

    def test_topics_truncation(self):
        """Verify topics are truncated to max 5."""
        metadata = CopyMetadata(
            sentiment="educational",
            sentiment_score=0.75,
            engagement_score=7.5,
            suggested_thumbnail_timestamp=5.0,
            primary_topics=["t1", "t2", "t3", "t4", "t5", "t6", "t7"],  # 7 topics
            hook_strength="medium",
            viral_potential=7.0,
        )

        assert len(metadata.primary_topics) == 5
