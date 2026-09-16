"""Sentiment pipeline stage."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import pandas as pd
from sqlalchemy import text
from app.agents.base import BaseAgent
from app.db.outputs import replace_output
from app.agents.sentiment.definitions import TOPIC_KEYWORDS, EMOTION_KEYWORDS, POSITIVE_WORDS, NEGATIVE_WORDS, CATEGORY_SCORES, PRIORITY_MODIFIERS, RESOLUTION_MODIFIERS, NEGATIVE_THRESHOLD, POSITIVE_THRESHOLD


class SentimentAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "sentiment"

    # Main run

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

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

        fb_results = self._score_feedback(feedback)
        tk_results = self._score_tickets(tickets)

        all_results = pd.concat([fb_results, tk_results], ignore_index=True)
        all_results["computed_at"] = datetime.now(timezone.utc).isoformat()

        self._logger.info("writing_sentiment_results", rows=len(all_results))
        replace_output(db, "sentiment_results", all_results)

        customers_updated = self._update_customer_aggregates(
            all_results, feedback, db, engine,
        )

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

        # Stay in the output transaction: large SQLite writes can spill the
        # page cache and hold an exclusive lock until the agent commits.
        total_customers = db.execute(
            text("SELECT COUNT(*) FROM customers")
        ).scalar_one()

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

    # Feedback scoring — rating-based with keyword adjustment

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

    # Ticket scoring — category + priority + resolution + keywords

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

    # Text analysis helpers

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

    # Customer-level aggregation

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

        # Write avg_sentiment and nps_score as batched executemany updates —
        # one statement per table instead of one round-trip per customer.
        sentiment_params = [
            {"score": float(row["avg_sentiment"]), "cid": row["customer_id"]}
            for _, row in cust_sentiment.iterrows()
        ]
        sentiment_count = len(sentiment_params)
        if sentiment_params:
            db.execute(
                text(
                    "UPDATE customer_features "
                    "SET avg_sentiment = :score "
                    "WHERE customer_id = :cid"
                ),
                sentiment_params,
            )

        nps_params = [
            {"nps": int(row["nps_score"]), "cid": row["customer_id"]}
            for _, row in nps_per_cust.iterrows()
        ]
        nps_count = len(nps_params)
        if nps_params:
            db.execute(
                text(
                    "UPDATE customer_features "
                    "SET nps_score = :nps "
                    "WHERE customer_id = :cid"
                ),
                nps_params,
            )

        self._logger.info(
            "customer_aggregates_updated",
            with_sentiment=sentiment_count,
            with_nps=nps_count,
        )
        return {"with_sentiment": sentiment_count, "with_nps": nps_count}

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

def _score_to_label(score: float) -> str:
    if score < NEGATIVE_THRESHOLD:
        return "negative"
    elif score > POSITIVE_THRESHOLD:
        return "positive"
    return "neutral"
