"""
SentimentAgent — deterministic sentiment analysis with keyword enrichment.

Hybrid approach:
  - Feedback: rating-based scoring (linear map from 1-10 to [-1,+1])
  - Tickets:  rule-based scoring (category + priority + resolution)
  - Both:     keyword-based topic extraction, emotion detection

No LLM calls required — fully deterministic and offline.

Inputs:  feedback (7,651 rows), support_tickets (11,080 rows)
Outputs: sentiment_results (~18,700 rows),
         updates customer_features.avg_sentiment + nps_score
Phase:   1 (no agent dependencies)
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import pandas as pd
from sqlalchemy import text

from app.agents.base import BaseAgent


# ── Topic taxonomy: keyword → topic mapping ──────────────────────

TOPIC_KEYWORDS = {
    "billing_confusion": [
        "billing", "invoice", "charge", "payment", "price",
        "pricing", "cost", "subscription", "renew",
    ],
    "performance": [
        "slow", "performance", "speed", "timeout", "latency",
        "loading", "lag", "timing out",
    ],
    "missing_feature": [
        "feature", "missing", "need", "wish", "request",
        "roadmap", "ability", "would like",
    ],
    "onboarding": [
        "onboard", "setup", "getting started", "learning curve",
        "training", "documentation",
    ],
    "data_quality": [
        "data", "sync", "export", "import", "csv",
        "corrupt", "report", "accurate",
    ],
    "integration": [
        "integration", "api", "connect", "third-party",
        "plugin", "webhook", "integrate",
    ],
    "support_quality": [
        "support", "help", "responsive", "resolved",
        "response time", "team",
    ],
    "usability": [
        "ui", "interface", "intuitive", "confusing",
        "user experience", "ux", "design", "easy to use",
    ],
    "reliability": [
        "down", "outage", "crash", "bug", "error",
        "broken", "fail", "issue", "unstable",
    ],
    "security": [
        "security", "password", "auth", "sso",
        "permission", "access", "sign-on",
    ],
    "value": [
        "value", "worth", "roi", "productive",
        "efficiency", "save", "hours",
    ],
    "communication": [
        "communicate", "update", "notify",
        "announcement", "changelog",
    ],
}


# ── Emotion detection keywords ───────────────────────────────────

EMOTION_KEYWORDS = {
    "frustration": [
        "frustrated", "annoying", "annoyed", "ridiculous",
        "unacceptable", "fed up", "terrible",
    ],
    "satisfaction": [
        "happy", "pleased", "satisfied", "great",
        "excellent", "love", "wonderful",
    ],
    "disappointment": [
        "disappointed", "let down", "expected more",
        "unfortunate", "disappointing",
    ],
    "enthusiasm": [
        "amazing", "impressed", "fantastic",
        "excited", "incredible",
    ],
    "confusion": [
        "confusing", "unclear", "don't understand",
        "complicated", "lost", "steep",
    ],
    "gratitude": [
        "thanks", "thank", "appreciate", "grateful", "helpful",
    ],
    "anxiety": [
        "worried", "concerned", "risk", "afraid",
        "uncertain", "confidence",
    ],
}


# ── Keyword sets for score adjustment ────────────────────────────

POSITIVE_WORDS = frozenset({
    "love", "great", "excellent", "amazing", "fantastic", "impressed",
    "helpful", "responsive", "intuitive", "easy", "wonderful", "perfect",
    "saved", "efficient", "recommend", "best", "appreciate", "better",
})

NEGATIVE_WORDS = frozenset({
    "frustrated", "broken", "terrible", "worst", "awful", "horrible",
    "disappointed", "slow", "crash", "bug", "fail", "failed", "poor",
    "unacceptable", "confusing", "corrupt", "lost", "cancel", "alternative",
})


# ── Ticket scoring rules ────────────────────────────────────────

CATEGORY_SCORES = {
    "cancellation": -0.70,
    "bug_report": -0.50,
    "technical": -0.30,
    "billing": -0.30,
    "feature_request": -0.10,
    "onboarding": 0.00,
}

PRIORITY_MODIFIERS = {
    "urgent": -0.15,
    "high": -0.05,
    "medium": 0.00,
    "low": 0.05,
}

RESOLUTION_MODIFIERS = {
    "resolved": 0.15,
    "open": 0.00,
    "escalated": -0.10,
}


# ── Label thresholds ─────────────────────────────────────────────

NEGATIVE_THRESHOLD = -0.20
POSITIVE_THRESHOLD = 0.20


class SentimentAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "sentiment"

    # ──────────────────────────────────────────────────────────────
    # Main run
    # ──────────────────────────────────────────────────────────────

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        # Step 1 — Load text sources
        feedback = pd.read_sql(
            text(
                "SELECT feedback_id, customer_id, submitted_at, "
                "channel, rating, text FROM feedback"
            ),
            engine,
        )
        tickets = pd.read_sql(
            text(
                "SELECT ticket_id, customer_id, category, priority, "
                "text, resolution_status FROM support_tickets"
            ),
            engine,
        )
        self._logger.info(
            "loaded_sources", feedback=len(feedback), tickets=len(tickets),
        )

        # Step 2 — Score each source
        fb_results = self._score_feedback(feedback)
        tk_results = self._score_tickets(tickets)

        # Step 3 — Combine and write to sentiment_results
        all_results = pd.concat([fb_results, tk_results], ignore_index=True)
        all_results["computed_at"] = datetime.now(timezone.utc).isoformat()

        self._logger.info("writing_sentiment_results", rows=len(all_results))
        db.execute(text("DELETE FROM sentiment_results"))
        db.commit()
        all_results.to_sql(
            "sentiment_results", engine, if_exists="append", index=False,
        )

        # Step 4 — Aggregate to customer level and update customer_features
        customers_updated = self._update_customer_aggregates(
            all_results, feedback, db, engine,
        )

        # Step 5 — Build summary
        label_dist = all_results["sentiment_label"].value_counts().to_dict()
        avg_score = round(float(all_results["sentiment_score"].mean()), 4)

        topic_counts: Dict[str, int] = {}
        for topics_json in all_results["topics"].dropna():
            try:
                for t in json.loads(topics_json):
                    topic_counts[t] = topic_counts.get(t, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

        top_topics = dict(
            sorted(topic_counts.items(), key=lambda x: -x[1])[:10]
        )

        self._logger.info(
            "sentiment_complete",
            total_docs=len(all_results),
            label_distribution=label_dist,
            avg_score=avg_score,
        )

        # Query total customer count for proportional validation
        total_customers = pd.read_sql(
            text("SELECT COUNT(*) AS n FROM customers"), engine
        )["n"].iloc[0]

        return {
            "status": "completed",
            "rows_affected": len(all_results),
            "input_doc_count": len(feedback) + len(tickets),
            "total_customers": int(total_customers),
            "tokens_used": 0,
            "model_used": None,
            "sentiment_summary": {
                "total_documents": len(all_results),
                "by_source": {
                    "feedback": len(fb_results),
                    "ticket": len(tk_results),
                },
                "label_distribution": label_dist,
                "avg_score": avg_score,
                "top_topics": top_topics,
                "customers_with_sentiment": customers_updated["with_sentiment"],
                "customers_with_nps": customers_updated["with_nps"],
            },
        }

    # ──────────────────────────────────────────────────────────────
    # Feedback scoring — rating-based with keyword adjustment
    # ──────────────────────────────────────────────────────────────

    def _score_feedback(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, r in df.iterrows():
            txt = r["text"] or ""
            rating = r["rating"]

            # Linear map: rating 1→−1.0, 5.5→0.0, 10→+1.0
            base_score = (rating - 5.5) / 4.5
            # Keyword adjustment scaled to ±0.075 so rating dominates
            adj = self._keyword_adjustment(txt) * 0.5
            score = round(max(-1.0, min(1.0, base_score + adj)), 4)

            rows.append({
                "document_id": r["feedback_id"],
                "document_type": "feedback",
                "customer_id": r["customer_id"],
                "sentiment_score": score,
                "sentiment_label": _score_to_label(score),
                "emotions": json.dumps(self._extract_emotions(txt, score)),
                "topics": json.dumps(self._extract_topics(txt)),
                "summary": txt[:200],
            })
        return pd.DataFrame(rows)

    # ──────────────────────────────────────────────────────────────
    # Ticket scoring — category + priority + resolution + keywords
    # ──────────────────────────────────────────────────────────────

    def _score_tickets(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, r in df.iterrows():
            txt = r["text"] or ""
            category = r["category"] or ""
            priority = r["priority"] or "medium"
            resolution = r["resolution_status"] or "open"

            base = CATEGORY_SCORES.get(category, -0.20)
            base += PRIORITY_MODIFIERS.get(priority, 0.0)
            base += RESOLUTION_MODIFIERS.get(resolution, 0.0)
            base += self._keyword_adjustment(txt)
            score = round(max(-1.0, min(1.0, base)), 4)

            # Topics: ticket category first, then keyword matches
            topics = [category] if category else []
            topics.extend(self._extract_topics(txt))
            topics = list(dict.fromkeys(topics))[:5]  # dedupe, max 5

            rows.append({
                "document_id": r["ticket_id"],
                "document_type": "ticket",
                "customer_id": r["customer_id"],
                "sentiment_score": score,
                "sentiment_label": _score_to_label(score),
                "emotions": json.dumps(self._extract_emotions(txt, score)),
                "topics": json.dumps(topics),
                "summary": txt[:200],
            })
        return pd.DataFrame(rows)

    # ──────────────────────────────────────────────────────────────
    # Text analysis helpers
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _keyword_adjustment(text: str) -> float:
        """Score adjustment from positive/negative keyword presence.
        Returns value in [-0.15, +0.15]."""
        words = set(re.findall(r"\b\w+\b", text.lower()))
        pos = len(words & POSITIVE_WORDS)
        neg = len(words & NEGATIVE_WORDS)
        return max(-0.15, min(0.15, (pos - neg) * 0.05))

    @staticmethod
    def _extract_topics(text: str) -> List[str]:
        """Match text against topic taxonomy. Returns up to 3 topics."""
        text_lower = text.lower()
        matched = []
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(topic)
        return matched[:3]

    @staticmethod
    def _extract_emotions(text: str, score: float) -> List[str]:
        """Detect emotions from keywords, with score-based fallback."""
        text_lower = text.lower()
        emotions = []
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                emotions.append(emotion)
        # Fallback: infer from score when no keywords matched
        if not emotions:
            if score > 0.3:
                emotions = ["satisfaction"]
            elif score < -0.3:
                emotions = ["frustration"]
            else:
                emotions = ["indifference"]
        return emotions[:3]

    # ──────────────────────────────────────────────────────────────
    # Customer-level aggregation
    # ──────────────────────────────────────────────────────────────

    def _update_customer_aggregates(
        self,
        results: pd.DataFrame,
        feedback: pd.DataFrame,
        db,
        engine,
    ) -> Dict[str, int]:
        """Compute avg_sentiment and nps_score per customer, write to customer_features."""

        # Average sentiment across all documents per customer
        cust_sentiment = (
            results.groupby("customer_id")["sentiment_score"]
            .mean()
            .round(4)
            .reset_index()
            .rename(columns={"sentiment_score": "avg_sentiment"})
        )

        # NPS: most recent NPS survey rating per customer
        nps_data = feedback[feedback["channel"] == "nps_survey"].copy()
        if not nps_data.empty:
            nps_data = nps_data.sort_values("submitted_at")
            nps_per_cust = (
                nps_data.groupby("customer_id")["rating"]
                .last()
                .reset_index()
                .rename(columns={"rating": "nps_score"})
            )
        else:
            nps_per_cust = pd.DataFrame(columns=["customer_id", "nps_score"])

        # Write avg_sentiment
        sentiment_count = 0
        for _, row in cust_sentiment.iterrows():
            db.execute(
                text(
                    "UPDATE customer_features "
                    "SET avg_sentiment = :score "
                    "WHERE customer_id = :cid"
                ),
                {"score": float(row["avg_sentiment"]), "cid": row["customer_id"]},
            )
            sentiment_count += 1

        # Write nps_score
        nps_count = 0
        for _, row in nps_per_cust.iterrows():
            db.execute(
                text(
                    "UPDATE customer_features "
                    "SET nps_score = :nps "
                    "WHERE customer_id = :cid"
                ),
                {"nps": int(row["nps_score"]), "cid": row["customer_id"]},
            )
            nps_count += 1

        db.commit()
        self._logger.info(
            "customer_aggregates_updated",
            with_sentiment=sentiment_count,
            with_nps=nps_count,
        )
        return {"with_sentiment": sentiment_count, "with_nps": nps_count}

    # ──────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors = []

        rows = output.get("rows_affected", 0)
        input_doc_count = output.get("input_doc_count", 0)
        if rows == 0:
            errors.append("No rows written to sentiment_results")
        elif input_doc_count > 0 and rows < input_doc_count * 0.9:
            errors.append(f"Expected ~{input_doc_count} rows, got {rows}")

        summary = output.get("sentiment_summary", {})
        dist = summary.get("label_distribution", {})

        # All three labels must be present
        expected_labels = {"positive", "neutral", "negative"}
        missing = expected_labels - set(dist.keys())
        if missing:
            errors.append(f"Missing sentiment labels: {missing}")

        # No single label should dominate (>80%)
        total = sum(dist.values()) if dist else 0
        if total > 0:
            for label, count in dist.items():
                frac = count / total
                if frac > 0.80:
                    errors.append(
                        f"Label '{label}' dominates at {frac:.1%} (>80%)"
                    )

        # Average score should be reasonable
        avg = summary.get("avg_score", 0)
        if not (-0.5 <= avg <= 0.5):
            errors.append(
                f"avg_score {avg} outside expected range [-0.5, 0.5]"
            )

        # Should have updated a meaningful fraction of customers
        with_sent = summary.get("customers_with_sentiment", 0)
        total_customers = output.get("total_customers", 0)
        if total_customers > 0 and with_sent < total_customers * 0.5:
            errors.append(
                f"Only {with_sent} of {total_customers} customers got avg_sentiment (expected 50%+)"
            )

        return (len(errors) == 0, errors)


# ── Module-level helpers ─────────────────────────────────────────


def _score_to_label(score: float) -> str:
    if score < NEGATIVE_THRESHOLD:
        return "negative"
    elif score > POSITIVE_THRESHOLD:
        return "positive"
    return "neutral"
