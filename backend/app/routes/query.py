from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str


@router.post("")
def submit_query(body: QueryRequest, db: Session = Depends(get_db)):
    """Submit a natural language question to the QueryAgent."""
    from app.agents.query_agent import QueryAgent

    engine = db.get_bind()
    agent = QueryAgent()
    result = agent.answer_question(body.question, engine)
    return result
