from datetime import datetime, timezone

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.evaluation_repository import (
    create_evaluation,
    update_evaluation_status,
    complete_evaluation,
    get_evaluation,
    get_evaluation_history,
    get_active_evaluation,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def test_create_evaluation(db_session):
    evaluation = create_evaluation(
        db_session,
        "test-evaluation-001",
    )

    assert evaluation.id == "test-evaluation-001"
    assert evaluation.status == "queued"


def test_update_evaluation_status(db_session):
    create_evaluation(db_session, "test-evaluation-002")

    evaluation = update_evaluation_status(
        db_session,
        "test-evaluation-002",
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    assert evaluation.status == "running"
    assert evaluation.started_at is not None


def test_get_active_evaluation(db_session):
    create_evaluation(db_session, "test-evaluation-003")

    evaluation = get_active_evaluation(db_session)

    assert evaluation is not None
    assert evaluation.id == "test-evaluation-003"


def test_complete_evaluation(db_session):
    evaluation_id = "test-evaluation-004"

    create_evaluation(db_session, evaluation_id)

    result = {
        "provider": "openrouter",
        "report": {
            "summary": {
                "total_tests": 4,
                "passed": 3,
                "failed": 1,
                "pass_rate": 75.0,
            },
            "metrics": {
                "Faithfulness": {
                    "average_score": 0.85,
                    "pass_rate": 75.0,
                    "total": 4,
                    "passed": 3,
                    "failed": 1,
                },
                "Answer Relevancy": {
                    "average_score": 0.90,
                    "pass_rate": 100.0,
                    "total": 4,
                    "passed": 4,
                    "failed": 0,
                },
            },
            "report_path": "reports/test-report.json",
        },
    }

    evaluation = complete_evaluation(
        db_session,
        evaluation_id,
        result,
    )

    assert evaluation.status == "completed"
    assert evaluation.provider == "openrouter"
    assert evaluation.total_tests == 4
    assert evaluation.passed_tests == 3
    assert evaluation.failed_tests == 1
    assert evaluation.pass_rate == 75.0
    assert evaluation.report_path == "reports/test-report.json"

    assert len(evaluation.metrics) == 2


def test_get_evaluation_history(db_session):
    create_evaluation(db_session, "test-evaluation-005")
    create_evaluation(db_session, "test-evaluation-006")

    history = get_evaluation_history(db_session)

    assert len(history) == 2


def test_get_nonexistent_evaluation(db_session):
    evaluation = get_evaluation(
        db_session,
        "does-not-exist",
    )

    assert evaluation is None