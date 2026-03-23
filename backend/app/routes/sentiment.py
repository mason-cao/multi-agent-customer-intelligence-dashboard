import json

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.sentiment_result import SentimentResult

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


@router.get("/summary")
@handle_errors("get_sentiment_summary")
def get_sentiment_summary(db: Session = Depends(get_db)):
    """Sentiment distribution, average score, and top topics."""
    # Label distribution
    label_rows = (
        db.query(
            SentimentResult.sentiment_label,
            func.count(SentimentResult.document_id).label("count"),
        )
        .group_by(SentimentResult.sentiment_label)
        .all()
    )
    distribution = {r.sentiment_label: r.count for r in label_rows}

    # Avg score and total
    avg_score = db.query(func.avg(SentimentResult.sentiment_score)).scalar() or 0.0
    total = db.query(func.count(SentimentResult.document_id)).scalar() or 0

    # Top topics — unpack JSON arrays and count
    topic_rows = (
        db.query(SentimentResult.topics, SentimentResult.sentiment_score)
        .filter(SentimentResult.topics.isnot(None))
        .all()
    )

    topic_counts: dict[str, list[float]] = {}
    for row in topic_rows:
        try:
            topics = json.loads(row.topics) if isinstance(row.topics, str) else row.topics
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(topics, list):
            continue
        for topic in topics:
            if not isinstance(topic, str):
                continue
            if topic not in topic_counts:
                topic_counts[topic] = []
            topic_counts[topic].append(row.sentiment_score)

    topics = sorted(
        [
            {
                "topic": topic,
                "count": len(scores),
                "avg_sentiment": round(sum(scores) / len(scores), 4),
            }
            for topic, scores in topic_counts.items()
        ],
        key=lambda x: -x["count"],
    )[:15]

    return {
        "distribution": distribution,
        "avg_score": round(float(avg_score), 4),
        "total": total,
        "topics": topics,
    }
