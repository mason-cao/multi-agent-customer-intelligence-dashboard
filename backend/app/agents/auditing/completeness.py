"""Check source availability and derived-table coverage with cached counts."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.agents.auditing.definitions import (
    PER_CUSTOMER_TABLES, SENTIMENT_SOURCE_TABLES, STATIC_TABLE_MINIMUMS, VALID_SUMMARY_TYPES,
)
from app.agents.auditing.results import _make_result, unavailable_result


def _check_completeness(engine, now: str) -> list[dict]:
    results = []
    counts: dict[str, int | None] = {}
    tables = ("customers", *SENTIMENT_SOURCE_TABLES, *PER_CUSTOMER_TABLES,
              "sentiment_results", *STATIC_TABLE_MINIMUMS)
    with engine.connect() as connection:
        for table in tables:
            try:
                counts[table] = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            except SQLAlchemyError:
                counts[table] = None
                results.append(unavailable_result("completeness", f"table_{table}_exists", now))

        customer_count = counts["customers"] or 0
        source_count = sum(counts[source] or 0 for source in SENTIMENT_SOURCE_TABLES)
        minimums = {
            "customers": 1,
            **dict.fromkeys(PER_CUSTOMER_TABLES, max(1, int(customer_count * 0.9))),
            "sentiment_results": max(1, int(source_count * 0.9)),
            **STATIC_TABLE_MINIMUMS,
        }
        for table, minimum in minimums.items():
            count = counts[table]
            if count is None:
                continue
            passed = count >= minimum
            results.append(_make_result(
                check_category="completeness", check_name=f"table_{table}_populated",
                severity="info" if passed else "critical", passed=passed,
                audit_message=f"Table '{table}' has {count:,} rows (minimum {minimum:,})",
                now=now, entity_id=table, expected_value=f">={minimum}",
                actual_value=str(count), affected_rows=count,
            ))

        for table in PER_CUSTOMER_TABLES:
            if counts[table] is None or not customer_count:
                continue
            try:
                # Duplicate or orphan IDs must not hide missing customers.
                covered = connection.execute(text(
                    f"SELECT COUNT(DISTINCT c.customer_id) FROM customers c "
                    f"JOIN {table} derived ON c.customer_id = derived.customer_id"
                )).scalar_one()
                passed = covered >= customer_count * 0.95
                results.append(_make_result(
                    check_category="completeness", check_name=f"{table}_cover_customers",
                    severity="info" if passed else "warning", passed=passed,
                    audit_message=f"{table} covers {covered}/{customer_count} customers",
                    now=now, entity_id=table, expected_value=str(customer_count),
                    actual_value=str(covered), affected_rows=customer_count - covered,
                ))
            except SQLAlchemyError:
                results.append(unavailable_result("completeness", f"{table}_cover_customers", now))

        try:
            sections = set(connection.execute(text(
                "SELECT DISTINCT summary_type FROM executive_summaries"
            )).scalars())
            missing = VALID_SUMMARY_TYPES - sections
            results.append(_make_result(
                check_category="completeness", check_name="narrative_all_sections_present",
                severity="critical" if missing else "info", passed=not missing,
                audit_message=f"Missing narrative sections: {', '.join(sorted(missing))}"
                              if missing else "All narrative sections present",
                now=now, entity_id="executive_summaries",
                expected_value=str(len(VALID_SUMMARY_TYPES)), actual_value=str(len(sections)),
            ))
        except SQLAlchemyError:
            results.append(unavailable_result("completeness", "narrative_all_sections_present", now))
    return results
