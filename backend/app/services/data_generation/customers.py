from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from faker import Faker
from app.services.data_generation.definitions import START_DATE, END_DATE, NUM_CUSTOMERS, CHURN_RATE, INDUSTRIES, COMPANY_SIZES, COMPANY_SIZE_WEIGHTS, PLAN_TIERS, REGIONS, REGION_WEIGHTS, CHANNELS, CHANNEL_WEIGHTS, MRR_BY_TIER, uid


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
