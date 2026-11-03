from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Evaluation(Base):
    __tablename__ = "evaluations"

    __table_args__ = (
        Index("ix_evaluations_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="queued",
        nullable=False,
    )

    total_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    passed_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    failed_tests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    pass_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    report_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metrics: Mapped[list[EvaluationMetric]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"

    __table_args__ = (
        UniqueConstraint(
            "evaluation_id",
            "metric_name",
            name="uq_evaluation_metric",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    evaluation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metric_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    average_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    pass_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    total: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    passed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    evaluation: Mapped[Evaluation] = relationship(
        back_populates="metrics",
    )