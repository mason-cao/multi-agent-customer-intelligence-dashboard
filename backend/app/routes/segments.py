from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.churn_prediction import ChurnPrediction
from app.models.customer_feature import CustomerFeature
from app.models.customer_segment import CustomerSegment

router = APIRouter(prefix="/api/segments", tags=["segments"])


@router.get("/summary")
@handle_errors("get_segment_summary")
def get_segment_summary(db: Session = Depends(get_db)):
    """Return per-segment stats: count, avg revenue, engagement, churn risk."""
    rows = (
        db.query(
            CustomerSegment.segment_id,
            CustomerSegment.segment_name,
            func.count(CustomerSegment.customer_id).label("customer_count"),
            func.avg(CustomerFeature.total_revenue).label("avg_revenue"),
            func.avg(CustomerFeature.engagement_score).label("avg_engagement"),
            func.avg(ChurnPrediction.churn_probability).label("avg_churn_risk"),
        )
        .join(
            CustomerFeature,
            CustomerSegment.customer_id == CustomerFeature.customer_id,
        )
        .outerjoin(
            ChurnPrediction,
            CustomerSegment.customer_id == ChurnPrediction.customer_id,
        )
        .group_by(CustomerSegment.segment_id, CustomerSegment.segment_name)
        .order_by(CustomerSegment.segment_id)
        .all()
    )

    return [
        {
            "segment_id": r.segment_id,
            "segment_name": r.segment_name,
            "customer_count": r.customer_count,
            "avg_revenue": round(r.avg_revenue or 0, 2),
            "avg_engagement": round(r.avg_engagement or 0, 4),
            "avg_churn_risk": round(r.avg_churn_risk or 0, 4),
        }
        for r in rows
    ]
