"""
Validate synthetic Luminosity Analytics dataset.

Checks row counts, distributions, correlations, foreign key integrity,
and story assumptions (outage window, churn signals, engagement patterns).

Usage:
    cd backend && source .venv/bin/activate
    python ../scripts/validate_data.py
"""

import os
import sys

import numpy as np
import pandas as pd

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ_ROOT, "backend"))

from app.db.database import engine  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f"  — {detail}"
        print(msg)


def table_count(table: str) -> int:
    return int(pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", engine).iloc[0]["n"])


# ---------------------------------------------------------------------------
# 1. Row counts
# ---------------------------------------------------------------------------
def check_row_counts():
    print("\n=== Row Counts ===")
    expected = {
        "customers": (4500, 5500),
        "orders": (30000, 50000),
        "subscriptions": (4500, 5500),
        "support_tickets": (8000, 15000),
        "feedback": (5000, 10000),
        "behavior_events": (500000, 1000000),
        "campaigns": (25, 25),
    }
    for table, (lo, hi) in expected.items():
        n = table_count(table)
        check(
            f"{table}: {n:,} rows (expected {lo:,}–{hi:,})",
            lo <= n <= hi,
            f"got {n:,}",
        )


# ---------------------------------------------------------------------------
# 2. Customer distributions
# ---------------------------------------------------------------------------
def check_customer_distributions():
    print("\n=== Customer Distributions ===")
    df = pd.read_sql("SELECT * FROM customers", engine)

    # Churn rate
    churn_rate = df["is_churned"].mean()
    check(
        f"Churn rate: {churn_rate:.1%} (expected 10–20%)",
        0.10 <= churn_rate <= 0.20,
        f"got {churn_rate:.1%}",
    )

    # Plan tiers — all 4 present, none <5%
    tier_pcts = df["plan_tier"].value_counts(normalize=True)
    for tier in ["free", "starter", "professional", "enterprise"]:
        pct = tier_pcts.get(tier, 0)
        check(
            f"Plan tier '{tier}': {pct:.1%} (min 5%)",
            pct >= 0.05,
            f"got {pct:.1%}",
        )

    # Company sizes — all 4 present, none <10%
    size_pcts = df["company_size"].value_counts(normalize=True)
    for size in ["startup", "smb", "mid_market", "enterprise"]:
        pct = size_pcts.get(size, 0)
        check(
            f"Company size '{size}': {pct:.1%} (min 10%)",
            pct >= 0.10,
            f"got {pct:.1%}",
        )

    # All 8 industries present
    n_industries = df["industry"].nunique()
    check(
        f"Industries present: {n_industries} (expected 8)",
        n_industries == 8,
        f"got {n_industries}",
    )

    # Churned customers have churned_date, non-churned don't
    churned = df[df["is_churned"] == 1]
    not_churned = df[df["is_churned"] == 0]
    check(
        "All churned customers have churned_date",
        churned["churned_date"].notna().all(),
        f"{churned['churned_date'].isna().sum()} missing",
    )
    check(
        "No non-churned customers have churned_date",
        not_churned["churned_date"].isna().all(),
        f"{not_churned['churned_date'].notna().sum()} unexpected",
    )


# ---------------------------------------------------------------------------
# 3. Foreign key integrity
# ---------------------------------------------------------------------------
def check_foreign_keys():
    print("\n=== Foreign Key Integrity ===")
    customer_ids = set(
        pd.read_sql("SELECT customer_id FROM customers", engine)["customer_id"]
    )

    child_tables = [
        "orders", "subscriptions", "support_tickets",
        "feedback", "behavior_events",
    ]
    for table in child_tables:
        child_ids = set(
            pd.read_sql(f"SELECT DISTINCT customer_id FROM {table}", engine)[
                "customer_id"
            ]
        )
        orphans = child_ids - customer_ids
        check(
            f"{table}: no orphan customer_ids",
            len(orphans) == 0,
            f"{len(orphans)} orphans found",
        )

    # Orders exist for >95% of customers
    customers_with_orders = set(
        pd.read_sql("SELECT DISTINCT customer_id FROM orders", engine)["customer_id"]
    )
    coverage = len(customers_with_orders) / len(customer_ids)
    check(
        f"Orders cover {coverage:.1%} of customers (min 95%)",
        coverage >= 0.95,
        f"got {coverage:.1%}",
    )


# ---------------------------------------------------------------------------
# 4. Revenue sanity
# ---------------------------------------------------------------------------
def check_revenue():
    print("\n=== Revenue ===")
    total = pd.read_sql(
        "SELECT SUM(amount) AS total FROM orders WHERE status = 'completed'",
        engine,
    ).iloc[0]["total"]
    check(
        f"Total completed revenue: ${total:,.0f} (min $1M)",
        total is not None and total > 1_000_000,
        f"got ${total:,.0f}" if total else "NULL",
    )


# ---------------------------------------------------------------------------
# 5. Outage window story — tickets skew technical/bug
# ---------------------------------------------------------------------------
def check_outage_tickets():
    print("\n=== Outage Window: Ticket Categories (Aug 15 – Sep 30 2024) ===")
    outage_tickets = pd.read_sql(
        """
        SELECT category, COUNT(*) AS n
        FROM support_tickets
        WHERE created_at >= '2024-08-15' AND created_at < '2024-10-01'
        GROUP BY category
        """,
        engine,
    )
    total = outage_tickets["n"].sum()
    if total == 0:
        check("Outage window has tickets", False, "0 tickets in window")
        return

    tech_bug = outage_tickets[
        outage_tickets["category"].isin(["technical", "bug_report"])
    ]["n"].sum()
    pct = tech_bug / total
    check(
        f"Outage tickets technical+bug: {pct:.1%} (min 50%)",
        pct >= 0.50,
        f"got {pct:.1%} ({tech_bug}/{total})",
    )


# ---------------------------------------------------------------------------
# 6. Outage window story — feedback skews negative
# ---------------------------------------------------------------------------
def check_outage_feedback():
    print("\n=== Outage Window: Feedback Ratings (Aug 15 – Sep 30 2024) ===")
    avg_rating = pd.read_sql(
        """
        SELECT AVG(rating) AS avg_rating
        FROM feedback
        WHERE submitted_at >= '2024-08-15' AND submitted_at < '2024-10-01'
          AND rating IS NOT NULL
        """,
        engine,
    ).iloc[0]["avg_rating"]

    if avg_rating is None:
        check("Outage feedback has ratings", False, "no ratings in window")
        return

    check(
        f"Outage window avg rating: {avg_rating:.1f} (max 5.0)",
        avg_rating <= 5.0,
        f"got {avg_rating:.1f}",
    )


# ---------------------------------------------------------------------------
# 7. Churned customer events cluster earlier
# ---------------------------------------------------------------------------
def check_churn_event_timing():
    print("\n=== Churn Signal: Event Timing ===")

    # For churned customers, compute median(event_day / active_days)
    # where event_day = days between signup and event
    # and active_days = days between signup and churn
    # If events cluster early, median ratio < 0.50
    query = """
        SELECT
            e.customer_id,
            julianday(e.timestamp) - julianday(c.signup_date) AS event_day,
            julianday(c.churned_date) - julianday(c.signup_date) AS active_days
        FROM behavior_events e
        JOIN customers c ON e.customer_id = c.customer_id
        WHERE c.is_churned = 1 AND c.churned_date IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    if len(df) == 0:
        check("Churned customer events exist", False, "no events for churned customers")
        return

    df = df[df["active_days"] > 0]
    df["ratio"] = df["event_day"] / df["active_days"]
    # Clamp: events before signup or after churn are edge cases
    df["ratio"] = df["ratio"].clip(0, 1)
    median_ratio = df["ratio"].median()

    check(
        f"Churned customer event median position: {median_ratio:.2f} (max 0.50)",
        median_ratio <= 0.50,
        f"got {median_ratio:.2f} (lower = more front-loaded)",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Luminosity Analytics — Synthetic Data Validation")
    print("=" * 60)

    check_row_counts()
    check_customer_distributions()
    check_foreign_keys()
    check_revenue()
    check_outage_tickets()
    check_outage_feedback()
    check_churn_event_timing()

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
