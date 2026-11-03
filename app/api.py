import json
import logging

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, BackgroundTasks, HTTPException

from app.schemas import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest,
    TestCaseResponse,
)

from app.dataset_repository import (
    load_dataset,
    get_test_case,
    create_test_case,
    update_test_case,
    delete_test_case,
)

from app.evaluator import run_evaluation


# --------------------------------------------------
# Configuration
# --------------------------------------------------

app = FastAPI(
    title="EvalForge API",
    description="An LLM evaluation framework for testing AI application quality.",
    version="1.0.0",
)

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"

logger = logging.getLogger(__name__)

@app.get("/")
def root():
    return {
        "message": "Welcome to EvalForge API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# --------------------------------------------------
# In-memory evaluation tracking
# --------------------------------------------------

evaluations = {}
evaluation_lock = Lock()


# --------------------------------------------------
# Background evaluation worker
# --------------------------------------------------

def execute_evaluation(evaluation_id: str):

    try:
        with evaluation_lock:
            evaluations[evaluation_id]["status"] = "running"
            evaluations[evaluation_id]["started_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

        logger.info("Starting evaluation: %s", evaluation_id)

        result = run_evaluation()

        with evaluation_lock:
            evaluations[evaluation_id].update({
                "status": "completed",
                "provider": result["provider"],
                "report": result["report"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })

        logger.info("Evaluation completed: %s", evaluation_id)

    except Exception as error:

        logger.exception(
            "Evaluation failed: %s",
            evaluation_id,
        )

        with evaluation_lock:
            evaluations[evaluation_id].update({
                "status": "failed",
                "error": str(error),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "service": "EvalForge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------
# Dataset endpoint
# --------------------------------------------------

@app.get("/dataset")
def get_dataset():

    dataset = load_dataset()

    return {
        "total_test_cases": len(dataset),
        "test_cases": dataset,
    }

@app.get("/dataset/{test_case_id}", response_model=TestCaseResponse)
def get_single_test_case(test_case_id: str):

    test_case = get_test_case(test_case_id)

    if not test_case:
        raise HTTPException(
            status_code=404,
            detail="Test case not found.",
        )

    return test_case

@app.post(
    "/dataset",
    response_model=TestCaseResponse,
    status_code=201,
)
def add_test_case(request: CreateTestCaseRequest):

    test_case = create_test_case(
        request.model_dump()
    )

    return test_case

@app.put(
    "/dataset/{test_case_id}",
    response_model=TestCaseResponse,
)
def edit_test_case(
    test_case_id: str,
    request: UpdateTestCaseRequest,
):

    updated_test_case = update_test_case(
        test_case_id,
        request.model_dump(),
    )

    if not updated_test_case:
        raise HTTPException(
            status_code=404,
            detail="Test case not found.",
        )

    return updated_test_case

@app.delete("/dataset/{test_case_id}")
def remove_test_case(test_case_id: str):

    deleted = delete_test_case(test_case_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Test case not found.",
        )

    return {
        "message": "Test case deleted successfully.",
        "id": test_case_id,
    }

# --------------------------------------------------
# Start evaluation
# --------------------------------------------------

@app.post("/evaluations", status_code=202)
def start_evaluation(background_tasks: BackgroundTasks):

    with evaluation_lock:

        # Prevent multiple simultaneous evaluations.
        for evaluation in evaluations.values():

            if evaluation["status"] in ("queued", "running"):

                raise HTTPException(
                    status_code=409,
                    detail="An evaluation is already in progress.",
                )

        evaluation_id = str(uuid4())

        evaluations[evaluation_id] = {
            "id": evaluation_id,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    background_tasks.add_task(
        execute_evaluation,
        evaluation_id,
    )

    return {
        "message": "Evaluation started successfully.",
        "evaluation_id": evaluation_id,
        "status": "queued",
    }


# --------------------------------------------------
# Get evaluation status/results
# --------------------------------------------------

@app.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str):

    evaluation = evaluations.get(evaluation_id)

    if not evaluation:

        raise HTTPException(
            status_code=404,
            detail="Evaluation not found.",
        )

    return evaluation


# --------------------------------------------------
# List generated reports
# --------------------------------------------------

@app.get("/reports")
def get_reports():

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    reports = []

    for report_file in sorted(
        REPORTS_DIR.glob("evaluation_*.json"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    ):

        reports.append({
            "filename": report_file.name,
            "created_at": datetime.fromtimestamp(
                report_file.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat(),
            "size_bytes": report_file.stat().st_size,
        })

    return {
        "total_reports": len(reports),
        "reports": reports,
    }


# --------------------------------------------------
# Retrieve a specific report
# --------------------------------------------------

@app.get("/reports/{filename}")
def get_report(filename: str):

    # Prevent path traversal.
    if Path(filename).name != filename or not filename.endswith(".json"):

        raise HTTPException(
            status_code=400,
            detail="Invalid report filename.",
        )

    report_path = REPORTS_DIR / filename

    if not report_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    with open(report_path, "r", encoding="utf-8") as file:

        return json.load(file)