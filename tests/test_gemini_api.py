#!/usr/bin/env python3
"""
Test script para verificar que la API de Gemini funciona correctamente.

Este script prueba:
1. Que la API key esté configurada
2. Que el modelo gemini-2.5-flash funcione
3. Que pueda generar respuestas JSON válidas
4. Que respete el formato solicitado

Uso:
    uv run python tests/test_gemini_api.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Añadir src al path para importar
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_google_genai import ChatGoogleGenerativeAI


def test_api_key():
    """Test 1: Verificar que la API key esté configurada"""
    print("=" * 60)
    print("TEST 1: API Key Configuration")
    print("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY")

    assert api_key, "GOOGLE_API_KEY no está configurada en .env"

    print(f"✓ API Key encontrada: {api_key[:20]}...")


def test_basic_connection():
    """Test 2: Verificar que podemos conectarnos al modelo"""
    print("\n" + "=" * 60)
    print("TEST 2: Basic Model Connection")
    print("=" * 60)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

    response = llm.invoke("Say 'Hello World' in one sentence.")
    print("✓ Modelo inicializado correctamente")
    print(f"✓ Respuesta: {response.content}")
    assert response.content is not None


def test_json_generation():
    """Test 3: Verificar que puede generar JSON válido"""
    print("\n" + "=" * 60)
    print("TEST 3: JSON Generation")
    print("=" * 60)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

    prompt = """Generate a JSON object with the following structure:
{
  "name": "John Doe",
  "age": 30,
  "city": "New York"
}

Respond ONLY with valid JSON (no markdown, no explanations):"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    # Limpiar respuesta si viene con markdown
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    response_text = response_text.strip()

    print(f"Raw response:\n{response_text}\n")

    # Intentar parsear JSON
    data = json.loads(response_text)

    print("✓ JSON válido generado")
    print(f"✓ Datos parseados: {data}")
    assert data is not None


def test_clip_classification():
    """Test 4: Simular clasificación de un clip (caso real)"""
    print("\n" + "=" * 60)
    print("TEST 4: Clip Classification (Real Use Case)")
    print("=" * 60)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

    # Simular un clip real
    clip_data = {
        "clip_id": 1,
        "transcript": "Hoy vamos a hablar sobre React hooks. Los hooks son una forma de usar state y otras características de React sin escribir una clase. El hook más común es useState.",
        "duration": 45,
    }

    prompt = f"""Clasifica este clip de video en uno de estos estilos: viral, educational, storytelling.

Clip:
{json.dumps(clip_data, indent=2, ensure_ascii=False)}

Responde SOLO con JSON en este formato (sin markdown):
{{
  "clip_id": 1,
  "style": "viral",
  "confidence": 0.85,
  "reason": "Brief explanation"
}}"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    # Limpiar respuesta
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    response_text = response_text.strip()

    print(f"Raw response:\n{response_text}\n")

    # Parsear JSON
    classification = json.loads(response_text)

    # Validar estructura
    required_fields = ["clip_id", "style", "confidence", "reason"]
    for field in required_fields:
        assert field in classification, f"Falta el campo '{field}' en la respuesta"

    # Validar que style sea válido
    valid_styles = ["viral", "educational", "storytelling"]
    assert classification["style"] in valid_styles, f"Style '{classification['style']}' no es válido"

    print("✓ Clasificación correcta generada")
    print(f"✓ Style: {classification['style']}")
    print(f"✓ Confidence: {classification['confidence']}")
    print(f"✓ Reason: {classification['reason']}")


def test_copy_generation():
    """Test 5: Generar un copy para un clip (caso real)"""
    print("\n" + "=" * 60)
    print("TEST 5: Copy Generation (Real Use Case)")
    print("=" * 60)

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.8)

    # Simular un clip real
    clip_data = {
        "clip_id": 1,
        "transcript": "Hoy vamos a hablar sobre React hooks. Los hooks son una forma de usar state y otras características de React sin escribir una clase.",
        "duration": 45,
    }

    prompt = f"""Genera un copy viral para este clip de video sobre tecnología.

Requisitos:
- Mezcla español e inglés (code-switching)
- Máximo 150 caracteres
- Incluye emojis relevantes
- DEBE incluir el hashtag #AICDMX
- Genera engagement

Clip:
{json.dumps(clip_data, indent=2, ensure_ascii=False)}

Responde SOLO con JSON (sin markdown):
{{
  "clip_id": 1,
  "copy": "El copy aquí con #AICDMX",
  "metadata": {{
    "sentiment": "curious_educational",
    "engagement_score": 8.5,
    "viral_potential": 7.8,
    "primary_topics": ["React", "hooks"]
  }}
}}"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    # Limpiar respuesta
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    response_text = response_text.strip()

    print(f"Raw response:\n{response_text}\n")

    # Parsear JSON
    copy_data = json.loads(response_text)

    # Validar estructura
    assert "copy" in copy_data, "Falta el campo 'copy'"

    # Validar que tenga #AICDMX
    assert "#AICDMX" in copy_data["copy"].upper(), f"El copy no incluye #AICDMX: {copy_data['copy']}"

    print("✓ Copy generado correctamente")
    print(f"✓ Copy: {copy_data['copy']}")
    print(f"✓ Metadata: {copy_data.get('metadata', {})}")


def main():
    """Ejecutar todos los tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "GEMINI API TEST SUITE" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    tests = [
        test_api_key,
        test_basic_connection,
        test_json_generation,
        test_clip_classification,
        test_copy_generation,
    ]

    results = []
    for test in tests:
        try:
            test()
            results.append(True)
        except Exception as e:
            print(f"\n Test failed: {e}")
            import traceback

            print(traceback.format_exc())
            results.append(False)

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "PASS" if result else "FAIL"
        print(f"{status} - Test {i}: {test.__name__}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print(
            "\nTodos los tests pasaron! La API de Gemini está funcionando correctamente."
        )
        return 0
    else:
        print(f"\n{total - passed} test(s) fallaron. Revisa la configuración.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
