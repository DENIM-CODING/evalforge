import json
import logging

import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Evaluation
from app.schemas import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest,
    TestCaseResponse,
    StartEvaluationRequest,
)
from app.dataset_repository import (
    load_dataset,
    get_test_case,
    create_test_case,
    update_test_case,
    delete_test_case,
)
from app.evaluator import (
    run_evaluation,
    OpenRouterRateLimitError,
)
from app.evaluation_repository import (
    create_evaluation,
    update_evaluation_status,
    complete_evaluation,
    get_evaluation,
    get_evaluation_history,
    get_active_evaluation,
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------

app = FastAPI(
    title="EvalForge API",
    description="An LLM evaluation framework for testing AI application quality.",
    version="1.0.0",
)

API_KEY = os.getenv("API_KEY")


@app.middleware("http")
async def authenticate_requests(request: Request, call_next):
    # Keep health checks publicly accessible for deployment platforms.
    if request.url.path == "/health":
        return await call_next(request)

    if not API_KEY:
        logger.error("API_KEY is not configured.")
        return JSONResponse(
            status_code=503,
            content={"detail": "API authentication is not configured."},
        )

    provided_key = request.headers.get("X-API-Key", "")

    if not hmac.compare_digest(provided_key, API_KEY):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key."},
        )

    return await call_next(request)

MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024  # 2 MB


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            request_size = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header."},
            )

        if request_size < 0 or request_size > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body exceeds the 2 MB limit."},
            )

    return await call_next(request)

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"

logger = logging.getLogger(__name__)

# Prevent simultaneous evaluation starts within this API process.
evaluation_lock = Lock()


# --------------------------------------------------
# Utility functions
# --------------------------------------------------

def serialize_evaluation(
    evaluation: Evaluation,
    include_report: bool = False,
) -> dict:
    """Convert a database evaluation record into an API response."""

    report = None

    if include_report and evaluation.report_path:
        report_path = Path(evaluation.report_path).resolve()

        # Only read reports located inside the reports directory.
        if report_path.is_relative_to(REPORTS_DIR.resolve()):
            if report_path.is_file():
                with open(report_path, "r", encoding="utf-8") as file:
                    report = json.load(file)

    return {
        "id": evaluation.id,
        "status": evaluation.status,
        "provider": evaluation.provider,
        "total_tests": evaluation.total_tests,
        "passed_tests": evaluation.passed_tests,
        "failed_tests": evaluation.failed_tests,
        "pass_rate": evaluation.pass_rate,
        "report_path": evaluation.report_path,
        "error": evaluation.error_message,
        "error_message": evaluation.error_message,
        "created_at": (
            evaluation.created_at.isoformat()
            if evaluation.created_at else None
        ),
        "started_at": (
            evaluation.started_at.isoformat()
            if evaluation.started_at else None
        ),
        "completed_at": (
            evaluation.completed_at.isoformat()
            if evaluation.completed_at else None
        ),
        "metrics": [
            {
                "name": metric.metric_name,
                "average_score": metric.average_score,
                "pass_rate": metric.pass_rate,
                "total": metric.total,
                "passed": metric.passed,
                "failed": metric.failed,
            }
            for metric in evaluation.metrics
        ],
        "report": report,
    }


# --------------------------------------------------
# Background evaluation worker
# --------------------------------------------------

def execute_evaluation(evaluation_id: str, metric_config: dict,):

    try:
        # Mark evaluation as running.
        with Session(get_engine()) as session:
            update_evaluation_status(
                session,
                evaluation_id,
                status="running",
                started_at=datetime.now(timezone.utc),
            )

        logger.info("Starting evaluation: %s", evaluation_id)

        # Execute the actual DeepEval/OpenRouter evaluation.
        result = run_evaluation(metric_config)

        # Persist evaluation summary and metric results.
        with Session(get_engine()) as session:
            complete_evaluation(
                session,
                evaluation_id,
                result,
            )

        logger.info("Evaluation completed: %s", evaluation_id)

    except OpenRouterRateLimitError as error:

        logger.warning(
            "OpenRouter rate limit reached for evaluation: %s",
            evaluation_id,
        )

        with Session(get_engine()) as session:
            update_evaluation_status(
                session,
                evaluation_id,
                status="rate_limited",
                error_message=str(error),
            )

    except Exception as error:

        logger.exception(
            "Evaluation failed: %s",
            evaluation_id,
        )

        with Session(get_engine()) as session:
            update_evaluation_status(
                session,
                evaluation_id,
                status="failed",
                error_message=str(error),
            )


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Welcome to EvalForge API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


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
# Dataset endpoints
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

    return create_test_case(request.model_dump())


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
def start_evaluation(
    background_tasks: BackgroundTasks,
    request: StartEvaluationRequest | None = None,
):

    # Use default configuration if no request body is supplied.
    metric_config = (
        request.metrics.model_dump()
        if request
        else StartEvaluationRequest().metrics.model_dump()
    )

    with evaluation_lock:

        with Session(get_engine()) as session:
            active_evaluation = get_active_evaluation(session)

            if active_evaluation:
                raise HTTPException(
                    status_code=409,
                    detail="An evaluation is already in progress.",
                )

            evaluation_id = str(uuid4())

            create_evaluation(
                session,
                evaluation_id,
            )

    background_tasks.add_task(
        execute_evaluation,
        evaluation_id,
        metric_config,
    )

    return {
        "message": "Evaluation started successfully.",
        "evaluation_id": evaluation_id,
        "status": "queued",
        "metric_configuration": metric_config,
    }


# --------------------------------------------------
# Evaluation history
# --------------------------------------------------

@app.get("/evaluations")
def list_evaluations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):

    with Session(get_engine()) as session:
        evaluations = get_evaluation_history(
            session,
            limit=limit,
            offset=offset,
        )

        return {
            "total": len(evaluations),
            "limit": limit,
            "offset": offset,
            "evaluations": [
                serialize_evaluation(evaluation)
                for evaluation in evaluations
            ],
        }


# --------------------------------------------------
# Get evaluation status/results
# --------------------------------------------------

@app.get("/evaluations/{evaluation_id}")
def get_evaluation_details(evaluation_id: str):

    with Session(get_engine()) as session:
        evaluation = get_evaluation(
            session,
            evaluation_id,
        )

        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail="Evaluation not found.",
            )

        return serialize_evaluation(
            evaluation,
            include_report=True,
        )


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