"""
Synthetic data generator for Luminosity Analytics — a fictional B2B SaaS company.

Generates 18 months of correlated customer data (Jul 2024 – Dec 2025) with
realistic patterns: seasonal revenue, churn signals, sentiment drift, a
simulated Q3 2024 outage, and segment-aware behavioral distributions.

Usage:
    python scripts/generate_data.py --seed 42
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# ---------------------------------------------------------------------------
# Ensure backend models are importable
# ---------------------------------------------------------------------------
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ_ROOT, "backend"))

from app.db.database import Base, engine, DATABASE_PATH  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
START_DATE = datetime(2024, 7, 1)
END_DATE = datetime(2025, 12, 31)
NUM_CUSTOMERS = 5000
CHURN_RATE = 0.15
INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Retail",
    "Manufacturing", "Education", "Media", "Logistics",
]
COMPANY_SIZES = ["startup", "smb", "mid_market", "enterprise"]
COMPANY_SIZE_WEIGHTS = [0.30, 0.30, 0.25, 0.15]
PLAN_TIERS = ["free", "starter", "professional", "enterprise"]
PLAN_TIER_WEIGHTS = [0.10, 0.30, 0.35, 0.25]
REGIONS = ["north_america", "europe", "apac", "latam"]
REGION_WEIGHTS = [0.45, 0.25, 0.20, 0.10]
CHANNELS = ["organic", "paid_search", "referral", "partner", "content"]
CHANNEL_WEIGHTS = [0.25, 0.25, 0.20, 0.15, 0.15]

MRR_BY_TIER = {"free": 0, "starter": 49, "professional": 149, "enterprise": 499}
EVENT_TYPES = ["login", "feature_use", "page_view", "export", "invite_user", "api_call"]
FEATURES = [
    "dashboard", "reports", "integrations", "api", "automations",
    "collaboration", "analytics", "export", "admin", "billing",
]

TICKET_CATEGORIES = [
    "billing", "technical", "feature_request", "bug_report",
    "onboarding", "cancellation",
]
FEEDBACK_CHANNELS = ["nps_survey", "csat_survey", "in_app", "email", "review_site"]

# Outage window: Q3 2024 (Aug 15 – Sep 30)
OUTAGE_START = datetime(2024, 8, 15)
OUTAGE_END = datetime(2024, 9, 30)

# ---------------------------------------------------------------------------
# Ticket & feedback text templates
# ---------------------------------------------------------------------------
TICKET_TEMPLATES = {
    "billing": [
        "I was charged twice this month and need a refund processed immediately.",
        "Our invoice doesn't match the agreed pricing. Can someone review this?",
        "We're having trouble updating our payment method in the billing portal.",
        "I need to understand the charges on our latest statement, several line items are unclear.",
        "Can we switch from monthly to annual billing? What discount is available?",
        "The auto-renewal charged us but we wanted to cancel. Please reverse this.",
    ],
    "technical": [
        "The dashboard keeps timing out when I try to load reports for the past quarter.",
        "Our API integration is returning 500 errors intermittently since last night.",
        "Data sync between our CRM and your platform seems delayed by several hours.",
        "The export feature generates corrupted CSV files when the dataset exceeds 10K rows.",
        "Single sign-on stopped working after we updated our identity provider config.",
        "Performance has degraded significantly — page loads are taking 15+ seconds.",
    ],
    "feature_request": [
        "We need the ability to schedule automated report delivery to stakeholders.",
        "Can you add support for custom date ranges in the analytics dashboard?",
        "We'd love a Slack integration for real-time alerts when metrics change.",
        "It would be helpful to have role-based access controls for different team members.",
        "Please consider adding a mobile app — our field team needs access on the go.",
        "We need webhook support for triggering workflows in our internal tools.",
    ],
    "bug_report": [
        "Charts on the overview page aren't rendering correctly in Safari.",
        "The search function returns no results even for exact-match queries.",
        "Notifications are being sent twice for every alert trigger we set up.",
        "The date picker component resets to today's date every time I change tabs.",
        "User permissions changes aren't taking effect until we clear the browser cache.",
        "Filters applied on one page persist unexpectedly when navigating to another.",
    ],
    "onboarding": [
        "We just signed up and need help migrating data from our previous analytics tool.",
        "Can someone walk us through setting up our first dashboard? The docs are unclear.",
        "Our team of 15 needs onboarding — is there a group training option available?",
        "We're stuck on the API setup step. The authentication flow isn't well documented.",
        "How do we connect our Salesforce instance? The integration guide seems outdated.",
    ],
    "cancellation": [
        "We've decided to move to a competitor that better fits our workflow. Please cancel.",
        "Our budget has been cut and we can no longer justify the cost. Need to cancel.",
        "The platform doesn't meet our needs. Too many missing features for our use case.",
        "We're consolidating tools and your product didn't make the cut. Please process cancellation.",
        "Repeated outages have eroded our trust. We need to cancel effective immediately.",
    ],
}

FEEDBACK_TEMPLATES = {
    "positive": [
        "Love the new analytics dashboard! It's exactly what our team needed.",
        "Support team was incredibly responsive and resolved our issue within the hour.",
        "The product keeps getting better with each release. Very impressed with the roadmap.",
        "Onboarding was smooth and the documentation is excellent. Great experience so far.",
        "The platform has saved our team at least 10 hours per week on reporting.",
    ],
    "neutral": [
        "The product works fine for basic use cases but we need more advanced features.",
        "Decent tool overall. Some UI improvements would make it much more intuitive.",
        "It gets the job done but the learning curve is steeper than expected.",
        "Solid product. Would appreciate better integration options with our existing stack.",
        "No major complaints, but nothing that really stands out from competitors either.",
    ],
    "negative": [
        "Frustrated with the constant performance issues. This is affecting our productivity.",
        "The pricing doesn't match the value we're getting. Considering alternatives.",
        "We've reported the same bug three times and it's still not fixed. Very disappointed.",
        "The recent UI update made everything harder to find. Please revert or improve navigation.",
        "Our team has lost confidence in the platform after the recent data sync failures.",
    ],
}


def uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Customer generation
# ---------------------------------------------------------------------------
def generate_customers(
    rng: np.random.Generator,
    fake: Faker,
    customer_count: int = NUM_CUSTOMERS,
    churn_rate: float = CHURN_RATE,
    primary_industry: str = None,
) -> pd.DataFrame:
    """Generate customers with demographic attributes."""
    # Industry distribution — weight toward primary if specified
    if primary_industry and primary_industry in INDUSTRIES:
        n = len(INDUSTRIES)
        base_w = 0.5 / (n - 1)
        industry_weights = [base_w] * n
        industry_weights[INDUSTRIES.index(primary_industry)] = 0.5
    else:
        industry_weights = None

    rows = []
    for _ in range(customer_count):
        signup = START_DATE + timedelta(
            days=int(rng.exponential(scale=120))  # heavier early signups
        )
        signup = min(signup, END_DATE - timedelta(days=30))

        company_size = rng.choice(COMPANY_SIZES, p=COMPANY_SIZE_WEIGHTS)
        # Enterprise skews to enterprise tier; startups skew to free/starter
        if company_size == "enterprise":
            tier_weights = [0.02, 0.08, 0.30, 0.60]
        elif company_size == "mid_market":
            tier_weights = [0.05, 0.15, 0.50, 0.30]
        elif company_size == "smb":
            tier_weights = [0.10, 0.40, 0.35, 0.15]
        else:  # startup
            tier_weights = [0.25, 0.40, 0.25, 0.10]
        plan_tier = rng.choice(PLAN_TIERS, p=tier_weights)

        rows.append({
            "customer_id": uid(),
            "name": fake.name(),
            "email": fake.email(),
            "company": fake.company(),
            "industry": rng.choice(INDUSTRIES, p=industry_weights),
            "company_size": company_size,
            "plan_tier": plan_tier,
            "signup_date": signup.strftime("%Y-%m-%d"),
            "region": rng.choice(REGIONS, p=REGION_WEIGHTS),
            "acquisition_channel": rng.choice(CHANNELS, p=CHANNEL_WEIGHTS),
            "is_churned": 0,
            "churned_date": None,
        })

    df = pd.DataFrame(rows)

    # Assign churn — bias toward lower tiers and later signups
    churn_indices = rng.choice(
        len(df), size=int(customer_count * churn_rate), replace=False
    )
    for idx in churn_indices:
        signup = datetime.strptime(df.at[idx, "signup_date"], "%Y-%m-%d")
        # Churn happens 60-300 days after signup
        days_to_churn = int(rng.uniform(60, 300))
        churn_date = signup + timedelta(days=days_to_churn)
        if churn_date <= END_DATE:
            df.at[idx, "is_churned"] = 1
            df.at[idx, "churned_date"] = churn_date.strftime("%Y-%m-%d")

    return df


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def generate_orders(
    customers: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Generate ~40K orders correlated with customer profiles."""
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

        tier = c["plan_tier"]
        base_amount = MRR_BY_TIER.get(tier, 49)
        if tier == "free":
            num_orders = max(1, int(rng.poisson(2)))
        else:
            num_orders = max(1, int(rng.poisson(8)))

        for _ in range(num_orders):
            order_date = signup + timedelta(days=int(rng.uniform(0, active_days)))
            # Seasonal multiplier — peaks in Jan and Sep
            month = order_date.month
            seasonal = 1.0 + 0.15 * np.cos(2 * np.pi * (month - 1) / 12)
            amount = max(
                0, base_amount * seasonal * rng.lognormal(0, 0.3)
            )
            categories = ["base_subscription", "add_on", "professional_services", "overage"]
            cat_weights = [0.50, 0.25, 0.15, 0.10]

            rows.append({
                "order_id": uid(),
                "customer_id": c["customer_id"],
                "order_date": order_date.strftime("%Y-%m-%d"),
                "amount": round(amount, 2),
                "product_category": rng.choice(categories, p=cat_weights),
                "status": rng.choice(
                    ["completed", "refunded", "failed"], p=[0.92, 0.05, 0.03]
                ),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------
def generate_subscriptions(
    customers: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    rows = []
    for _, c in customers.iterrows():
        tier = c["plan_tier"]
        mrr = MRR_BY_TIER[tier] * rng.uniform(0.9, 1.1)
        signup = datetime.strptime(c["signup_date"], "%Y-%m-%d")
        renewal = signup + timedelta(days=365)
        if renewal > END_DATE:
            renewal = END_DATE

        is_churned = bool(c["is_churned"])
        payment_failures = int(rng.poisson(0.5 if is_churned else 0.1))

        rows.append({
            "subscription_id": uid(),
            "customer_id": c["customer_id"],
            "plan_tier": tier,
            "mrr": round(mrr, 2),
            "start_date": signup.strftime("%Y-%m-%d"),
            "renewal_date": renewal.strftime("%Y-%m-%d"),
            "payment_method": rng.choice(
                ["credit_card", "invoice", "ach"], p=[0.60, 0.25, 0.15]
            ),
            "payment_failures_90d": payment_failures,
            "auto_renew": 0 if is_churned else int(rng.choice([0, 1], p=[0.1, 0.9])),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Support tickets
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Behavior events
# ---------------------------------------------------------------------------
def generate_events(
    customers: pd.DataFrame, rng: np.random.Generator
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
        company_size = c["company_size"]

        # Enterprise: fewer logins, more feature breadth
        # Startup: more logins, fewer features
        if company_size == "enterprise":
            events_per_day = rng.uniform(0.1, 0.4)
            feature_breadth = rng.integers(5, 10)
        elif company_size in ("mid_market", "smb"):
            events_per_day = rng.uniform(0.15, 0.5)
            feature_breadth = rng.integers(3, 8)
        else:  # startup
            events_per_day = rng.uniform(0.3, 0.8)
            feature_breadth = rng.integers(2, 5)

        num_events = max(5, int(events_per_day * active_days))
        # Churned customers: declining activity pattern
        used_features = list(rng.choice(FEATURES, size=feature_breadth, replace=False))

        for i in range(num_events):
            # For churned customers, cluster events earlier in their lifecycle
            if is_churned:
                day_offset = int(rng.beta(2, 5) * active_days)
            else:
                day_offset = int(rng.uniform(0, active_days))

            ts = signup + timedelta(
                days=day_offset,
                hours=int(rng.uniform(8, 20)),
                minutes=int(rng.uniform(0, 60)),
            )

            event_type = rng.choice(EVENT_TYPES, p=[0.30, 0.25, 0.20, 0.10, 0.08, 0.07])
            feature_name = rng.choice(used_features) if event_type == "feature_use" else None
            session_dur = int(rng.exponential(300)) if event_type == "login" else None

            rows.append({
                "event_id": uid(),
                "customer_id": c["customer_id"],
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                "event_type": event_type,
                "feature_name": feature_name,
                "session_duration_sec": session_dur,
                "metadata": None,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------
def generate_campaigns(rng: np.random.Generator) -> pd.DataFrame:
    campaign_defs = [
        ("Q3 2024 Retention Push", "email", "At Risk", "2024-08-01", "2024-08-31"),
        ("Enterprise Onboarding Webinar", "webinar", "New Customers", "2024-09-15", "2024-09-15"),
        ("Holiday Discount 2024", "discount", "Hibernating", "2024-11-25", "2024-12-31"),
        ("New Year Kickoff", "email", "Loyal Customers", "2025-01-05", "2025-01-20"),
        ("Feature Launch Announcement", "in_app", "Champions", "2025-02-10", "2025-02-28"),
        ("Spring Re-engagement", "email", "At Risk", "2025-03-01", "2025-03-31"),
        ("Q2 Upsell Campaign", "email", "Loyal Customers", "2025-04-15", "2025-05-15"),
        ("Customer Success Check-in", "email", "Champions", "2025-05-01", "2025-05-31"),
        ("Mid-Year Review Webinar", "webinar", "New Customers", "2025-06-15", "2025-06-15"),
        ("Summer Promo", "discount", "Hibernating", "2025-07-01", "2025-07-31"),
        ("Back to Business", "email", "At Risk", "2025-09-01", "2025-09-30"),
        ("Product Update Blast", "in_app", "Champions", "2025-09-15", "2025-09-30"),
        ("Q4 Retention Sprint", "email", "At Risk", "2025-10-01", "2025-10-31"),
        ("Black Friday Deal", "discount", "Hibernating", "2025-11-24", "2025-11-30"),
        ("Year-End Review", "email", "Loyal Customers", "2025-12-01", "2025-12-15"),
        ("Referral Program Launch", "in_app", "Champions", "2024-10-01", "2024-10-31"),
        ("Startup Accelerator", "webinar", "New Customers", "2024-11-15", "2024-11-15"),
        ("API Workshop", "webinar", "Champions", "2025-01-20", "2025-01-20"),
        ("Win-Back Campaign", "email", "Hibernating", "2025-03-15", "2025-04-15"),
        ("Enterprise Expansion", "email", "Loyal Customers", "2025-04-01", "2025-04-30"),
        ("Health Check Outreach", "email", "At Risk", "2025-06-01", "2025-06-30"),
        ("New Feature Beta", "in_app", "Champions", "2025-07-15", "2025-08-15"),
        ("Training Series", "webinar", "New Customers", "2025-08-01", "2025-08-31"),
        ("Loyalty Rewards", "in_app", "Champions", "2025-10-15", "2025-11-15"),
        ("End of Year Renewal Push", "email", "At Risk", "2025-12-01", "2025-12-31"),
    ]

    rows = []
    for name, ctype, segment, start, end in campaign_defs:
        targeted = int(rng.uniform(200, 1200))
        conv = float(rng.uniform(0.03, 0.25))
        engaged = int(targeted * conv)
        rows.append({
            "campaign_id": uid(),
            "name": name,
            "type": ctype,
            "start_date": start,
            "end_date": end,
            "target_segment": segment,
            "customers_targeted": targeted,
            "customers_engaged": engaged,
            "conversion_rate": round(conv, 4),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Reusable dataset generation
# ---------------------------------------------------------------------------
def generate_dataset(
    target_engine,
    customer_count: int = NUM_CUSTOMERS,
    churn_rate: float = CHURN_RATE,
    primary_industry: str = None,
    seed: int = 42,
    on_stage=None,
    include_outage: bool = True,
) -> dict:
    """Generate a complete synthetic dataset into target_engine.

    Args:
        target_engine: SQLAlchemy engine to write data into.
        customer_count: Number of customers to generate.
        churn_rate: Fraction of customers that churn (0.0-1.0).
        primary_industry: If set, weights industry distribution toward this value.
        seed: Random seed for reproducibility.
        on_stage: Optional callback(index, name) called before each stage.
        include_outage: If True, simulates a Q3 2024 service outage.

    Returns:
        Dict mapping table names to row counts.
    """
    rng = np.random.default_rng(seed)
    fake = Faker()
    Faker.seed(seed)

    def _stage(index, name):
        if on_stage:
            on_stage(index, name)

    _stage(1, "Creating customer profiles")
    customers = generate_customers(rng, fake, customer_count, churn_rate, primary_industry)

    _stage(2, "Generating subscriptions")
    subscriptions = generate_subscriptions(customers, rng)

    _stage(3, "Generating orders & transactions")
    orders = generate_orders(customers, rng)

    _stage(4, "Building behavioral events")
    events = generate_events(customers, rng)

    _stage(5, "Generating support tickets")
    tickets = generate_tickets(customers, rng, include_outage=include_outage)

    _stage(6, "Generating customer feedback")
    feedback = generate_feedback(customers, rng, include_outage=include_outage)

    _stage(7, "Loading marketing campaigns")
    campaigns = generate_campaigns(rng)

    # Create tables in target database
    import app.models  # noqa: F401 — register models
    Base.metadata.create_all(target_engine)

    # Write all tables
    customers.to_sql("customers", target_engine, if_exists="append", index=False)
    orders.to_sql("orders", target_engine, if_exists="append", index=False)
    subscriptions.to_sql("subscriptions", target_engine, if_exists="append", index=False)
    tickets.to_sql("support_tickets", target_engine, if_exists="append", index=False)
    feedback.to_sql("feedback", target_engine, if_exists="append", index=False)
    events.to_sql("behavior_events", target_engine, if_exists="append", index=False)
    campaigns.to_sql("campaigns", target_engine, if_exists="append", index=False)

    return {
        "customers": len(customers),
        "orders": len(orders),
        "subscriptions": len(subscriptions),
        "support_tickets": len(tickets),
        "feedback": len(feedback),
        "behavior_events": len(events),
        "campaigns": len(campaigns),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main(seed: int = 42):
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    # Drop existing tables for clean regeneration of global DB
    import app.models  # noqa: F401
    Base.metadata.drop_all(engine)

    def on_stage(index, name):
        print(f"  [{index}/7] {name}...")

    print("Generating synthetic dataset...\n")
    summary = generate_dataset(
        target_engine=engine,
        seed=seed,
        on_stage=on_stage,
    )

    print("\nDone! Summary:")
    for table_name, count in summary.items():
        print(f"  {table_name}: {count:,} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic Luminosity Analytics data")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    main(args.seed)
