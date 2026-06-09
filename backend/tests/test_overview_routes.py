"""Tests for overview dashboard route resilience."""

import pytest

from tests.helpers import create_workspace_with_token, workspace_session


def _seed_overview_orders(workspace_id: str):
    from app.models.order import Order

    order_ids = [
        "overview_bad_date",
        "overview_current_window",
        "overview_prior_window",
    ]
    db = workspace_session(workspace_id)
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


def _cleanup_overview_orders(workspace_id: str, order_ids: list[str]):
    from app.models.order import Order

    db = workspace_session(workspace_id)
    try:
        db.query(Order).filter(Order.order_id.in_(order_ids)).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_overview_kpis_ignore_malformed_order_dates(client):
    workspace, headers = await create_workspace_with_token(client, "Overview Route Test")
    order_ids = _seed_overview_orders(workspace["id"])
    try:
        resp = await client.get("/api/overview/kpis", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["monthly_revenue"]["value"] == "$100"
        assert body["monthly_revenue"]["trend"] == 100.0
    finally:
        _cleanup_overview_orders(workspace["id"], order_ids)
