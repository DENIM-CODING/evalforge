from unittest.mock import patch

from app import evaluator


def test_create_test_cases():

    dataset = [
        {
            "id": "TC001",
            "input": "What is the return policy?",
            "actual_output": "90 days",
            "expected_output": "30 days",
            "context": [
                "Customers can return products within 30 days.",
                "Products must be unused."
            ]
        }
    ]

    test_cases = evaluator.create_test_cases(dataset)

    assert len(test_cases) == 1

    test_case = test_cases[0]

    assert test_case.input == "What is the return policy?"
    assert test_case.actual_output == "90 days"
    assert test_case.expected_output == "30 days"

    assert test_case.context == dataset[0]["context"]
    assert test_case.retrieval_context == dataset[0]["context"]


def test_create_multiple_test_cases():

    dataset = [
        {
            "id": "TC001",
            "input": "Question 1",
            "actual_output": "Answer 1",
            "expected_output": "Expected 1",
            "context": ["Context 1"]
        },
        {
            "id": "TC002",
            "input": "Question 2",
            "actual_output": "Answer 2",
            "expected_output": "Expected 2",
            "context": ["Context 2"]
        }
    ]

    test_cases = evaluator.create_test_cases(dataset)

    assert len(test_cases) == 2
    assert test_cases[0].input == "Question 1"
    assert test_cases[1].input == "Question 2"


def test_is_rate_limit_error():

    assert evaluator.is_rate_limit_error(
        Exception("429 Too Many Requests")
    )

    assert evaluator.is_rate_limit_error(
        Exception("free-models-per-day quota exceeded")
    )

    assert evaluator.is_rate_limit_error(
        Exception("RateLimitError")
    )

    assert not evaluator.is_rate_limit_error(
        Exception("Invalid API key")
    )

    assert not evaluator.is_rate_limit_error(
        Exception("Connection timeout")
    )


@patch("app.evaluator.evaluate")
@patch("app.evaluator.build_metrics")
def test_run_with_openrouter(mock_build_metrics, mock_evaluate):

    test_cases = ["mock_test_case"]
    mock_metrics = ["mock_metric"]

    mock_build_metrics.return_value = mock_metrics
    mock_evaluate.return_value = "mock_evaluation_result"

    result = evaluator.run_with_openrouter(test_cases)

    mock_build_metrics.assert_called_once_with()

    mock_evaluate.assert_called_once_with(
        test_cases=test_cases,
        metrics=mock_metrics
    )

    assert result == "mock_evaluation_result"