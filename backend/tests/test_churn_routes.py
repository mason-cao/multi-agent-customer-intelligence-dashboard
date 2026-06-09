"""Tests for churn dashboard route resilience."""

import pytest

from tests.helpers import create_workspace_with_token, workspace_session


def _seed_churn_route_data(workspace_id: str):
    from app.models.churn_prediction import ChurnPrediction
    from app.models.customer import Customer

    db = workspace_session(workspace_id)
    customer_ids = ["test_bad_factors", "test_valid_factors"]
    try:
        db.query(ChurnPrediction).filter(
            ChurnPrediction.customer_id.in_(customer_ids)
        ).delete(synchronize_session=False)
        db.query(Customer).filter(
            Customer.customer_id.in_(customer_ids)
        ).delete(synchronize_session=False)

        db.add_all(
            [
                Customer(
                    customer_id="test_bad_factors",
                    name="Bad Factors",
                    email="bad@example.com",
                    company="Test Co",
                    industry="Technology",
                    company_size="SMB",
                    plan_tier="Pro",
                    signup_date="2024-01-01",
                    region="NA",
                    acquisition_channel="Direct",
                    is_churned=0,
                ),
                Customer(
                    customer_id="test_valid_factors",
                    name="Valid Factors",
                    email="valid@example.com",
                    company="Test Co",
                    industry="Technology",
                    company_size="SMB",
                    plan_tier="Pro",
                    signup_date="2024-01-01",
                    region="NA",
                    acquisition_channel="Direct",
                    is_churned=0,
                ),
                ChurnPrediction(
                    customer_id="test_bad_factors",
                    churn_probability=0.91,
                    risk_tier="Critical",
                    top_risk_factors="{bad-json",
                ),
                ChurnPrediction(
                    customer_id="test_valid_factors",
                    churn_probability=0.75,
                    risk_tier="High",
                    top_risk_factors=(
                        '[{"descriptor":"Low engagement","feature":"engagement_score",'
                        '"importance":"0.42"},"bad-item",{"feature":"ignored","importance":"bad"}]'
                    ),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    return customer_ids


def _cleanup_churn_route_data(workspace_id: str, customer_ids: list[str]):
    from app.models.churn_prediction import ChurnPrediction
    from app.models.customer import Customer

    db = workspace_session(workspace_id)
    try:
        db.query(ChurnPrediction).filter(
            ChurnPrediction.customer_id.in_(customer_ids)
        ).delete(synchronize_session=False)
        db.query(Customer).filter(
            Customer.customer_id.in_(customer_ids)
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_at_risk_customers_tolerates_malformed_risk_factors(client):
    workspace, headers = await create_workspace_with_token(client, "Churn Route Test")
    customer_ids = _seed_churn_route_data(workspace["id"])
    try:
        resp = await client.get("/api/churn/at-risk?limit=2", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["customer_id"] == "test_bad_factors"
        assert body[0]["top_risk_factor"] == "N/A"
        assert body[1]["top_risk_factor"] == "Low engagement"
    finally:
        _cleanup_churn_route_data(workspace["id"], customer_ids)


@pytest.mark.asyncio
async def test_feature_importance_tolerates_malformed_risk_factors(client):
    workspace, headers = await create_workspace_with_token(client, "Feature Route Test")
    customer_ids = _seed_churn_route_data(workspace["id"])
    try:
        resp = await client.get("/api/churn/feature-importance", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body == [{"feature": "engagement_score", "importance": 0.42}]
    finally:
        _cleanup_churn_route_data(workspace["id"], customer_ids)
