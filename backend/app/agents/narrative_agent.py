"""Generate executive summaries from aggregated workspace metrics."""

from typing import Any, Dict, List, Tuple
from app.agents.base import BaseAgent
from app.agents.narrative.definitions import NARRATIVE_VERSION, SECTIONS
from app.db.outputs import replace_output
from app.agents.narrative.metrics import _aggregate_metrics
from app.agents.narrative.insights import _generate_insights
from app.agents.narrative.sections import _assemble_sections


class NarrativeAgent(BaseAgent):

    @property
    def name(self) -> str:
        return "narrative"

    def run(self, db) -> Dict[str, Any]:
        engine = db.get_bind()

        stats = _aggregate_metrics(engine)

        if stats["total_customers"] == 0:
            return {
                "status": "failed",
                "rows_affected": 0,
                "tokens_used": 0,
                "model_used": None,
                "error": "No customer data available — upstream agents may have failed",
            }

        self._logger.info(
            "metrics_aggregated",
            total_customers=stats["total_customers"],
            segments=len(stats["segment_dist"]),
        )

        insights = _generate_insights(stats)
        self._logger.info("insights_generated", count=len(insights))

        summaries = _assemble_sections(stats, insights)
        self._logger.info("sections_assembled", count=len(summaries))

        replace_output(db, "executive_summaries", summaries)

        section_types = [s["summary_type"] for s in summaries]
        total_text_len = sum(len(s["summary_text"]) for s in summaries)

        self._logger.info(
            "narrative_complete",
            sections=len(summaries),
            total_text_chars=total_text_len,
        )

        return {
            "status": "completed",
            "rows_affected": len(summaries),
            "tokens_used": 0,
            "model_used": None,
            "narrative_summary": {
                "narrative_version": NARRATIVE_VERSION,
                "sections_generated": section_types,
                "total_sections": len(summaries),
                "total_text_chars": total_text_len,
                "insights_ranked": len(insights),
            },
        }

    def validate_output(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        rows = output.get("rows_affected", 0)
        if rows < len(SECTIONS):
            errors.append(
                f"Expected {len(SECTIONS)} sections, got {rows}"
            )

        summary = output.get("narrative_summary", {})
        sections = summary.get("sections_generated", [])

        missing = set(SECTIONS) - set(sections)
        if missing:
            errors.append(f"Missing sections: {missing}")

        total_chars = summary.get("total_text_chars", 0)
        if total_chars < len(SECTIONS) * 200:
            errors.append(
                f"Total text too short at {total_chars} chars "
                f"(expected {len(SECTIONS) * 200}+)"
            )

        insights_count = summary.get("insights_ranked", 0)
        if insights_count < 5:
            errors.append(
                f"Only {insights_count} insights generated, expected 5+"
            )

        return (len(errors) == 0, errors)
