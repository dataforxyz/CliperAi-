"""
Video Namer - Genera nombres descriptivos para videos a partir de transcripciones

Este modulo proporciona funciones para generar nombres de video:
- first_words: Extrae las primeras N palabras del transcript
- llm_summary: Usa Gemini para generar un titulo descriptivo corto
- filename: Usa el nombre original del archivo (fallback)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Palabras comunes a filtrar al inicio (en ingles y espanol)
FILLER_WORDS = {
    "um",
    "uh",
    "like",
    "so",
    "well",
    "okay",
    "ok",
    "right",
    "yeah",
    "yes",
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "i",
    "you",
    "we",
    "they",
    "it",
    "este",
    "pues",
    "bueno",
    "entonces",
    "mira",
    "oye",
    "eh",
    "osea",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "y",
    "o",
    "pero",
    "que",
    "de",
    "en",
    "es",
    "no",
    "si",
    "como",
    "para",
    "por",
    "con",
    "se",
    "al",
}


def _slugify(text: str, max_chars: int = 40) -> str:
    """
    Convierte texto a un slug seguro para nombres de archivo.

    Args:
        text: Texto a convertir
        max_chars: Maximo de caracteres

    Returns:
        Slug seguro para nombres de archivo
    """
    # Elimina caracteres no alfanumericos excepto espacios y guiones
    cleaned = re.sub(r"[^\w\s-]", "", text.lower().strip())
    # Reemplaza espacios multiples por guion bajo
    cleaned = re.sub(r"[\s_]+", "_", cleaned)
    # Elimina guiones bajos al inicio/final
    cleaned = cleaned.strip("_-")
    # Trunca respetando limites de palabra
    if len(cleaned) > max_chars:
        truncated = cleaned[:max_chars]
        # No cortar en medio de palabra
        last_underscore = truncated.rfind("_")
        if last_underscore > max_chars * 0.5:
            truncated = truncated[:last_underscore]
        cleaned = truncated.rstrip("_-")
    return cleaned or "unnamed_video"


def _extract_first_words(transcript_data: dict, word_count: int = 5) -> str:
    """
    Extrae las primeras N palabras significativas del transcript.

    Args:
        transcript_data: Dict con la transcripcion (formato WhisperX)
        word_count: Numero de palabras a extraer

    Returns:
        Texto con las primeras palabras
    """
    segments = transcript_data.get("segments", [])
    if not segments:
        return ""

    # Colecta palabras de los primeros segmentos
    collected_words = []
    for segment in segments:
        # Usa word_segments si estan disponibles (mas preciso)
        words = segment.get("words", [])
        if words:
            for word_obj in words:
                word = word_obj.get("word", "").strip().lower()
                # Elimina puntuacion al final
                word_clean = re.sub(r"[^\w]", "", word)
                if (
                    word_clean
                    and word_clean not in FILLER_WORDS
                    and len(word_clean) > 1
                ):
                    collected_words.append(word_clean)
                    if len(collected_words) >= word_count:
                        break
        else:
            # Fallback: usa el texto del segmento
            text = segment.get("text", "").strip()
            for word in text.split():
                word_clean = re.sub(r"[^\w]", "", word.lower())
                if (
                    word_clean
                    and word_clean not in FILLER_WORDS
                    and len(word_clean) > 1
                ):
                    collected_words.append(word_clean)
                    if len(collected_words) >= word_count:
                        break

        if len(collected_words) >= word_count:
            break

    return " ".join(collected_words)


def _generate_llm_summary(transcript_data: dict, max_chars: int = 40) -> str | None:
    """
    Usa Gemini para generar un titulo descriptivo corto.

    Args:
        transcript_data: Dict con la transcripcion
        max_chars: Maximo de caracteres para el titulo

    Returns:
        Titulo generado por LLM, o None si falla
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        logger.warning("langchain_google_genai no disponible para LLM naming")
        return None

    segments = transcript_data.get("segments", [])
    if not segments:
        return None

    # Construye contexto con los primeros ~500 caracteres
    full_text = " ".join(seg.get("text", "") for seg in segments[:10])[:500]
    if not full_text.strip():
        return None

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.3,  # Baja creatividad para titulos consistentes
        )

        prompt = f"""Generate a short, descriptive title (maximum {max_chars} characters) for a video based on this transcript excerpt.

The title must:
- Be descriptive of the main topic
- NOT use emojis or special characters
- Be in the same language as the content
- Be easy to read as a filename (no colons, slashes, etc.)

Transcript:
{full_text}

Respond ONLY with the title, no quotes or explanations."""

        response = llm.invoke(prompt)
        title = response.content.strip()

        # Limpia la respuesta
        title = re.sub(r'^["\']|["\']$', "", title)  # Quita comillas
        title = title[:max_chars]

        logger.info(f"LLM generated title: {title}")
        return title

    except Exception as e:
        logger.warning(f"Error generating title with LLM: {e}")
        return None


def generate_video_name(
    *,
    transcript_path: str | None = None,
    original_filename: str,
    method: Literal["filename", "first_words", "llm_summary"] = "filename",
    max_chars: int = 40,
    word_count: int = 5,
) -> str:
    """
    Genera un nombre descriptivo para el video.

    Args:
        transcript_path: Ruta al JSON de transcripcion (requerido para first_words/llm_summary)
        original_filename: Nombre original del archivo de video
        method: Metodo de generacion ("filename", "first_words", "llm_summary")
        max_chars: Maximo de caracteres en el nombre
        word_count: Numero de palabras (solo para first_words)

    Returns:
        Nombre generado (slug seguro para filesystem)
    """
    # Fallback por defecto
    fallback_name = _slugify(Path(original_filename).stem, max_chars)

    if method == "filename":
        return fallback_name

    # Para otros metodos necesitamos la transcripcion
    if not transcript_path or not Path(transcript_path).exists():
        logger.warning("Transcript not available, using filename as fallback")
        return fallback_name

    try:
        with open(transcript_path, encoding="utf-8") as f:
            transcript_data = json.load(f)
    except Exception as e:
        logger.warning(f"Error loading transcript: {e}")
        return fallback_name

    if method == "first_words":
        text = _extract_first_words(transcript_data, word_count)
        if text:
            return _slugify(text, max_chars)
        logger.warning("Could not extract words, using filename")
        return fallback_name

    elif method == "llm_summary":
        title = _generate_llm_summary(transcript_data, max_chars)
        if title:
            return _slugify(title, max_chars)
        # Fallback a first_words si LLM falla
        logger.info("LLM failed, trying first_words as fallback")
        text = _extract_first_words(transcript_data, word_count)
        if text:
            return _slugify(text, max_chars)
        return fallback_name

    return fallback_name
