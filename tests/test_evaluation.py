from app.dataset_repository import load_dataset
from app.evaluator import create_test_cases


def test_dataset_loading():
    dataset = load_dataset()

    assert len(dataset) == 4
    assert isinstance(dataset, list)


def test_evaluation_cases_creation():
    dataset = load_dataset()
    test_cases = create_test_cases(dataset)

    assert len(test_cases) == 4

    for test_case in test_cases:
        assert test_case.input
        assert test_case.actual_output
        assert test_case.expected_output
        assert test_case.context
        assert test_case.retrieval_context