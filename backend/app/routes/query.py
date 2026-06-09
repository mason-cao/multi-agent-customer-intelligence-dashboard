from typing import List

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.utils.privacy import text_log_metadata
from app.schemas.query import QueryRequest, QueryResultItem, QuerySuggestion

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=QueryResultItem)
@handle_errors("submit_query")
def submit_query(body: QueryRequest, db: Session = Depends(get_db)):
    """Submit a natural language question to the QueryAgent."""
    logger.info("submit_query", **text_log_metadata(body.question))
    from app.agents.query_agent import QueryAgent
    from app.services.llm_client import LLMClient

    engine = db.get_bind()
    agent = QueryAgent()
    # Mock-first: with no API key LLMClient() runs in mock mode and route_query()
    # is a no-op, so the deterministic engine fully answers. A real key adds
    # whitelisted intent routing as a fallback only.
    result = agent.answer_question(body.question, engine, llm_client=LLMClient())
    return result


@router.get("/suggestions", response_model=List[QuerySuggestion])
@handle_errors("query_suggestions")
def query_suggestions():
    """Guided prompt suggestions, derived from the intent registry. No workspace
    data is needed, so this works before any query has been run."""
    from app.agents.query_agent import build_suggestions

    return build_suggestions()
