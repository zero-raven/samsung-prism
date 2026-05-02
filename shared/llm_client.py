"""
FinSight LLM Client — Google Genai SDK Wrapper
================================================
Provides a unified interface for all skills to call Google Gemini.
Uses the new `google-genai` SDK (replaces deprecated google-generativeai).
Handles retries, YAML parsing, and error recovery.

Environment:
    GEMINI_API_KEY  — Required. Your Google AI Studio API key.
"""

import os
import time
import yaml
import json

from google import genai
from google.genai import types

_client = None


def _get_client():
    """Get or create the Genai client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate(prompt: str, model_name: str = "gemini-2.0-flash",
             max_retries: int = 2, retry_delay: float = 3.0) -> str:
    """
    Generate text from Gemini.

    INPUT:
        prompt      — The full prompt string
        model_name  — Gemini model identifier
        max_retries — Number of retries on failure
        retry_delay — Seconds between retries

    OUTPUT:
        str — The generated text response
    """
    client = _get_client()

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if attempt < max_retries:
                print(f"[LLM] Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise RuntimeError(f"[LLM] All {max_retries + 1} attempts failed: {e}")


def generate_yaml(prompt: str, model_name: str = "gemini-2.0-flash",
                  max_retries: int = 2) -> dict:
    """
    Generate structured YAML output from Gemini and parse it.

    INPUT:
        prompt      — Prompt that instructs the model to return YAML
        model_name  — Gemini model identifier

    OUTPUT:
        dict — Parsed YAML as a Python dictionary

    If the model wraps YAML in ```yaml ... ``` fences, they are stripped.
    On parse failure, retries with an explicit correction prompt.
    """
    for attempt in range(max_retries + 1):
        raw = generate(prompt, model_name)
        cleaned = _strip_yaml_fences(raw)

        try:
            parsed = yaml.safe_load(cleaned)
            if isinstance(parsed, dict):
                return parsed
            else:
                raise ValueError(f"Expected dict, got {type(parsed)}")
        except Exception as e:
            if attempt < max_retries:
                print(f"[LLM] YAML parse failed (attempt {attempt + 1}): {e}")
                # Retry with a correction prompt
                prompt = (
                    f"Your previous response was not valid YAML. "
                    f"Error: {e}\n\n"
                    f"Please respond with ONLY valid YAML, no markdown fences, "
                    f"no extra text.\n\n"
                    f"Original request:\n{prompt}"
                )
            else:
                print(f"[LLM] YAML parse failed after all retries. Raw output:\n{raw}")
                return {"error": str(e), "raw_output": raw}


def generate_json(prompt: str, model_name: str = "gemini-2.0-flash",
                  max_retries: int = 2) -> dict:
    """
    Generate structured JSON output from Gemini and parse it.

    INPUT:
        prompt      — Prompt that instructs the model to return JSON
        model_name  — Gemini model identifier

    OUTPUT:
        dict — Parsed JSON as a Python dictionary
    """
    client = _get_client()

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            if attempt < max_retries:
                print(f"[LLM] JSON generation failed (attempt {attempt + 1}): {e}")
                time.sleep(3)
            else:
                print(f"[LLM] JSON generation failed after all retries: {e}")
                return {"error": str(e)}


def _strip_yaml_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```yaml"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
