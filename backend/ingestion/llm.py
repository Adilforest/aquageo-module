"""Provider-agnostic LLM adapter via litellm (issue #21, M4 foundation).

Provider/model/key come from env: ``LLM_PROVIDER`` / ``LLM_MODEL`` and the
provider key (``GEMINI_API_KEY`` by default, ``ANTHROPIC_API_KEY`` optional —
litellm reads these from the environment itself). Switching provider = editing
env only, no code change.

``extract_structured(text, json_schema)`` returns a dict validated against the
schema, using the model's JSON mode, with retries and error handling.

NOTE: in tests ``litellm.completion`` is mocked — there is no real network call.
"""
from __future__ import annotations

import json

import jsonschema
import litellm
from django.conf import settings

DEFAULT_SYSTEM = (
    "Ты извлекаешь структурированные данные из текста паспорта/документа "
    "гидротехнического сооружения. Верни ТОЛЬКО валидный JSON строго по "
    "переданной JSON-схеме, без пояснений."
)


class LLMError(Exception):
    """Raised when structured extraction fails after all retries."""


def active_model() -> str:
    return getattr(settings, "LLM_MODEL", "gemini/gemini-2.5-flash")


def extract_structured(
    text: str,
    json_schema: dict,
    *,
    model: str | None = None,
    system: str | None = None,
    max_retries: int = 2,
    temperature: float = 0.0,
) -> dict:
    """Extract a schema-conforming dict from free text via the LLM.

    Retries on transport errors, invalid JSON, or schema violations. Raises
    ``LLMError`` if no valid result is obtained within ``max_retries`` + 1 tries.
    """
    model = model or active_model()
    messages = [
        {"role": "system", "content": system or DEFAULT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"JSON-схема:\n{json.dumps(json_schema, ensure_ascii=False)}\n\n"
                f"Текст:\n{text}\n\nВерни JSON по схеме."
            ),
        },
    ]

    last_error: Exception | None = None
    for _attempt in range(max_retries + 1):
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            jsonschema.validate(instance=data, schema=json_schema)
            return data
        except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
            last_error = exc  # bad output — retry
        except Exception as exc:  # transport/provider error — retry
            last_error = exc

    raise LLMError(
        f"structured extraction failed after {max_retries + 1} attempts: {last_error}"
    )
