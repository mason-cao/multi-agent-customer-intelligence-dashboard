"""Tests for the customers list route, including search."""

import pytest

from tests.helpers import create_workspace_with_token, workspace_session


def _seed_customers(workspace_id: str):
    from app.models.customer import Customer

    customer_ids = ["cust_search_a", "cust_search_b", "cust_search_c"]
    rows = [
        Customer(
            customer_id="cust_search_a",
            name="Jordan Lee",
            email="jordan@acme.test",
            company="Acme Analytics",
            industry="Technology",
            company_size="smb",
            plan_tier="starter",
            signup_date="2024-08-01",
            region="north_america",
            acquisition_channel="organic",
            is_churned=0,
        ),
        Customer(
            customer_id="cust_search_b",
            name="Priya Patel",
            email="priya@borealis.test",
            company="Borealis Health",
            industry="Healthcare",
            company_size="enterprise",
            plan_tier="enterprise",
            signup_date="2024-09-15",
            region="europe",
            acquisition_channel="referral",
            is_churned=0,
        ),
        Customer(
            customer_id="cust_search_c",
            name="Sam Ortiz",
            email="sam@acmecorp.test",
            company="Acme Corp",
            industry="Retail",
            company_size="startup",
            plan_tier="free",
            signup_date="2024-10-20",
            region="latam",
            acquisition_channel="paid_search",
            is_churned=0,
        ),
    ]

    db = workspace_session(workspace_id)
    try:
        db.query(Customer).filter(Customer.customer_id.in_(customer_ids)).delete(
            synchronize_session=False
        )
        db.add_all(rows)
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_customers_search_filters_by_name_and_company(client):
    workspace, headers = await create_workspace_with_token(client, "Customer Search Test")
    _seed_customers(workspace["id"])

    # No filter returns everyone
    resp = await client.get("/api/customers", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 3

    # Company match (case-insensitive substring) narrows the list and total
    resp = await client.get("/api/customers?q=acme", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {c["customer_id"] for c in body["customers"]} == {
        "cust_search_a",
        "cust_search_c",
    }

    # Name match
    resp = await client.get("/api/customers?q=priya", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["customers"][0]["name"] == "Priya Patel"

    # No match returns an empty page, not an error
    resp = await client.get("/api/customers?q=zzz-no-match", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
