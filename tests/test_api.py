import json
import pytest

from fastapi.testclient import TestClient
from app.api import app
from app import dataset_repository


@pytest.fixture
def client(tmp_path, monkeypatch):

    dataset_path = tmp_path / "golden_dataset.json"

    initial_data = [
        {
            "id": "TC001",
            "input": "What is the return policy?",
            "actual_output": "90 days",
            "expected_output": "30 days",
            "context": [
                "Customers can return products within 30 days."
            ]
        },
        {
            "id": "TC002",
            "input": "How can I contact support?",
            "actual_output": "Email support",
            "expected_output": "Email support",
            "context": [
                "Customers can contact support through email."
            ]
        }
    ]

    dataset_path.write_text(
        json.dumps(initial_data),
        encoding="utf-8"
    )

    monkeypatch.setattr(
        dataset_repository,
        "DATASET_PATH",
        dataset_path
    )

    return TestClient(app)


def test_health_check(client):

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "EvalForge"


def test_get_all_test_cases(client):

    response = client.get("/dataset")

    assert response.status_code == 200

    data = response.json()

    assert data["total_test_cases"] == 2
    assert len(data["test_cases"]) == 2


def test_get_single_test_case(client):

    response = client.get("/dataset/TC001")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "TC001"
    assert data["expected_output"] == "30 days"


def test_get_nonexistent_test_case(client):

    response = client.get("/dataset/TC999")

    assert response.status_code == 404


def test_create_test_case(client):

    payload = {
        "input": "What is the warranty period?",
        "actual_output": "2 years",
        "expected_output": "1 year",
        "context": [
            "Products come with a 1-year warranty."
        ]
    }

    response = client.post("/dataset", json=payload)

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == "TC003"
    assert data["input"] == payload["input"]


def test_create_invalid_test_case(client):

    payload = {
        "input": "",
        "actual_output": "Some answer",
        "expected_output": "Expected answer",
        "context": []
    }

    response = client.post("/dataset", json=payload)

    assert response.status_code == 422


def test_update_test_case(client):

    payload = {
        "input": "What is the return policy?",
        "actual_output": "30 days",
        "expected_output": "30 days",
        "context": [
            "Customers can return products within 30 days."
        ]
    }

    response = client.put(
        "/dataset/TC001",
        json=payload
    )

    assert response.status_code == 200

    data = response.json()

    assert data["actual_output"] == "30 days"


def test_update_nonexistent_test_case(client):

    payload = {
        "input": "Some question",
        "actual_output": "Some answer",
        "expected_output": "Expected answer",
        "context": ["Some context"]
    }

    response = client.put(
        "/dataset/TC999",
        json=payload
    )

    assert response.status_code == 404


def test_delete_test_case(client):

    response = client.delete("/dataset/TC001")

    assert response.status_code == 200

    # Verify that the test case was actually deleted.
    get_response = client.get("/dataset/TC001")

    assert get_response.status_code == 404


def test_delete_nonexistent_test_case(client):

    response = client.delete("/dataset/TC999")

    assert response.status_code == 404