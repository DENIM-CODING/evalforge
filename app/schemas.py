from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------
# Dataset Schemas
# --------------------------------------------------

class TestCaseBase(StrictModel):
    input: Annotated[str, Field(min_length=1, max_length=10_000)]
    actual_output: Annotated[str, Field(min_length=1, max_length=20_000)]
    expected_output: Annotated[str, Field(min_length=1, max_length=20_000)]

    context: list[
        Annotated[str, Field(min_length=1, max_length=10_000)]
    ] = Field(min_length=1, max_length=20)

    @field_validator("input", "actual_output", "expected_output")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot contain only whitespace.")
        return value

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("Context entries cannot contain only whitespace.")
        return value


class CreateTestCaseRequest(TestCaseBase):
    pass


class UpdateTestCaseRequest(TestCaseBase):
    pass


class TestCaseResponse(TestCaseBase):
    id: str = Field(min_length=1, max_length=50)


# --------------------------------------------------
# Evaluation Configuration
# --------------------------------------------------

class MetricSettings(StrictModel):
    enabled: bool = True
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class MetricsConfiguration(StrictModel):
    faithfulness: MetricSettings = Field(default_factory=MetricSettings)
    answer_relevancy: MetricSettings = Field(default_factory=MetricSettings)
    hallucination: MetricSettings = Field(default_factory=MetricSettings)

    @model_validator(mode="after")
    def validate_enabled_metrics(self):
        if not any(
            metric.enabled
            for metric in [
                self.faithfulness,
                self.answer_relevancy,
                self.hallucination,
            ]
        ):
            raise ValueError("At least one evaluation metric must be enabled.")

        return self


class StartEvaluationRequest(StrictModel):
    metrics: MetricsConfiguration = Field(default_factory=MetricsConfiguration)