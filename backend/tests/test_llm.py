"""LLM adapter tests — litellm is mocked, NO real API calls (issue #21)."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ingestion.llm import LLMError, extract_structured

SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "length_km": {"type": "number"}},
    "required": ["name", "length_km"],
    "additionalProperties": True,
}


def fake_response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_returns_parsed_dict_validated_against_schema():
    payload = {"name": "Магистральный канал", "length_km": 12.5}
    resp = fake_response(json.dumps(payload))
    with patch("ingestion.llm.litellm.completion", return_value=resp) as m:
        result = extract_structured("текст паспорта", SCHEMA)
    assert result == payload
    assert m.call_count == 1  # exactly one (mocked) call, no network


def test_retries_on_transport_error_then_succeeds():
    payload = {"name": "Канал", "length_km": 3}
    side = [RuntimeError("502 upstream"), fake_response(json.dumps(payload))]
    with patch("ingestion.llm.litellm.completion", side_effect=side) as m:
        result = extract_structured("текст", SCHEMA, max_retries=2)
    assert result == payload
    assert m.call_count == 2  # failed once, retried, succeeded


def test_schema_violation_retried_then_raises_llmerror():
    # missing required "length_km" every time -> exhausts retries
    bad = fake_response(json.dumps({"name": "X"}))
    with patch("ingestion.llm.litellm.completion", return_value=bad) as m:
        with pytest.raises(LLMError):
            extract_structured("текст", SCHEMA, max_retries=2)
    assert m.call_count == 3  # initial + 2 retries, all invalid


def test_invalid_json_retried_then_raises():
    with patch("ingestion.llm.litellm.completion", return_value=fake_response("не json")) as m:
        with pytest.raises(LLMError):
            extract_structured("текст", SCHEMA, max_retries=1)
    assert m.call_count == 2


def test_uses_configured_model_and_json_mode():
    payload = {"name": "К", "length_km": 1}
    resp = fake_response(json.dumps(payload))
    with patch("ingestion.llm.litellm.completion", return_value=resp) as m:
        extract_structured("t", SCHEMA, model="anthropic/claude-haiku-4-5")
    _, kwargs = m.call_args
    assert kwargs["model"] == "anthropic/claude-haiku-4-5"
    assert kwargs["response_format"] == {"type": "json_object"}
