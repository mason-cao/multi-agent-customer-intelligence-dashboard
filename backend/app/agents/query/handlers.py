"""All query handlers share the (engine, params) interface."""

from app.agents.query.segments import _handle_churn_by_segment, _handle_sentiment_by_segment, _handle_segment_overview, _handle_revenue_by_segment
from app.agents.query.customers import _handle_top_risk_customers, _handle_high_risk_negative, _handle_customer_lookup, _handle_industry_breakdown
from app.agents.query.reports import _handle_recommendation_dist, _handle_priority_actions, _handle_executive_insights, _handle_audit_findings, _handle_ticket_topics
from app.agents.query.summary import _handle_customer_summary


INTENT_HANDLERS = {
    "churn_by_segment": _handle_churn_by_segment,
    "top_risk_customers": _handle_top_risk_customers,
    "recommendation_dist": _handle_recommendation_dist,
    "sentiment_by_segment": _handle_sentiment_by_segment,
    "segment_overview": _handle_segment_overview,
    "priority_actions": _handle_priority_actions,
    "executive_insights": _handle_executive_insights,
    "audit_findings": _handle_audit_findings,
    "high_risk_negative": _handle_high_risk_negative,
    "customer_summary": _handle_customer_summary,
    "revenue_by_segment": _handle_revenue_by_segment,
    "industry_breakdown": _handle_industry_breakdown,
    "customer_lookup": _handle_customer_lookup,
    "ticket_topics": _handle_ticket_topics,
}
