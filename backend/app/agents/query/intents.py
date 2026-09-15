"""Deterministic intent scoring and bounded query parameters; registry order breaks ties."""

import re
from typing import Any, Dict, List, Optional, Tuple


INTENT_REGISTRY: List[Dict[str, Any]] = [
    {
        "intent": "high_risk_negative",
        "kw": [("negative sentiment", 3), ("high risk", 2), ("at risk", 1),
               ("unhappy", 2), ("frustrated", 2), ("negative", 1)],
        "description": "Actions for high-risk negative-sentiment customers",
        "result_kind": "table",
        "label": "High-risk + unhappy",
        "example": "What should we do for high-risk customers with negative sentiment?",
        "followups": ["Show the top 10 highest-risk customers",
                      "How does sentiment vary by segment?"],
    },
    {
        "intent": "customer_lookup",
        "kw": [("look up", 3), ("lookup", 3), ("who is", 3), ("customer named", 3),
               ("show me customer", 3), ("find", 2), ("search", 2), ("profile", 2),
               ("details for", 2), ("customer", 1)],
        "description": "Look up a specific customer by name, company, or ID",
        "result_kind": "table",
        "label": "Find a customer",
        "example": "Look up customer Jordan Lee",
        "followups": ["Show the top 10 highest-risk customers",
                      "Give me an overall customer intelligence summary"],
    },
    {
        "intent": "ticket_topics",
        "kw": [("ticket", 3), ("support topic", 3), ("topics", 2), ("complaint", 2),
               ("support", 1)],
        "description": "Most common support ticket topics",
        "result_kind": "distribution",
        "label": "Support topics",
        "example": "What are the most common support ticket topics?",
        "followups": ["How does sentiment vary by segment?",
                      "What should we prioritize this week?"],
    },
    {
        "intent": "industry_breakdown",
        "kw": [("industry", 3), ("industries", 3), ("vertical", 2), ("sector", 2)],
        "description": "Customer count, revenue, and churn broken down by industry",
        "result_kind": "table",
        "label": "By industry",
        "example": "How does churn vary by industry?",
        "followups": ["Break down revenue by segment",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "audit_findings",
        "kw": [("audit", 3), ("validation", 2), ("data quality", 2),
               ("trust", 1), ("warning", 1)],
        "description": "Current audit warnings and failures",
        "result_kind": "table",
        "label": "Audit findings",
        "example": "Are there any audit warnings?",
        "followups": ["Give me an overall customer intelligence summary",
                      "What are the most important executive insights?"],
    },
    {
        "intent": "executive_insights",
        "kw": [("executive", 3), ("narrative", 2), ("key insight", 2),
               ("what matters", 2), ("headline", 2), ("insight", 1)],
        "description": "Current executive narrative summaries",
        "result_kind": "list",
        "label": "Executive insights",
        "example": "What are the most important executive insights right now?",
        "followups": ["Give me an overall customer intelligence summary",
                      "What should we prioritize this week?"],
    },
    {
        "intent": "priority_actions",
        "kw": [("prioritize", 3), ("this week", 3), ("what should we do", 3),
               ("priority", 2), ("urgent", 2), ("immediate", 2),
               ("focus on", 2), ("act now", 2)],
        "description": "Highest-priority retention actions for this week",
        "result_kind": "table",
        "label": "This week's priorities",
        "example": "What should we prioritize this week?",
        "followups": ["Show the top 10 highest-risk customers",
                      "What actions are most common?"],
    },
    {
        "intent": "recommendation_dist",
        "kw": [("next best action", 3), ("recommend", 2), ("recommendation", 2),
               ("distribution", 2), ("action", 1), ("common", 1), ("frequent", 1)],
        "description": "Recommendation action distribution",
        "result_kind": "distribution",
        "label": "Recommended actions",
        "example": "What actions are most common?",
        "followups": ["What should we prioritize this week?",
                      "Break down revenue by segment"],
    },
    {
        "intent": "segment_overview",
        "kw": [("segment", 2), ("overview", 2), ("how many", 2),
               ("size", 1), ("breakdown", 1)],
        "description": "Segment sizes and key metrics",
        "result_kind": "table",
        "label": "Segment overview",
        "example": "Give me a segment overview",
        "followups": ["Break down revenue by segment",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "revenue_by_segment",
        "kw": [("revenue", 2), ("segment", 2), ("mrr", 1), ("spend", 1)],
        "description": "Total and average revenue per customer segment",
        "result_kind": "distribution",
        "label": "Revenue by segment",
        "example": "Break down revenue by segment",
        "followups": ["Give me a segment overview",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "sentiment_by_segment",
        "kw": [("sentiment", 2), ("segment", 2), ("feel", 1), ("mood", 1), ("happy", 1)],
        "description": "Average sentiment per customer segment",
        "result_kind": "distribution",
        "label": "Sentiment by segment",
        "example": "How does sentiment vary by segment?",
        "followups": ["What are the most common support ticket topics?",
                      "Which segment has the highest churn risk?"],
    },
    {
        "intent": "churn_by_segment",
        "kw": [("segment", 2), ("churn", 1), ("risk", 1), ("retention", 1)],
        "description": "Average churn risk per customer segment",
        "result_kind": "distribution",
        "label": "Churn by segment",
        "example": "Which segment has the highest churn risk?",
        "followups": ["Show the top 10 highest-risk customers",
                      "Break down revenue by segment"],
    },
    {
        "intent": "top_risk_customers",
        "kw": [("riskiest", 3), ("most likely to leave", 3), ("highest risk", 2),
               ("who will churn", 2), ("high risk", 1), ("at risk", 1),
               ("top", 1), ("customer", 1)],
        "description": "Highest-risk customers with recommended actions",
        "result_kind": "table",
        "label": "Highest-risk customers",
        "example": "Show the top 10 highest-risk customers",
        "followups": ["What should we do for high-risk customers with negative sentiment?",
                      "What should we prioritize this week?"],
    },
    {
        "intent": "customer_summary",
        "kw": [("overall", 2), ("summary", 2), ("intelligence", 2), ("dashboard", 2),
               ("everything", 2), ("snapshot", 2), ("at a glance", 2),
               ("how are we doing", 3)],
        "description": "Aggregated intelligence summary across all outputs",
        "result_kind": "metric",
        "label": "Full summary",
        "example": "Give me an overall customer intelligence summary",
        "followups": ["Which segment has the highest churn risk?",
                      "What are the most important executive insights?"],
    },
]

INTENT_META: Dict[str, Dict[str, Any]] = {
    e["intent"]: {
        "result_kind": e["result_kind"],
        "followups": e["followups"],
        "label": e["label"],
        "example": e["example"],
        "description": e["description"],
    }
    for e in INTENT_REGISTRY
}

UNSUPPORTED_FOLLOWUPS = [
    "Which segment has the highest churn risk?",
    "Show the top 10 highest-risk customers",
    "What should we prioritize this week?",
]

MIN_INTENT_SCORE = 1

SUPPORTED_DESCRIPTIONS = [entry["description"] for entry in INTENT_REGISTRY]

def _normalize(question: str) -> str:
    """Lowercase and replace non-alphanumeric runs with single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()

def build_suggestions() -> List[Dict[str, str]]:
    """Guided prompt suggestions derived from the intent registry."""
    return [
        {"intent": e["intent"], "label": e["label"], "example": e["example"]}
        for e in INTENT_REGISTRY
    ]

def _extract_lookup_term(question: str) -> str:
    """Pull a likely customer name / company / id out of a lookup question."""
    m = re.search(
        r"(?:customer named|show me customer|look up|lookup|who is|profile of|"
        r"details for|about|for|customer)\s+([A-Za-z0-9'.\- ]{2,60})",
        question,
        re.I,
    )
    if m:
        term = m.group(1).strip()
    else:
        caps = re.findall(r"\b[A-Z][\w'.\-]*(?:\s+[A-Z][\w'.\-]*)*\b", question)
        term = caps[0] if caps else ""
    term = re.sub(r"^(customer|client|account)\s+", "", term, flags=re.I).strip()
    term = re.sub(r"\s+(please|now|today|thanks|thank you).*$", "", term, flags=re.I).strip()
    return term

def extract_params(question: str, intent: str) -> Dict[str, Any]:
    """Extract safe, bound parameters from a question for the matched intent.

    Returns only scalar values. Callers pass these to handlers as bound SQL
    params — they are never string-interpolated into SQL.
    """
    params: Dict[str, Any] = {}
    if intent == "top_risk_customers":
        m = re.search(r"\b(?:top|first|highest|show me)\s+(\d{1,3})\b", question, re.I)
        if not m:
            m = re.search(r"\b(\d{1,3})\s+(?:customers?|riskiest|accounts?)\b", question, re.I)
        if m:
            params["limit"] = max(1, min(int(m.group(1)), 50))
    elif intent == "customer_lookup":
        term = _extract_lookup_term(question)
        if term:
            params["query"] = term
    return params

def _sanitize_params(raw: Any) -> Dict[str, Any]:
    """Whitelist params returned by LLM routing down to safe scalar types,
    so a model can never smuggle anything into a handler beyond limit/query."""
    params: Dict[str, Any] = {}
    if not isinstance(raw, dict):
        return params
    limit = raw.get("limit")
    if isinstance(limit, bool):
        limit = None
    if isinstance(limit, int) or (isinstance(limit, str) and limit.isdigit()):
        params["limit"] = max(1, min(int(limit), 50))
    query = raw.get("query")
    if isinstance(query, str) and query.strip():
        params["query"] = query.strip()[:80]
    return params

def classify_intent(question: str) -> Tuple[str, str]:
    """
    Classify a question into a supported intent via keyword scoring.

    Each intent's score is the sum of the weights of its keyword phrases that
    appear in the normalized question; the highest-scoring intent wins, with
    registry order breaking ties (earlier entries win). This makes rewordings
    resolve to the best match rather than the first regex hit.

    Returns (intent_name, intent_description), or ("unsupported", ...) when no
    intent clears MIN_INTENT_SCORE.
    """
    q = _normalize(question)

    best_intent: Optional[str] = None
    best_score = 0
    best_desc = ""
    for entry in INTENT_REGISTRY:
        score = sum(weight for phrase, weight in entry["kw"] if phrase in q)
        if score > best_score:
            best_score = score
            best_intent = entry["intent"]
            best_desc = entry["description"]

    if best_intent is None or best_score < MIN_INTENT_SCORE:
        return "unsupported", "Question does not match any supported query type"
    return best_intent, best_desc
