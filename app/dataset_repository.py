import json

from pathlib import Path
from threading import RLock

from pydantic import TypeAdapter, ValidationError

from app.schemas import (
    CreateTestCaseRequest,
    TestCaseResponse,
)


DATASET_PATH = (
    Path(__file__).parent.parent
    / "datasets"
    / "golden_dataset.json"
)

DATASET_LOCK = RLock()

MAX_DATASET_SIZE_BYTES = 10 * 1024 * 1024
MAX_TEST_CASES = 500

DATASET_ADAPTER = TypeAdapter(list[TestCaseResponse])


class DatasetValidationError(ValueError):
    """Raised when the golden dataset is invalid."""


def validate_dataset(dataset):
    if not isinstance(dataset, list):
        raise DatasetValidationError(
            "Golden dataset must contain a JSON array."
        )

    if len(dataset) > MAX_TEST_CASES:
        raise DatasetValidationError(
            f"Dataset cannot contain more than {MAX_TEST_CASES} test cases."
        )

    try:
        validated = DATASET_ADAPTER.validate_python(dataset)
    except ValidationError as error:
        raise DatasetValidationError(
            f"Golden dataset contains invalid test cases: {error}"
        ) from error

    validated_dataset = [
        item.model_dump() for item in validated
    ]

    ids = [item["id"] for item in validated_dataset]

    if len(ids) != len(set(ids)):
        raise DatasetValidationError(
            "Golden dataset contains duplicate test case IDs."
        )

    return validated_dataset


def load_dataset():
    """Load and validate all test cases."""

    with DATASET_LOCK:
        if not DATASET_PATH.is_file():
            raise DatasetValidationError(
                "Golden dataset file does not exist."
            )

        if DATASET_PATH.stat().st_size > MAX_DATASET_SIZE_BYTES:
            raise DatasetValidationError(
                "Golden dataset exceeds the maximum allowed file size."
            )

        try:
            with open(DATASET_PATH, "r", encoding="utf-8") as file:
                dataset = json.load(file)

        except json.JSONDecodeError as error:
            raise DatasetValidationError(
                "Golden dataset contains invalid JSON."
            ) from error

        return validate_dataset(dataset)


def save_dataset(dataset):
    """Validate and persist dataset changes atomically."""

    validated_dataset = validate_dataset(dataset)

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)

    temp_path = DATASET_PATH.with_suffix(".tmp")

    with DATASET_LOCK:
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(
                validated_dataset,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temp_path.replace(DATASET_PATH)


def get_test_case(test_case_id: str):
    """Retrieve a test case by ID."""

    dataset = load_dataset()

    for test_case in dataset:
        if test_case["id"] == test_case_id:
            return test_case

    return None


def create_test_case(test_case_data: dict):
    """Create a test case with an automatically generated ID."""

    validated_data = CreateTestCaseRequest.model_validate(
        test_case_data
    ).model_dump()

    with DATASET_LOCK:
        dataset = load_dataset()

        if len(dataset) >= MAX_TEST_CASES:
            raise DatasetValidationError(
                f"Dataset cannot contain more than {MAX_TEST_CASES} test cases."
            )

        numeric_ids = []

        for item in dataset:
            existing_id = item["id"]

            if existing_id.startswith("TC"):
                try:
                    numeric_ids.append(int(existing_id[2:]))
                except ValueError:
                    continue

        next_id = max(numeric_ids, default=0) + 1

        test_case = {
            "id": f"TC{next_id:03d}",
            **validated_data,
        }

        dataset.append(test_case)
        save_dataset(dataset)

        return test_case


def update_test_case(test_case_id: str, updated_data: dict):
    """Replace an existing test case."""

    validated_data = CreateTestCaseRequest.model_validate(
        updated_data
    ).model_dump()

    with DATASET_LOCK:
        dataset = load_dataset()

        for index, test_case in enumerate(dataset):
            if test_case["id"] == test_case_id:
                updated_test_case = {
                    "id": test_case_id,
                    **validated_data,
                }

                dataset[index] = updated_test_case
                save_dataset(dataset)

                return updated_test_case

        return None


def delete_test_case(test_case_id: str):
    """Delete a test case."""

    with DATASET_LOCK:
        dataset = load_dataset()

        updated_dataset = [
            item for item in dataset
            if item["id"] != test_case_id
        ]

        if len(updated_dataset) == len(dataset):
            return False

        save_dataset(updated_dataset)

        return True