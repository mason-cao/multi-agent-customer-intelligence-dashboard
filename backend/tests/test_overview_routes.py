"""Tests for overview dashboard route resilience."""

import pytest


def _seed_overview_orders():
    from app.db.database import SessionLocal
    from app.models.order import Order

    order_ids = [
        "overview_bad_date",
        "overview_current_window",
        "overview_prior_window",
    ]
    db = SessionLocal()
    try:
        db.query(Order).filter(Order.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.add_all(
            [
                Order(
                    order_id="overview_bad_date",
                    customer_id="overview_customer",
                    order_date="not-a-date",
                    amount=999_999.0,
                    product_category="test",
                    status="paid",
                ),
                Order(
                    order_id="overview_current_window",
                    customer_id="overview_customer",
                    order_date="2024-03-31T00:00:00",
                    amount=100.0,
                    product_category="test",
                    status="paid",
                ),
                Order(
                    order_id="overview_prior_window",
                    customer_id="overview_customer",
                    order_date="2024-02-20T00:00:00",
                    amount=50.0,
                    product_category="test",
                    status="paid",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    return order_ids


def _cleanup_overview_orders(order_ids: list[str]):
    from app.db.database import SessionLocal
    from app.models.order import Order

    db = SessionLocal()
    try:
        db.query(Order).filter(Order.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_overview_kpis_ignore_malformed_order_dates(client):
    order_ids = _seed_overview_orders()
    try:
        resp = await client.get("/api/overview/kpis")
        assert resp.status_code == 200
        body = resp.json()
        assert body["monthly_revenue"]["value"] == "$100"
        assert body["monthly_revenue"]["trend"] == 100.0
    finally:
        _cleanup_overview_orders(order_ids)
