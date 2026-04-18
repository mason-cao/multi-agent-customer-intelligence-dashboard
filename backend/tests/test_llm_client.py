"""Tests for the LLM client helper contract."""

from app.services.llm_client import _parse_json


def test_parse_json_accepts_objects():
    assert _parse_json('{"ok": true}') == {"ok": True}


def test_parse_json_accepts_arrays():
    assert _parse_json('[{"score": 0.8}]') == [{"score": 0.8}]


def test_parse_json_strips_markdown_fences():
    assert _parse_json('```json\n{"ok": true}\n```') == {"ok": True}


def test_parse_json_returns_none_for_invalid_json():
    assert _parse_json("not json") is None
