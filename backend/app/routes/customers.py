from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer
from app.models.customer_feature import CustomerFeature
from app.models.customer_segment import CustomerSegment
from app.models.sentiment_result import SentimentResult

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def get_customers(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Paginated customer list with cross-agent enrichment."""
    total = db.query(func.count(Customer.customer_id)).scalar() or 0

    # Subquery for per-customer avg sentiment from sentiment_results
    sent_sub = (
        db.query(
            SentimentResult.customer_id,
            func.avg(SentimentResult.sentiment_score).label("avg_sentiment"),
        )
        .group_by(SentimentResult.customer_id)
        .subquery()
    )

    rows = (
        db.query(
            Customer.customer_id,
            Customer.name,
            Customer.email,
            Customer.company,
            Customer.industry,
            Customer.plan_tier,
            Customer.signup_date,
            Customer.region,
            Customer.is_churned,
            CustomerFeature.engagement_score,
            CustomerFeature.total_revenue,
            CustomerSegment.segment_name,
            ChurnPrediction.churn_probability,
            ChurnPrediction.risk_tier,
            sent_sub.c.avg_sentiment,
        )
        .outerjoin(
            CustomerFeature,
            Customer.customer_id == CustomerFeature.customer_id,
        )
        .outerjoin(
            CustomerSegment,
            Customer.customer_id == CustomerSegment.customer_id,
        )
        .outerjoin(
            ChurnPrediction,
            Customer.customer_id == ChurnPrediction.customer_id,
        )
        .outerjoin(
            sent_sub,
            Customer.customer_id == sent_sub.c.customer_id,
        )
        .order_by(Customer.name)
        .offset(offset)
        .limit(limit)
        .all()
    )

    customers = [
        {
            "customer_id": r.customer_id,
            "name": r.name,
            "email": r.email,
            "company": r.company,
            "industry": r.industry,
            "plan_tier": r.plan_tier,
            "signup_date": r.signup_date,
            "region": r.region,
            "is_churned": bool(r.is_churned),
            "engagement_score": round(r.engagement_score, 4) if r.engagement_score is not None else None,
            "total_revenue": round(r.total_revenue, 2) if r.total_revenue is not None else None,
            "segment_name": r.segment_name,
            "churn_probability": round(r.churn_probability, 4) if r.churn_probability is not None else None,
            "risk_tier": r.risk_tier,
            "avg_sentiment": round(float(r.avg_sentiment), 4) if r.avg_sentiment is not None else None,
        }
        for r in rows
    ]

    return {"customers": customers, "total": total}
