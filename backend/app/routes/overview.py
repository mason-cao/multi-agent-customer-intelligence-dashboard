from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.anomaly import Anomaly
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer
from app.models.customer_feature import CustomerFeature
from app.models.order import Order
from app.models.sentiment_result import SentimentResult
from app.schemas.overview import KpiCard, NarrativeResponse, OverviewKpis

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _fmt_currency(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:.0f}"


@router.get("/kpis", response_model=OverviewKpis)
def get_overview_kpis(db: Session = Depends(get_db)):
    # --- Total customers ---
    total_customers = db.query(func.count(Customer.customer_id)).scalar() or 0

    # --- Monthly revenue (most recent 30 days of order data) ---
    latest_order_date = db.query(func.max(Order.order_date)).scalar()
    if latest_order_date:
        cutoff = (
            datetime.fromisoformat(latest_order_date) - timedelta(days=30)
        ).isoformat()
        prior_cutoff = (
            datetime.fromisoformat(latest_order_date) - timedelta(days=60)
        ).isoformat()
        monthly_revenue = (
            db.query(func.sum(Order.amount))
            .filter(Order.order_date >= cutoff)
            .scalar()
            or 0.0
        )
        prior_revenue = (
            db.query(func.sum(Order.amount))
            .filter(Order.order_date >= prior_cutoff, Order.order_date < cutoff)
            .scalar()
            or 0.0
        )
        revenue_trend = (
            ((monthly_revenue - prior_revenue) / prior_revenue * 100)
            if prior_revenue > 0
            else 0.0
        )
    else:
        monthly_revenue = 0.0
        revenue_trend = 0.0

    # --- Churn rate (avg probability across all predictions) ---
    avg_churn = (
        db.query(func.avg(ChurnPrediction.churn_probability)).scalar() or 0.0
    )
    churn_pct = avg_churn * 100

    high_risk_count = (
        db.query(func.count(ChurnPrediction.customer_id))
        .filter(ChurnPrediction.risk_tier.in_(["High", "Critical"]))
        .scalar()
        or 0
    )

    # --- Avg sentiment ---
    avg_sentiment = (
        db.query(func.avg(SentimentResult.sentiment_score)).scalar() or 0.0
    )

    # --- Active anomalies ---
    anomaly_count = db.query(func.count(Anomaly.anomaly_id)).scalar() or 0

    return OverviewKpis(
        total_customers=KpiCard(
            label="Total Customers",
            value=total_customers,
            trend=0.0,
            trend_label="all accounts",
        ),
        monthly_revenue=KpiCard(
            label="Monthly Revenue",
            value=_fmt_currency(monthly_revenue),
            trend=round(revenue_trend, 1),
            trend_label="vs prior 30d",
        ),
        churn_rate=KpiCard(
            label="Churn Rate",
            value=f"{churn_pct:.1f}%",
            trend=float(high_risk_count),
            trend_label="high/critical risk",
        ),
        avg_sentiment=KpiCard(
            label="Avg Sentiment",
            value=round(avg_sentiment, 2),
            trend=0.0,
            trend_label="across all feedback",
        ),
        active_anomalies=KpiCard(
            label="Anomalies",
            value=anomaly_count,
            trend=0.0,
            trend_label="detected",
        ),
    )


@router.get("/narrative", response_model=NarrativeResponse)
def get_narrative(db: Session = Depends(get_db)):
    # Gather summary stats for narrative generation
    total = db.query(func.count(Customer.customer_id)).scalar() or 0
    avg_churn = db.query(func.avg(ChurnPrediction.churn_probability)).scalar() or 0.0
    avg_sent = db.query(func.avg(SentimentResult.sentiment_score)).scalar() or 0.0
    high_risk = (
        db.query(func.count(ChurnPrediction.customer_id))
        .filter(ChurnPrediction.risk_tier.in_(["High", "Critical"]))
        .scalar()
        or 0
    )
    anomaly_count = db.query(func.count(Anomaly.anomaly_id)).scalar() or 0

    churn_pct = avg_churn * 100
    sentiment_label = (
        "positive" if avg_sent > 0.20 else "neutral" if avg_sent > -0.20 else "negative"
    )

    highlights = []
    concerns = []

    if churn_pct < 20:
        highlights.append(
            f"Overall churn risk is manageable at {churn_pct:.1f}%"
        )
    else:
        concerns.append(
            f"Elevated churn risk at {churn_pct:.1f}% across the customer base"
        )

    if avg_sent > 0.20:
        highlights.append(
            f"Customer sentiment is {sentiment_label} (avg score: {avg_sent:.2f})"
        )
    else:
        concerns.append(
            f"Customer sentiment trending {sentiment_label} (avg score: {avg_sent:.2f})"
        )

    if high_risk > 0:
        concerns.append(
            f"{high_risk} customers flagged as high or critical churn risk"
        )

    if anomaly_count > 0:
        concerns.append(f"{anomaly_count} anomalies detected requiring review")
    else:
        highlights.append("No anomalies detected in the current analysis window")

    summary = (
        f"Across {total:,} active customers, the platform shows a {churn_pct:.1f}% "
        f"average churn probability with {sentiment_label} overall sentiment. "
        f"{high_risk} accounts are flagged as high or critical risk."
    )

    return NarrativeResponse(
        executive_summary=summary,
        key_metrics=[
            {"label": "Total Customers", "value": total},
            {"label": "Avg Churn Probability", "value": f"{churn_pct:.1f}%"},
            {"label": "Avg Sentiment", "value": round(avg_sent, 2)},
            {"label": "High-Risk Accounts", "value": high_risk},
            {"label": "Anomalies", "value": anomaly_count},
        ],
        highlights=highlights,
        concerns=concerns,
        generated_at=datetime.utcnow().isoformat(),
    )
