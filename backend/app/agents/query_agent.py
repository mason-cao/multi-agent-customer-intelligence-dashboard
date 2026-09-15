"""Run approved analytics queries and record their outcomes."""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import pandas as pd
from app.agents.base import BaseAgent
from app.db.outputs import replace_output
from app.utils.privacy import text_log_metadata
from app.agents.query.intents import INTENT_META, UNSUPPORTED_FOLLOWUPS, SUPPORTED_DESCRIPTIONS, extract_params, _sanitize_params, classify_intent
from app.agents.query.handlers import INTENT_HANDLERS


QUERY_VERSION = "intent-v2"

QUERY_RESULT_COLUMNS = [
    "query_id", "original_question", "matched_intent", "query_status",
    "answer_text", "structured_result", "source_tables", "row_count",
    "execution_ms", "query_version", "executed_at",
]

class QueryAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "query"

    def run(self, db) -> Dict[str, Any]:
        """
        Run a batch of demo questions to populate query_results.

        This satisfies the BaseAgent interface. For single-question use,
        call answer_question() directly.
        """
        engine = db.get_bind()

        demo_questions = [
            "Which segment has the highest churn risk?",
            "Show the top 10 highest-risk customers.",
            "What actions are most common?",
            "How does sentiment vary by segment?",
            "Give me a segment overview.",
            "What should we prioritize this week?",
            "What are the most important executive insights right now?",
            "Are there any audit warnings?",
            "What actions are recommended for high-risk negative-sentiment customers?",
            "Give me an overall customer intelligence summary.",
            "What is the meaning of life?",
        ]

        results = []
        for q in demo_questions:
            result = self.answer_question(q, engine)
            results.append(result)

        # Write all results to query_results table (DELETE + INSERT preserves ORM
        # constraints). Only persisted columns are written — response-only fields
        # (result_kind, suggested_followups) are dropped here.
        df = pd.DataFrame(results)[QUERY_RESULT_COLUMNS]
        replace_output(db, "query_results", df)
        self._logger.info("query_results_written", rows=len(df))

        success = sum(1 for r in results if r["query_status"] == "success")
        unsupported = sum(1 for r in results if r["query_status"] == "unsupported")

        return {
            "status": "completed",
            "rows_affected": len(results),
            "tokens_used": 0,
            "model_used": None,
            "query_summary": {
                "query_version": QUERY_VERSION,
                "total_queries": len(results),
                "successful": success,
                "unsupported": unsupported,
                "supported_intents": len(INTENT_HANDLERS),
            },
        }

    def answer_question(self, question: str, engine, llm_client=None) -> Dict[str, Any]:
        """Route to a fixed handler; providers may choose only approved intents and parameters."""
        started = time.monotonic()
        intent, _ = classify_intent(question)
        params = extract_params(question, intent) if intent != "unsupported" else {}
        if intent == "unsupported" and llm_client is not None and not llm_client.is_mock:
            routed = llm_client.route_query(question, list(INTENT_HANDLERS))
            if routed and routed.get("intent") in INTENT_HANDLERS:
                intent = routed["intent"]
                params = _sanitize_params(routed.get("params"))

        meta = INTENT_META.get(intent, {})
        response = {
            "query_id": str(uuid.uuid4()),
            "original_question": question,
            "matched_intent": intent,
            "query_status": "unsupported" if intent == "unsupported" else "error",
            "answer_text": "We couldn't complete that query safely. Try a suggested question or refresh the workspace.",
            "structured_result": None,
            "source_tables": None,
            "row_count": None,
            "query_version": QUERY_VERSION,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "result_kind": "text",
            "suggested_followups": list(meta.get("followups", UNSUPPORTED_FOLLOWUPS)),
        }
        if intent == "unsupported":
            supported = "\n".join(f"  - {description}" for description in SUPPORTED_DESCRIPTIONS)
            response.update(
                answer_text="I can't answer that one yet. I currently understand these question types:\n"
                            f"{supported}\n\nTry one of the suggested questions below.",
                structured_result=json.dumps({"supported_intents": SUPPORTED_DESCRIPTIONS}),
            )
        else:
            try:
                result = INTENT_HANDLERS[intent](engine, params)
                response.update(
                    query_status="success",
                    answer_text=result["answer_text"],
                    structured_result=json.dumps(result["structured_result"], default=str),
                    source_tables=result["source_tables"],
                    row_count=result.get("row_count"),
                    result_kind=result.get("result_kind", meta.get("result_kind", "table")),
                )
                self._logger.info(
                    "query_answered", intent=intent, **text_log_metadata(question),
                    row_count=result.get("row_count"),
                )
            except Exception as exc:
                self._logger.error("query_failed", intent=intent, error_type=type(exc).__name__)
        response["execution_ms"] = int((time.monotonic() - started) * 1000)
        return response

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        if rows == 0:
            errors.append("No query results were produced")

        summary = output.get("query_summary", {})
        successful = summary.get("successful", 0)
        if successful == 0:
            errors.append("No queries resolved successfully")

        total = summary.get("total_queries", 0)
        if total > 0 and successful / total < 0.5:
            errors.append(
                f"Only {successful}/{total} queries successful, expected >50%"
            )

        return (len(errors) == 0, errors)
