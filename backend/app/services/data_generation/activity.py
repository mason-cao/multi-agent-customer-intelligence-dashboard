from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from app.services.data_generation.definitions import END_DATE, MRR_BY_TIER, EVENT_TYPES, FEATURES, uid


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
