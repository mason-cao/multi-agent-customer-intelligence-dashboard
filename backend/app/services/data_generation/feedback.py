from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from app.services.data_generation.definitions import END_DATE, TICKET_CATEGORIES, FEEDBACK_CHANNELS, OUTAGE_START, OUTAGE_END, TICKET_TEMPLATES, FEEDBACK_TEMPLATES, uid


def generate_tickets(
    customers: pd.DataFrame, rng: np.random.Generator, include_outage: bool = True
) -> pd.DataFrame:
    rows = []
    for _, c in customers.iterrows():
        signup = datetime.strptime(c["signup_date"], "%Y-%m-%d")
        end = (
            datetime.strptime(c["churned_date"], "%Y-%m-%d")
            if c["is_churned"]
            else END_DATE
        )
        active_days = (end - signup).days
        if active_days < 1:
            continue

        is_churned = bool(c["is_churned"])
        num_tickets = int(rng.poisson(3.5 if is_churned else 2.0))

        for _ in range(num_tickets):
            created = signup + timedelta(days=int(rng.uniform(0, active_days)))

            # During outage, more technical/bug tickets
            if include_outage and OUTAGE_START <= created <= OUTAGE_END:
                cat_weights = [0.10, 0.35, 0.05, 0.35, 0.05, 0.10]
            elif is_churned and (end - created).days < 30:
                # Near-churn: more cancellation/billing
                cat_weights = [0.25, 0.15, 0.05, 0.10, 0.05, 0.40]
            else:
                cat_weights = [0.20, 0.25, 0.15, 0.15, 0.15, 0.10]

            category = rng.choice(TICKET_CATEGORIES, p=cat_weights)
            templates = TICKET_TEMPLATES[category]
            text = rng.choice(templates)

            priority_weights = (
                [0.10, 0.25, 0.35, 0.30]
                if include_outage and OUTAGE_START <= created <= OUTAGE_END
                else [0.30, 0.35, 0.25, 0.10]
            )

            resolved_at = None
            resolution_status = rng.choice(
                ["open", "in_progress", "resolved", "escalated"],
                p=[0.10, 0.10, 0.70, 0.10],
            )
            if resolution_status == "resolved":
                resolved_at = (
                    created + timedelta(hours=int(rng.exponential(48)))
                ).strftime("%Y-%m-%dT%H:%M:%S")

            rows.append({
                "ticket_id": uid(),
                "customer_id": c["customer_id"],
                "created_at": created.strftime("%Y-%m-%dT%H:%M:%S"),
                "resolved_at": resolved_at,
                "category": category,
                "priority": rng.choice(
                    ["low", "medium", "high", "urgent"], p=priority_weights
                ),
                "subject": text[:60] + ("..." if len(text) > 60 else ""),
                "text": text,
                "resolution_status": resolution_status,
            })
    return pd.DataFrame(rows)

def generate_feedback(
    customers: pd.DataFrame, rng: np.random.Generator, include_outage: bool = True
) -> pd.DataFrame:
    rows = []
    for _, c in customers.iterrows():
        signup = datetime.strptime(c["signup_date"], "%Y-%m-%d")
        end = (
            datetime.strptime(c["churned_date"], "%Y-%m-%d")
            if c["is_churned"]
            else END_DATE
        )
        active_days = (end - signup).days
        if active_days < 1:
            continue

        is_churned = bool(c["is_churned"])
        num_feedback = int(rng.poisson(1.8 if is_churned else 1.5))

        for _ in range(num_feedback):
            submitted = signup + timedelta(days=int(rng.uniform(0, active_days)))

            # Sentiment influenced by outage window and churn status
            if include_outage and OUTAGE_START <= submitted <= OUTAGE_END:
                sentiment_bucket = rng.choice(
                    ["positive", "neutral", "negative"], p=[0.15, 0.25, 0.60]
                )
            elif is_churned and (end - submitted).days < 60:
                sentiment_bucket = rng.choice(
                    ["positive", "neutral", "negative"], p=[0.10, 0.20, 0.70]
                )
            else:
                sentiment_bucket = rng.choice(
                    ["positive", "neutral", "negative"], p=[0.50, 0.30, 0.20]
                )

            templates = FEEDBACK_TEMPLATES[sentiment_bucket]
            text = rng.choice(templates)

            rating_map = {"positive": (7, 10), "neutral": (5, 7), "negative": (1, 5)}
            lo, hi = rating_map[sentiment_bucket]
            rating = int(rng.uniform(lo, hi + 1))

            rows.append({
                "feedback_id": uid(),
                "customer_id": c["customer_id"],
                "submitted_at": submitted.strftime("%Y-%m-%dT%H:%M:%S"),
                "channel": rng.choice(FEEDBACK_CHANNELS),
                "rating": min(rating, 10),
                "text": text,
            })
    return pd.DataFrame(rows)
