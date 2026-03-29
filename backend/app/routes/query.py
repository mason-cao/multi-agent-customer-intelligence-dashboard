import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.schemas.query import QueryRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("")
@handle_errors("submit_query")
def submit_query(body: QueryRequest, db: Session = Depends(get_db)):
    """Submit a natural language question to the QueryAgent."""
    logger.info("submit_query", question=body.question)
    from app.agents.query_agent import QueryAgent

    engine = db.get_bind()
    agent = QueryAgent()
    result = agent.answer_question(body.question, engine)
    return result
