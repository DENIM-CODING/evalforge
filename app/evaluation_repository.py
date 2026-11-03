from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import Evaluation, EvaluationMetric


def create_evaluation(
    session: Session,
    evaluation_id: str,
) -> Evaluation:
    evaluation = Evaluation(
        id=evaluation_id,
        status="queued",
    )

    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)

    return evaluation


def update_evaluation_status(
    session: Session,
    evaluation_id: str,
    status: str,
    started_at: datetime | None = None,
    error_message: str | None = None,
) -> Evaluation | None:

    evaluation = session.get(Evaluation, evaluation_id)

    if not evaluation:
        return None

    evaluation.status = status

    if started_at is not None:
        evaluation.started_at = started_at

    if error_message is not None:
        evaluation.error_message = error_message

    if status in ("completed", "failed", "rate_limited"):
        evaluation.completed_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(evaluation)

    return evaluation


def complete_evaluation(
    session: Session,
    evaluation_id: str,
    result: dict,
) -> Evaluation | None:

    evaluation = session.get(Evaluation, evaluation_id)

    if not evaluation:
        return None

    report = result["report"]
    summary = report["summary"]

    evaluation.status = "completed"
    evaluation.provider = result["provider"]

    evaluation.total_tests = summary["total_tests"]
    evaluation.passed_tests = summary["passed"]
    evaluation.failed_tests = summary["failed"]
    evaluation.pass_rate = summary["pass_rate"]

    evaluation.report_path = report.get("report_path")
    evaluation.error_message = None
    evaluation.completed_at = datetime.now(timezone.utc)

    # Replace metric summaries for this evaluation.
    session.execute(
        delete(EvaluationMetric).where(
            EvaluationMetric.evaluation_id == evaluation_id
        )
    )

    for metric_name, stats in report["metrics"].items():

        metric = EvaluationMetric(
            evaluation_id=evaluation_id,
            metric_name=metric_name,
            average_score=stats["average_score"],
            pass_rate=stats["pass_rate"],
            total=stats["total"],
            passed=stats["passed"],
            failed=stats["failed"],
        )

        session.add(metric)

    session.commit()

    return get_evaluation(session, evaluation_id)


def get_evaluation(
    session: Session,
    evaluation_id: str,
) -> Evaluation | None:

    statement = (
        select(Evaluation)
        .options(selectinload(Evaluation.metrics))
        .where(Evaluation.id == evaluation_id)
    )

    return session.scalar(statement)


def get_evaluation_history(
    session: Session,
    limit: int = 20,
    offset: int = 0,
) -> list[Evaluation]:

    statement = (
        select(Evaluation)
        .options(selectinload(Evaluation.metrics))
        .order_by(Evaluation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(session.scalars(statement).all())

def get_active_evaluation(session: Session) -> Evaluation | None:
    statement = (
        select(Evaluation)
        .where(Evaluation.status.in_(["queued", "running"]))
        .limit(1)
    )

    return session.scalar(statement)