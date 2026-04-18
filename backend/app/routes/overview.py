from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from sqlalchemy import text as sql_text

from app.db.database import get_db
from app.utils.error_handling import handle_errors
from app.models.anomaly import Anomaly
from app.models.churn_prediction import ChurnPrediction
from app.models.customer import Customer
from app.models.customer_feature import CustomerFeature
from app.models.order import Order
from app.models.sentiment_result import SentimentResult
from app.schemas.overview import KpiCard, NarrativeResponse, OverviewKpis

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/overview", tags=["overview"])


def _read_workspace_context(db: Session) -> dict:
    """Read workspace_context key-value pairs, returning empty dict on failure."""
    try:
        rows = db.execute(sql_text("SELECT key, value FROM workspace_context")).fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception:
        logger.warning("workspace_context_read_failed", exc_info=True)
        return {}


def _fmt_currency(amount: float) -> str:
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:.0f}"


def _parse_order_datetime(value) -> datetime | None:
    """Parse an order date defensively, normalizing aware values to naive UTC."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _compute_recent_revenue(order_rows) -> tuple[float, float]:
    """Return latest-30-day revenue and prior-30-day trend from valid order dates."""
    parsed_orders = []
    for row in order_rows:
        order_date = _parse_order_datetime(row.order_date)
        if order_date is None:
            continue
        parsed_orders.append((order_date, float(row.amount or 0.0)))

    if not parsed_orders:
        return 0.0, 0.0

    latest_order_date = max(order_date for order_date, _ in parsed_orders)
    cutoff = latest_order_date - timedelta(days=30)
    prior_cutoff = latest_order_date - timedelta(days=60)

    monthly_revenue = sum(
        amount for order_date, amount in parsed_orders if order_date >= cutoff
    )
    prior_revenue = sum(
        amount
        for order_date, amount in parsed_orders
        if prior_cutoff <= order_date < cutoff
    )
    revenue_trend = (
        ((monthly_revenue - prior_revenue) / prior_revenue * 100)
        if prior_revenue > 0
        else 0.0
    )
    return monthly_revenue, revenue_trend


@router.get("/kpis", response_model=OverviewKpis)
@handle_errors("get_overview_kpis")
def get_overview_kpis(db: Session = Depends(get_db)):
    # --- Total customers ---
    total_customers = db.query(func.count(Customer.customer_id)).scalar() or 0

    # --- Monthly revenue (most recent 30 days of valid order data) ---
    order_rows = db.query(Order.order_date, Order.amount).all()
    monthly_revenue, revenue_trend = _compute_recent_revenue(order_rows)

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
@handle_errors("get_narrative")
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

    # Include scenario description if available
    ws_ctx = _read_workspace_context(db)
    scenario_desc = ws_ctx.get("scenario_description", "")
    company_name = ws_ctx.get("company_name", "the platform")

    prefix = ""
    if scenario_desc:
        prefix = f"{scenario_desc} "

    summary = (
        f"{prefix}Across {total:,} active customers, {company_name} shows a {churn_pct:.1f}% "
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
