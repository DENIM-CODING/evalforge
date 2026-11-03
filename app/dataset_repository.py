import json

from pathlib import Path
from threading import RLock


DATASET_PATH = (
    Path(__file__).parent.parent
    / "datasets"
    / "golden_dataset.json"
)

# Protect dataset operations from simultaneous modifications.
DATASET_LOCK = RLock()


def load_dataset():
    """Load all test cases from the JSON dataset."""

    with DATASET_LOCK:
        with open(DATASET_PATH, "r", encoding="utf-8") as file:
            return json.load(file)


def save_dataset(dataset):
    """Persist dataset changes using an atomic file replacement."""

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)

    temp_path = DATASET_PATH.with_suffix(".tmp")

    with DATASET_LOCK:

        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(
                dataset,
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
    """Create a new test case with an automatically generated ID."""

    with DATASET_LOCK:

        dataset = load_dataset()

        existing_ids = {
            item["id"] for item in dataset
        }

        numeric_ids = []

        for existing_id in existing_ids:
            if existing_id.startswith("TC"):
                try:
                    numeric_ids.append(int(existing_id[2:]))
                except ValueError:
                    continue

        next_id = max(numeric_ids, default=0) + 1

        test_case = {
            "id": f"TC{next_id:03d}",
            **test_case_data,
        }

        dataset.append(test_case)

        save_dataset(dataset)

        return test_case


def update_test_case(test_case_id: str, updated_data: dict):
    """Replace an existing test case."""

    with DATASET_LOCK:

        dataset = load_dataset()

        for index, test_case in enumerate(dataset):

            if test_case["id"] == test_case_id:

                updated_test_case = {
                    "id": test_case_id,
                    **updated_data,
                }

                dataset[index] = updated_test_case

                save_dataset(dataset)

                return updated_test_case

        return None


def delete_test_case(test_case_id: str):
    """Delete a test case by ID."""

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