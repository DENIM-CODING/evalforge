import json
import pytest

from app import dataset_repository


@pytest.fixture
def sample_dataset(tmp_path, monkeypatch):
    """
    Create an isolated temporary dataset for each test.
    This prevents tests from modifying the actual golden_dataset.json.
    """

    dataset_path = tmp_path / "golden_dataset.json"

    initial_data = [
        {
            "id": "TC001",
            "input": "What is the return policy?",
            "actual_output": "90 days",
            "expected_output": "30 days",
            "context": ["Customers can return products within 30 days."]
        },
        {
            "id": "TC002",
            "input": "How can I contact support?",
            "actual_output": "Email support",
            "expected_output": "Email support",
            "context": ["Customers can contact support through email."]
        },
        {
            "id": "TC003",
            "input": "What payment methods are accepted?",
            "actual_output": "Credit cards",
            "expected_output": "Credit cards",
            "context": ["We accept credit cards."]
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

    return dataset_path


def test_load_dataset(sample_dataset):

    dataset = dataset_repository.load_dataset()

    assert len(dataset) == 3
    assert dataset[0]["id"] == "TC001"


def test_get_existing_test_case(sample_dataset):

    test_case = dataset_repository.get_test_case("TC001")

    assert test_case is not None
    assert test_case["id"] == "TC001"
    assert test_case["expected_output"] == "30 days"


def test_get_nonexistent_test_case(sample_dataset):

    test_case = dataset_repository.get_test_case("TC999")

    assert test_case is None


def test_create_test_case(sample_dataset):

    new_test_case = {
        "input": "What is the warranty period?",
        "actual_output": "2 years",
        "expected_output": "1 year",
        "context": ["Products come with a 1-year warranty."]
    }

    created = dataset_repository.create_test_case(new_test_case)

    assert created["id"] == "TC004"
    assert created["input"] == "What is the warranty period?"

    dataset = dataset_repository.load_dataset()

    assert len(dataset) == 4
    assert dataset[-1]["id"] == "TC004"


def test_update_existing_test_case(sample_dataset):

    updated_data = {
        "input": "What is the return policy?",
        "actual_output": "30 days",
        "expected_output": "30 days",
        "context": ["Customers can return products within 30 days."]
    }

    updated = dataset_repository.update_test_case(
        "TC001",
        updated_data
    )

    assert updated is not None
    assert updated["actual_output"] == "30 days"

    saved_case = dataset_repository.get_test_case("TC001")

    assert saved_case["actual_output"] == "30 days"


def test_update_nonexistent_test_case(sample_dataset):

    updated = dataset_repository.update_test_case(
        "TC999",
        {
            "input": "Some question",
            "actual_output": "Some answer",
            "expected_output": "Expected answer",
            "context": ["Some context"]
        }
    )

    assert updated is None


def test_delete_existing_test_case(sample_dataset):

    deleted = dataset_repository.delete_test_case("TC001")

    assert deleted is True

    dataset = dataset_repository.load_dataset()

    assert len(dataset) == 2
    assert all(item["id"] != "TC001" for item in dataset)


def test_delete_nonexistent_test_case(sample_dataset):

    deleted = dataset_repository.delete_test_case("TC999")

    assert deleted is False