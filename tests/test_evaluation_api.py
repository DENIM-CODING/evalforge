import json

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Evaluation
import app.api as api


@pytest.fixture
def client(monkeypatch, tmp_path):

    # Create an isolated in-memory database.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    # Make the API use our test database instead of Neon.
    monkeypatch.setattr(
        api,
        "get_engine",
        lambda: engine,
    )

    # Keep test reports isolated.
    monkeypatch.setattr(
        api,
        "REPORTS_DIR",
        tmp_path,
    )

    with TestClient(api.app) as test_client:
        yield test_client

    engine.dispose()


def create_mock_evaluation(tmp_path):
    """Return a realistic evaluation result without calling an LLM."""

    report = {
        "project": "EvalForge",
        "provider": "openrouter",
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
        "test_cases": [],
    }

    report_path = tmp_path / "evaluation_test.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file)

    report["report_path"] = str(report_path)

    return {
        "provider": "openrouter",
        "report": report,
    }


def test_start_evaluation(client, monkeypatch, tmp_path):

    monkeypatch.setattr(
        api,
        "run_evaluation",
        lambda metric_config=None: create_mock_evaluation(tmp_path),
    )

    response = client.post("/evaluations")

    assert response.status_code == 202

    data = response.json()

    assert data["status"] == "queued"
    assert data["evaluation_id"]

    # Background task should have completed by the time
    # TestClient returns the response.
    evaluation_response = client.get(
        f"/evaluations/{data['evaluation_id']}"
    )

    assert evaluation_response.status_code == 200

    evaluation = evaluation_response.json()

    assert evaluation["status"] == "completed"
    assert evaluation["provider"] == "openrouter"
    assert evaluation["total_tests"] == 4
    assert evaluation["passed_tests"] == 3
    assert evaluation["failed_tests"] == 1
    assert evaluation["pass_rate"] == 75.0


def test_list_evaluations(client, monkeypatch, tmp_path):

    monkeypatch.setattr(
        api,
        "run_evaluation",
        lambda metric_config=None: create_mock_evaluation(tmp_path)
    )

    client.post("/evaluations")

    response = client.get("/evaluations")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["evaluations"]) == 1
    assert data["evaluations"][0]["status"] == "completed"


def test_get_evaluation_details(client, monkeypatch, tmp_path):

    monkeypatch.setattr(
        api,
        "run_evaluation",
        lambda metric_config=None: create_mock_evaluation(tmp_path),
    )

    start_response = client.post("/evaluations")

    evaluation_id = start_response.json()["evaluation_id"]

    response = client.get(
        f"/evaluations/{evaluation_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == evaluation_id
    assert data["status"] == "completed"

    assert len(data["metrics"]) == 2
    assert data["metrics"][0]["name"] in (
        "Faithfulness",
        "Answer Relevancy",
    )

    assert data["report"] is not None
    assert data["report"]["project"] == "EvalForge"


def test_get_nonexistent_evaluation(client):

    response = client.get(
        "/evaluations/nonexistent-id"
    )

    assert response.status_code == 404


def test_prevent_duplicate_active_evaluations(client):

    # Insert an evaluation that is already running.
    with Session(api.get_engine()) as session:
        session.add(
            Evaluation(
                id="existing-evaluation",
                status="running",
            )
        )
        session.commit()

    response = client.post("/evaluations")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "An evaluation is already in progress."
    )


def test_evaluation_history_pagination(client, monkeypatch, tmp_path):

    monkeypatch.setattr(
        api,
        "run_evaluation",
        lambda metric_config=None: create_mock_evaluation(tmp_path),
    )

    client.post("/evaluations")
    client.post("/evaluations")

    response = client.get("/evaluations?limit=1&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["evaluations"]) == 1