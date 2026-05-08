"""
FinSight LLM Client — Groq (OpenAI-compatible)
================================================
Provides a unified interface for all skills.
Uses Groq's OpenAI-compatible API for fast inference.

Environment:
    GROQ_API_KEY  — Required. Get one at https://console.groq.com/keys
"""

import os
import time
import yaml
import json

from openai import OpenAI

_client = None
_last_call_ts = 0.0
_MIN_INTERVAL_SEC = 2.5  # ≤ 24 RPM, well under Groq's 30 RPM ceiling


def _throttle():
    global _last_call_ts
    now = time.time()
    wait = _MIN_INTERVAL_SEC - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.time()


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY environment variable is not set. "
                "Get a free key at https://console.groq.com/keys"
            )
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


_MODEL_MAP = {
    "gemini-2.0-flash": "llama-3.3-70b-versatile",
    "gemini-1.5-flash": "llama-3.1-8b-instant",
    "gemini-1.5-pro": "llama-3.3-70b-versatile",
}


def _resolve_model(model_name: str) -> str:
    return _MODEL_MAP.get(model_name, model_name)


def generate(prompt: str, model_name: str = "llama-3.3-70b-versatile",
             max_retries: int = 2, retry_delay: float = 3.0) -> str:
    client = _get_client()
    model = _resolve_model(model_name)

    for attempt in range(max_retries + 1):
        try:
            _throttle()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            msg = str(e).lower()
            backoff = retry_delay * (2 ** attempt)
            if "rate" in msg or "429" in msg:
                backoff = max(backoff, 20.0)
            if attempt < max_retries:
                print(f"[LLM] Attempt {attempt + 1} failed: {e}. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
            else:
                raise RuntimeError(f"[LLM] All {max_retries + 1} attempts failed: {e}")


def generate_yaml(prompt: str, model_name: str = "llama-3.3-70b-versatile",
                  max_retries: int = 2) -> dict:
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


def generate_json(prompt: str, model_name: str = "llama-3.3-70b-versatile",
                  max_retries: int = 2) -> dict:
    client = _get_client()
    model = _resolve_model(model_name)

    for attempt in range(max_retries + 1):
        try:
            _throttle()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            msg = str(e).lower()
            backoff = 3.0 * (2 ** attempt)
            if "rate" in msg or "429" in msg:
                backoff = max(backoff, 20.0)
            if attempt < max_retries:
                print(f"[LLM] JSON generation failed (attempt {attempt + 1}): {e}. Sleeping {backoff:.1f}s.")
                time.sleep(backoff)
            else:
                print(f"[LLM] JSON generation failed after all retries: {e}")
                return {"error": str(e)}


def _strip_yaml_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```yaml"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
