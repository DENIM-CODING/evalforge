from deepeval import assert_test
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
)
from deepeval.test_case import LLMTestCase

from app.evaluator import load_dataset, create_test_cases


def test_dataset_loading():
    dataset = load_dataset()

    assert len(dataset) == 3


def test_evaluation_cases_creation():
    dataset = load_dataset()
    test_cases = create_test_cases(dataset)

    assert len(test_cases) == 3


def test_ai_response_quality():
    dataset = load_dataset()
    test_cases = create_test_cases(dataset)

    metrics = [
        FaithfulnessMetric(threshold=0.7),
        AnswerRelevancyMetric(threshold=0.7),
    ]

    results = evaluate(
        test_cases=test_cases,
        metrics=metrics,
    )

    assert len(results.test_results) == len(test_cases)