import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.churn_prediction import ChurnPrediction
from app.schemas.churn import AtRiskCustomer, ChurnDistribution, FeatureImportance
from app.models.customer import Customer
from app.models.subscription import Subscription

router = APIRouter(prefix="/api/churn", tags=["churn"])


def _parse_risk_factors(raw_value) -> list[dict]:
    """Parse risk-factor JSON defensively for dashboard routes."""
    try:
        factors = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(factors, list):
        return []
    return [factor for factor in factors if isinstance(factor, dict)]


@router.get("/distribution", response_model=list[ChurnDistribution])
@handle_errors("get_churn_distribution")
def get_churn_distribution(db: Session = Depends(get_db)):
    """Risk tier counts and MRR at risk per tier."""
    # Subquery: per-customer total MRR
    sub_mrr = (
        db.query(
            Subscription.customer_id,
            func.sum(Subscription.mrr).label("total_mrr"),
        )
        .group_by(Subscription.customer_id)
        .subquery()
    )

    rows = (
        db.query(
            ChurnPrediction.risk_tier,
            func.count(ChurnPrediction.customer_id).label("count"),
            func.coalesce(func.sum(sub_mrr.c.total_mrr), 0).label("mrr_at_risk"),
        )
        .outerjoin(
            sub_mrr, ChurnPrediction.customer_id == sub_mrr.c.customer_id
        )
        .group_by(ChurnPrediction.risk_tier)
        .all()
    )

    tier_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    result = sorted(
        [
            {
                "risk_tier": r.risk_tier,
                "count": r.count,
                "mrr_at_risk": round(float(r.mrr_at_risk), 2),
            }
            for r in rows
        ],
        key=lambda x: tier_order.get(x["risk_tier"], 99),
    )
    return result


@router.get("/at-risk", response_model=list[AtRiskCustomer])
@handle_errors("get_at_risk_customers")
def get_at_risk_customers(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """Top at-risk customers sorted by churn probability descending."""
    sub_mrr = (
        db.query(
            Subscription.customer_id,
            func.sum(Subscription.mrr).label("total_mrr"),
        )
        .group_by(Subscription.customer_id)
        .subquery()
    )

    rows = (
        db.query(
            ChurnPrediction.customer_id,
            Customer.name,
            Customer.company,
            ChurnPrediction.churn_probability,
            ChurnPrediction.risk_tier,
            ChurnPrediction.top_risk_factors,
            sub_mrr.c.total_mrr,
        )
        .join(Customer, ChurnPrediction.customer_id == Customer.customer_id)
        .outerjoin(
            sub_mrr, ChurnPrediction.customer_id == sub_mrr.c.customer_id
        )
        .order_by(desc(ChurnPrediction.churn_probability))
        .limit(limit)
        .all()
    )

    result = []
    for r in rows:
        factors = _parse_risk_factors(r.top_risk_factors)
        top_factor = factors[0].get("descriptor") if factors else None
        result.append(
            {
                "customer_id": r.customer_id,
                "name": r.name,
                "company": r.company,
                "churn_probability": round(r.churn_probability, 4),
                "risk_tier": r.risk_tier,
                "top_risk_factor": top_factor or "N/A",
                "mrr": round(float(r.total_mrr or 0), 2),
            }
        )
    return result


@router.get("/feature-importance", response_model=list[FeatureImportance])
@handle_errors("get_feature_importance")
def get_feature_importance(db: Session = Depends(get_db)):
    """Observed feature importance from top_risk_factors across all predictions."""
    rows = (
        db.query(ChurnPrediction.top_risk_factors)
        .filter(ChurnPrediction.top_risk_factors.isnot(None))
        .all()
    )

    # Aggregate: count how often each feature appears as a top risk factor
    # and average the absolute SHAP importance across all customers
    feature_stats: dict[str, list[float]] = {}
    for (factors_json,) in rows:
        factors = _parse_risk_factors(factors_json)
        for f in factors:
            name = f.get("feature", "")
            try:
                imp = abs(float(f.get("importance", 0)))
            except (TypeError, ValueError):
                continue
            if name not in feature_stats:
                feature_stats[name] = []
            feature_stats[name].append(imp)

    result = sorted(
        [
            {
                "feature": name,
                "importance": round(sum(vals) / len(vals), 4),
            }
            for name, vals in feature_stats.items()
            if vals
        ],
        key=lambda x: -x["importance"],
    )
    return result
