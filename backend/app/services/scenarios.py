"""Built-in and bounded random workspace scenarios."""

import random


SCENARIOS = {
    "velocity_saas": {
        "company_name": "Velocity SaaS",
        "industry": "Technology",
        "customer_count": 1000,
        "description": "Fast-growing startup with high engagement and low churn",
        "churn_rate": 0.08,
        "profile": "healthy_growth",
    },
    "atlas_enterprise": {
        "company_name": "Atlas Enterprise",
        "industry": "Finance",
        "customer_count": 5000,
        "description": "Mature B2B platform with mixed customer health",
        "churn_rate": 0.14,
        "profile": "mixed_health",
    },
    "beacon_analytics": {
        "company_name": "Beacon Analytics",
        "industry": "Technology",
        "customer_count": 2500,
        "description": "Mid-market analytics company experiencing a churn crisis",
        "churn_rate": 0.25,
        "profile": "churn_crisis",
    },
    "meridian_data": {
        "company_name": "Meridian Data",
        "industry": "Healthcare",
        "customer_count": 500,
        "description": "Small data company with heavy support load",
        "churn_rate": 0.12,
        "profile": "support_heavy",
    },
}


_RANDOM_PREFIXES = [
    "Nova", "Apex", "Crest", "Pulse", "Summit",
    "Orbit", "Forge", "Helix", "Prism", "Vantage",
    "Nimbus", "Cipher", "Ember", "Lumen", "Zenith",
]
_RANDOM_SUFFIXES = [
    "Labs", "Systems", "Solutions", "Group", "Technologies",
    "Analytics", "Networks", "Digital", "Dynamics", "Platforms",
]
_RANDOM_INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Retail",
    "Manufacturing", "Education", "Media", "Logistics",
]


def generate_random_scenario() -> dict:
    """Generate a bounded random company scenario configuration."""
    rng = random.Random()
    company_name = f"{rng.choice(_RANDOM_PREFIXES)} {rng.choice(_RANDOM_SUFFIXES)}"
    industry = rng.choice(_RANDOM_INDUSTRIES)
    customer_count = rng.choice([300, 500, 800, 1000, 1500, 2000, 3000, 4000, 5000, 6000])
    churn_rate = round(rng.uniform(0.06, 0.25), 2)
    include_outage = rng.choice([True, False])
    seed = rng.randint(1, 99999)

    if churn_rate <= 0.10:
        profile = "healthy_growth"
    elif churn_rate <= 0.18:
        profile = "mixed_health"
    else:
        profile = "churn_crisis"

    return {
        "company_name": company_name,
        "industry": industry,
        "customer_count": customer_count,
        "churn_rate": churn_rate,
        "include_outage": include_outage,
        "profile": profile,
        "seed": seed,
    }


