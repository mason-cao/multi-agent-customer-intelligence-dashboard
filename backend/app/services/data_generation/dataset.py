"""Generate source tables atomically, retaining only customers between stages."""

from collections.abc import Callable

import numpy as np
from faker import Faker

from app.db.database import Base
from app.services.data_generation.activity import generate_campaigns, generate_events, generate_orders
from app.services.data_generation.customers import generate_customers, generate_subscriptions
from app.services.data_generation.feedback import generate_feedback, generate_tickets
from app.services.data_generation.definitions import CHURN_RATE, NUM_CUSTOMERS


def generate_dataset(
    target_engine,
    customer_count: int = NUM_CUSTOMERS,
    churn_rate: float = CHURN_RATE,
    primary_industry: str | None = None,
    seed: int = 42,
    on_stage: Callable[[int, str], None] | None = None,
    include_outage: bool = True,
) -> dict[str, int]:
    """Append a complete dataset in one transaction; failures leave existing rows intact."""
    import app.models  # noqa: F401 — register table definitions

    rng = np.random.default_rng(seed)
    fake = Faker()
    fake.seed_instance(seed)
    if on_stage:
        on_stage(1, "Creating customer profiles")
    customers = generate_customers(rng, fake, customer_count, churn_rate, primary_industry)
    stages = (
        ("subscriptions", "Generating subscriptions", lambda: generate_subscriptions(customers, rng)),
        ("orders", "Generating orders & transactions", lambda: generate_orders(customers, rng)),
        ("behavior_events", "Building behavioral events", lambda: generate_events(customers, rng)),
        ("support_tickets", "Generating support tickets", lambda: generate_tickets(customers, rng, include_outage=include_outage)),
        ("feedback", "Generating customer feedback", lambda: generate_feedback(customers, rng, include_outage=include_outage)),
        ("campaigns", "Loading marketing campaigns", lambda: generate_campaigns(rng)),
    )
    Base.metadata.create_all(target_engine)
    counts = {"customers": len(customers)}
    with target_engine.begin() as connection:
        customers.to_sql("customers", connection, if_exists="append", index=False)
        for index, (table, label, generate) in enumerate(stages, start=2):
            if on_stage:
                on_stage(index, label)
            frame = generate()
            frame.to_sql(table, connection, if_exists="append", index=False)
            counts[table] = len(frame)
            del frame
    return counts
