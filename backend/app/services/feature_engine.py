"""
Feature computation functions for the BehaviorAgent.

Each function queries raw source tables and returns a DataFrame indexed by
customer_id. The BehaviorAgent merges these into the customer_features table.

All functions are pure — they read from the DB and return DataFrames.
No side effects, no writes.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Reference date — the "now" point for computing recency-based features.
# Set to end of synthetic data range.
# ---------------------------------------------------------------------------
DEFAULT_REFERENCE_DATE = datetime(2025, 12, 31)


def compute_login_features(
    engine, reference_date: datetime = None
) -> pd.DataFrame:
    """
    Compute login frequency features per customer.

    Returns DataFrame with columns:
        customer_id, login_frequency_7d, login_frequency_30d
    """
    ref = reference_date or DEFAULT_REFERENCE_DATE
    d7 = (ref - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
    d30 = (ref - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    ref_str = ref.strftime("%Y-%m-%dT%H:%M:%S")

    # 7-day logins
    q7 = pd.read_sql(
        text(
            "SELECT customer_id, COUNT(*) AS login_frequency_7d "
            "FROM behavior_events "
            "WHERE event_type = 'login' AND timestamp >= :d7 AND timestamp <= :ref "
            "GROUP BY customer_id"
        ),
        engine,
        params={"d7": d7, "ref": ref_str},
    )

    # 30-day logins
    q30 = pd.read_sql(
        text(
            "SELECT customer_id, COUNT(*) AS login_frequency_30d "
            "FROM behavior_events "
            "WHERE event_type = 'login' AND timestamp >= :d30 AND timestamp <= :ref "
            "GROUP BY customer_id"
        ),
        engine,
        params={"d30": d30, "ref": ref_str},
    )

    result = q7.merge(q30, on="customer_id", how="outer")
    result = result.fillna(0)
    result["login_frequency_7d"] = result["login_frequency_7d"].astype(int)
    result["login_frequency_30d"] = result["login_frequency_30d"].astype(int)
    return result


def compute_engagement_features(
    engine, reference_date: datetime = None
) -> pd.DataFrame:
    """
    Compute engagement features per customer.

    Returns DataFrame with columns:
        customer_id, feature_usage_breadth, session_duration_avg, trend_direction
    """
    ref = reference_date or DEFAULT_REFERENCE_DATE
    ref_str = ref.strftime("%Y-%m-%dT%H:%M:%S")

    # Feature breadth: count of distinct features used (all time)
    breadth = pd.read_sql(
        text(
            "SELECT customer_id, COUNT(DISTINCT feature_name) AS feature_usage_breadth "
            "FROM behavior_events "
            "WHERE event_type = 'feature_use' AND feature_name IS NOT NULL "
            "AND timestamp <= :ref "
            "GROUP BY customer_id"
        ),
        engine,
        params={"ref": ref_str},
    )

    # Average session duration from login events
    duration = pd.read_sql(
        text(
            "SELECT customer_id, AVG(session_duration_sec) AS session_duration_avg "
            "FROM behavior_events "
            "WHERE event_type = 'login' AND session_duration_sec IS NOT NULL "
            "AND timestamp <= :ref "
            "GROUP BY customer_id"
        ),
        engine,
        params={"ref": ref_str},
    )

    # Trend direction: linear regression slope on weekly login counts
    # over the last 12 weeks
    d12w = (ref - timedelta(weeks=12)).strftime("%Y-%m-%dT%H:%M:%S")
    weekly_logins = pd.read_sql(
        text(
            "SELECT customer_id, "
            "  CAST(((julianday(timestamp) - julianday(:d12w)) / 7) AS INTEGER) AS week_num, "
            "  COUNT(*) AS cnt "
            "FROM behavior_events "
            "WHERE event_type = 'login' AND timestamp >= :d12w AND timestamp <= :ref "
            "GROUP BY customer_id, week_num"
        ),
        engine,
        params={"d12w": d12w, "ref": ref_str},
    )

    trend_rows = []
    if not weekly_logins.empty:
        for cid, group in weekly_logins.groupby("customer_id"):
            if len(group) < 2:
                trend_rows.append({"customer_id": cid, "trend_direction": "stable"})
                continue
            x = group["week_num"].values.astype(float)
            y = group["cnt"].values.astype(float)
            # Simple linear regression slope
            if x.std() == 0:
                slope = 0.0
            else:
                slope = np.polyfit(x, y, 1)[0]
            if slope > 0.1:
                direction = "increasing"
            elif slope < -0.1:
                direction = "declining"
            else:
                direction = "stable"
            trend_rows.append({"customer_id": cid, "trend_direction": direction})

    trend_df = pd.DataFrame(trend_rows) if trend_rows else pd.DataFrame(
        columns=["customer_id", "trend_direction"]
    )

    result = breadth.merge(duration, on="customer_id", how="outer")
    result = result.merge(trend_df, on="customer_id", how="outer")
    result["feature_usage_breadth"] = result["feature_usage_breadth"].fillna(0).astype(int)
    result["session_duration_avg"] = result["session_duration_avg"].fillna(0.0)
    result["trend_direction"] = result["trend_direction"].fillna("stable")
    return result


def compute_revenue_features(engine) -> pd.DataFrame:
    """
    Compute revenue features per customer.

    Returns DataFrame with columns:
        customer_id, total_revenue, order_count, days_since_last_order, avg_order_value
    """
    ref_str = DEFAULT_REFERENCE_DATE.strftime("%Y-%m-%d")

    revenue = pd.read_sql(
        text(
            "SELECT customer_id, "
            "  SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) AS total_revenue, "
            "  COUNT(CASE WHEN status = 'completed' THEN 1 END) AS order_count, "
            "  MAX(order_date) AS last_order_date "
            "FROM orders "
            "GROUP BY customer_id"
        ),
        engine,
    )

    if revenue.empty:
        return pd.DataFrame(
            columns=["customer_id", "total_revenue", "order_count",
                      "days_since_last_order", "avg_order_value"]
        )

    revenue["days_since_last_order"] = revenue["last_order_date"].apply(
        lambda d: (DEFAULT_REFERENCE_DATE - datetime.strptime(d, "%Y-%m-%d")).days
        if pd.notna(d) else 999
    )
    revenue["avg_order_value"] = (
        revenue["total_revenue"] / revenue["order_count"].clip(lower=1)
    )
    revenue = revenue.drop(columns=["last_order_date"])
    revenue["total_revenue"] = revenue["total_revenue"].round(2)
    revenue["avg_order_value"] = revenue["avg_order_value"].round(2)
    return revenue


def compute_support_features(
    engine, reference_date: datetime = None
) -> pd.DataFrame:
    """
    Compute support ticket features per customer.

    Returns DataFrame with columns:
        customer_id, support_ticket_count_30d
    """
    ref = reference_date or DEFAULT_REFERENCE_DATE
    d30 = (ref - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    ref_str = ref.strftime("%Y-%m-%dT%H:%M:%S")

    tickets = pd.read_sql(
        text(
            "SELECT customer_id, COUNT(*) AS support_ticket_count_30d "
            "FROM support_tickets "
            "WHERE created_at >= :d30 AND created_at <= :ref "
            "GROUP BY customer_id"
        ),
        engine,
        params={"d30": d30, "ref": ref_str},
    )
    tickets["support_ticket_count_30d"] = tickets["support_ticket_count_30d"].astype(int)
    return tickets
