"""Tests for the natural-language query API contract."""

import pytest


@pytest.mark.asyncio
async def test_query_rejects_blank_question(client):
    resp = await client.post("/api/query", json={"question": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_trims_question_and_parses_structured_result(client):
    resp = await client.post(
        "/api/query",
        json={"question": "   What is the weather today?   "},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["original_question"] == "What is the weather today?"
    assert body["query_status"] == "unsupported"
    assert isinstance(body["structured_result"], dict)
    assert isinstance(body["structured_result"]["supported_intents"], list)
