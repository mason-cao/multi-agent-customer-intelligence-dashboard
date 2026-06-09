"""Tests for the natural-language query API contract."""

import pytest

from tests.helpers import create_workspace_with_token, workspace_session


def _create_empty_workspace_db(workspace_id: str):
    db = workspace_session(workspace_id)
    db.close()


@pytest.mark.asyncio
async def test_query_rejects_blank_question(client):
    workspace, headers = await create_workspace_with_token(client, "Blank Query Test")
    _create_empty_workspace_db(workspace["id"])
    resp = await client.post(
        "/api/query",
        headers=headers,
        json={"question": "   "},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_trims_question_and_parses_structured_result(client):
    workspace, headers = await create_workspace_with_token(client, "Query Test")
    _create_empty_workspace_db(workspace["id"])
    resp = await client.post(
        "/api/query",
        headers=headers,
        json={"question": "   What is the weather today?   "},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["original_question"] == "What is the weather today?"
    assert body["query_status"] == "unsupported"
    assert isinstance(body["structured_result"], dict)
    assert isinstance(body["structured_result"]["supported_intents"], list)
    # Response envelope carries rendering hints and guided follow-ups.
    assert "result_kind" in body
    assert isinstance(body["suggested_followups"], list)


@pytest.mark.asyncio
async def test_query_suggestions_endpoint(client):
    resp = await client.get("/api/query/suggestions")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    first = body[0]
    assert "intent" in first
    assert "label" in first
    assert "example" in first
