"""Regression tests for atomic outputs and shared pipeline failure semantics."""

from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.agents.base import BaseAgent
from app.db.database import Base
from app.db.outputs import replace_output
from app.services.pipeline import AgentSpec, execute_pipeline


@pytest.fixture
def pipeline_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'pipeline.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.mark.parametrize("as_frame", [False, True])
def test_failed_replacement_preserves_previous_output_and_records_failure(pipeline_engine, as_frame):
    with pipeline_engine.begin() as connection:
        connection.execute(text("INSERT INTO workspace_context (key, value) VALUES ('old', 'retained')"))

    class BrokenOutputAgent(BaseAgent):
        name = "broken_output"

        def run(self, db):
            rows = [{"key": "duplicate", "value": "one"}, {"key": "duplicate", "value": "two"}]
            replace_output(db, "workspace_context", pd.DataFrame(rows) if as_frame else rows)
            return {"status": "completed"}

        def validate_output(self, output):
            return True, []

    with sessionmaker(bind=pipeline_engine)() as db:
        result = BrokenOutputAgent().execute(db)
    assert result["_status"] == "failed"
    with pipeline_engine.connect() as connection:
        assert connection.execute(text("SELECT key, value FROM workspace_context")).all() == [("old", "retained")]
        assert connection.execute(text("SELECT status FROM agent_runs")).scalar_one() == "failed"


def test_explicit_agent_failure_is_not_reclassified_as_partial(pipeline_engine):
    class FailedAgent(BaseAgent):
        name = "explicit_failure"

        def run(self, db):
            replace_output(db, "workspace_context", [{"key": "new", "value": "discard"}])
            return {"status": "failed", "error": "missing upstream input"}

        def validate_output(self, output):
            return True, []

    with sessionmaker(bind=pipeline_engine)() as db:
        result = FailedAgent().execute(db)
    assert result["_status"] == "failed"
    with pipeline_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM workspace_context")).scalar_one() == 0


def test_pipeline_stops_before_downstream_agents_and_groups_run_ids(pipeline_engine, monkeypatch):
    seen = []

    class GoodAgent(BaseAgent):
        name = "good"

        def run(self, db):
            seen.append(self.name)
            return {"status": "completed", "rows_affected": 1}

        def validate_output(self, output):
            return True, []

    class FailedAgent(GoodAgent):
        name = "failed"

        def run(self, db):
            seen.append(self.name)
            return {"status": "failed", "error": "stopped"}

    monkeypatch.setattr("app.services.pipeline.importlib.import_module", lambda _: SimpleNamespace(Good=GoodAgent, Failed=FailedAgent))
    specs = (
        AgentSpec("Good", "test", "Good", True, 8),
        AgentSpec("Failed", "test", "Failed", True, 9),
        AgentSpec("Never", "test", "Good", True, 10),
    )
    outcomes = list(execute_pipeline(sessionmaker(bind=pipeline_engine), specs=specs))
    assert seen == ["good", "failed"]
    assert [outcome.action for outcome in outcomes] == ["ok", "fatal"]
    with pipeline_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(DISTINCT run_id) FROM agent_runs")).scalar_one() == 1


def test_optional_import_failure_allows_later_agent_to_run(pipeline_engine):
    specs = (
        AgentSpec("Optional", "module_that_does_not_exist", "Missing", False, 13),
        AgentSpec("QueryAgent", "app.agents.query_agent", "QueryAgent", False, 14),
    )
    outcomes = list(execute_pipeline(sessionmaker(bind=pipeline_engine), specs=specs))
    assert len(outcomes) == 2
    assert outcomes[0].action == "warn"


def test_generated_dataset_runs_every_agent_and_keeps_one_run_id(pipeline_engine):
    from app.services.data_generation.dataset import generate_dataset
    from app.services.pipeline import PIPELINE

    counts = generate_dataset(pipeline_engine, customer_count=100, churn_rate=0.2, seed=42)
    assert counts["customers"] == 100
    outcomes = list(execute_pipeline(sessionmaker(bind=pipeline_engine)))
    assert len(outcomes) == len(PIPELINE)
    assert all(outcome.output["_status"] in ("completed", "partial") for outcome in outcomes), [
        (outcome.spec.label, outcome.output) for outcome in outcomes
    ]
    with pipeline_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(DISTINCT run_id) FROM agent_runs")).scalar_one() == 1
        for table in ("customer_features", "customer_segments", "churn_predictions", "recommendations"):
            assert connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 100
        assert connection.execute(text("SELECT COUNT(*) FROM executive_summaries")).scalar_one() == 7
        assert connection.execute(text("SELECT COUNT(*) FROM query_results WHERE query_status = 'error'")).scalar_one() == 0


def test_source_generation_failure_rolls_back_prior_stages(pipeline_engine):
    from app.services.data_generation.dataset import generate_dataset

    def interrupt(index, name):
        if index == 3:
            raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError, match="interrupted"):
        generate_dataset(pipeline_engine, customer_count=20, on_stage=interrupt)
    with pipeline_engine.connect() as connection:
        for table in ("customers", "subscriptions"):
            assert connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() == 0


def test_agent_history_shows_latest_failure_instead_of_older_success(pipeline_engine):
    from app.models.agent_run import AgentRun
    from app.routes.agents import get_agents_summary

    with sessionmaker(bind=pipeline_engine)() as db:
        db.add_all([
            AgentRun(id="old", agent_name="behavior", run_id="run1", status="completed",
                     started_at="2026-01-01T00:00:00", completed_at="2026-01-01T00:01:00"),
            AgentRun(id="new", agent_name="behavior", run_id="run2", status="failed",
                     started_at="2026-01-02T00:00:00", completed_at="2026-01-02T00:01:00"),
        ])
        db.commit()
        summary = get_agents_summary(db)
    assert len(summary["runs"]) == 1
    assert summary["runs"][0]["id"] == "new"
    assert summary["runs"][0]["status"] == "failed"
    assert summary["audit"]["total_checks"] == 0
