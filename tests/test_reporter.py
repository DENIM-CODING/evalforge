import json
from types import SimpleNamespace

import app.reporter as reporter
from app.reporter import generate_report


def create_mock_evaluation_result():
    """Create mock DeepEval results for testing."""

    test_results = [
        SimpleNamespace(
            input="What is the return policy?",
            actual_output="Products can be returned within 90 days.",
            expected_output="Products can be returned within 30 days.",
            success=False,
            metrics_data=[
                SimpleNamespace(
                    name="Faithfulness",
                    score=0.0,
                    threshold=0.7,
                    success=False,
                    reason="Incorrect return period.",
                ),
                SimpleNamespace(
                    name="Answer Relevancy",
                    score=1.0,
                    threshold=0.7,
                    success=True,
                    reason="Answer is relevant.",
                ),
            ],
        ),
        SimpleNamespace(
            input="How can I contact support?",
            actual_output="Contact support through email.",
            expected_output="Contact support through email.",
            success=True,
            metrics_data=[
                SimpleNamespace(
                    name="Faithfulness",
                    score=1.0,
                    threshold=0.7,
                    success=True,
                    reason="Answer is faithful.",
                ),
                SimpleNamespace(
                    name="Answer Relevancy",
                    score=1.0,
                    threshold=0.7,
                    success=True,
                    reason="Answer is relevant.",
                ),
            ],
        ),
    ]

    return SimpleNamespace(test_results=test_results)


def create_mock_dataset():
    return [
        {
            "id": "TC001",
            "input": "What is the return policy?",
            "actual_output": "Products can be returned within 90 days.",
            "expected_output": "Products can be returned within 30 days.",
        },
        {
            "id": "TC002",
            "input": "How can I contact support?",
            "actual_output": "Contact support through email.",
            "expected_output": "Contact support through email.",
        },
    ]


def test_report_generation(tmp_path, monkeypatch):
    monkeypatch.setattr(reporter, "REPORTS_DIR", tmp_path)

    result = generate_report(
        create_mock_evaluation_result(),
        create_mock_dataset(),
        provider="openrouter",
    )

    assert result["project"] == "EvalForge"
    assert result["provider"] == "openrouter"
    assert "generated_at" in result
    assert "report_path" in result

    assert len(list(tmp_path.glob("*.json"))) == 1


def test_report_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(reporter, "REPORTS_DIR", tmp_path)

    result = generate_report(
        create_mock_evaluation_result(),
        create_mock_dataset(),
        provider="openrouter",
    )

    summary = result["summary"]

    assert summary["total_tests"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["pass_rate"] == 50.0


def test_metric_aggregation(tmp_path, monkeypatch):
    monkeypatch.setattr(reporter, "REPORTS_DIR", tmp_path)

    result = generate_report(
        create_mock_evaluation_result(),
        create_mock_dataset(),
        provider="openrouter",
    )

    metrics = result["metrics"]

    faithfulness = metrics["Faithfulness"]

    assert faithfulness["average_score"] == 0.5
    assert faithfulness["total"] == 2
    assert faithfulness["passed"] == 1
    assert faithfulness["failed"] == 1
    assert faithfulness["pass_rate"] == 50.0

    relevancy = metrics["Answer Relevancy"]

    assert relevancy["average_score"] == 1.0
    assert relevancy["passed"] == 2
    assert relevancy["failed"] == 0
    assert relevancy["pass_rate"] == 100.0


def test_report_contains_test_case_details(tmp_path, monkeypatch):
    monkeypatch.setattr(reporter, "REPORTS_DIR", tmp_path)

    result = generate_report(
        create_mock_evaluation_result(),
        create_mock_dataset(),
        provider="openrouter",
    )

    test_cases = result["test_cases"]

    assert len(test_cases) == 2

    assert test_cases[0]["id"] == "TC001"
    assert test_cases[0]["passed"] is False

    assert len(test_cases[0]["metrics"]) == 2
    assert test_cases[0]["metrics"][0]["name"] == "Faithfulness"


def test_report_is_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(reporter, "REPORTS_DIR", tmp_path)

    result = generate_report(
        create_mock_evaluation_result(),
        create_mock_dataset(),
        provider="openrouter",
    )

    report_path = result["report_path"]

    with open(report_path, "r", encoding="utf-8") as file:
        saved_report = json.load(file)

    assert saved_report["project"] == "EvalForge"
    assert saved_report["provider"] == "openrouter"
    assert saved_report["summary"]["total_tests"] == 2
    assert len(saved_report["test_cases"]) == 2