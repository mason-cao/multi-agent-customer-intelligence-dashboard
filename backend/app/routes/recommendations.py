from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.recommendation import Recommendation

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/summary")
@handle_errors("get_recommendation_summary")
def get_recommendation_summary(db: Session = Depends(get_db)):
    """Aggregate recommendation stats: distributions by action, category, priority, etc."""
    total = db.query(func.count(Recommendation.recommendation_id)).scalar() or 0

    action_dist = dict(
        db.query(Recommendation.action_label, func.count(Recommendation.recommendation_id))
        .group_by(Recommendation.action_label)
        .all()
    )
    category_dist = dict(
        db.query(Recommendation.action_category, func.count(Recommendation.recommendation_id))
        .group_by(Recommendation.action_category)
        .all()
    )
    priority_dist = dict(
        db.query(Recommendation.action_priority, func.count(Recommendation.recommendation_id))
        .group_by(Recommendation.action_priority)
        .all()
    )
    confidence_dist = dict(
        db.query(Recommendation.confidence, func.count(Recommendation.recommendation_id))
        .group_by(Recommendation.confidence)
        .all()
    )
    timeframe_dist = dict(
        db.query(Recommendation.target_timeframe, func.count(Recommendation.recommendation_id))
        .group_by(Recommendation.target_timeframe)
        .all()
    )

    avg_urgency = db.query(func.avg(Recommendation.urgency_score)).scalar() or 0.0

    return {
        "total_recommendations": total,
        "action_distribution": action_dist,
        "category_distribution": category_dist,
        "priority_distribution": {str(k): v for k, v in priority_dist.items()},
        "confidence_distribution": confidence_dist,
        "avg_urgency": round(float(avg_urgency), 4),
        "timeframe_distribution": timeframe_dist,
    }


@router.get("/top")
@handle_errors("get_top_recommendations")
def get_top_recommendations(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """Top recommendations sorted by priority (ascending) then urgency (descending)."""
    rows = (
        db.query(Recommendation)
        .order_by(Recommendation.action_priority, Recommendation.urgency_score.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "recommendation_id": r.recommendation_id,
            "customer_id": r.customer_id,
            "action_code": r.action_code,
            "action_label": r.action_label,
            "action_category": r.action_category,
            "action_priority": r.action_priority,
            "urgency_score": round(r.urgency_score, 4),
            "confidence": r.confidence,
            "primary_driver": r.primary_driver,
            "secondary_driver": r.secondary_driver,
            "reasoning": r.reasoning,
            "recommended_channel": r.recommended_channel,
            "recommended_owner": r.recommended_owner,
            "target_timeframe": r.target_timeframe,
            "recommendation_version": r.recommendation_version,
            "computed_at": r.computed_at,
        }
        for r in rows
    ]
