import json
import os
from pathlib import Path

from dotenv import load_dotenv
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    HallucinationMetric,
)
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase
from app.dataset_repository import load_dataset

from app.reporter import generate_report

load_dotenv()


def create_test_cases(dataset):
    test_cases = []

    for item in dataset:
        test_case = LLMTestCase(
            input=item["input"],
            actual_output=item["actual_output"],
            expected_output=item["expected_output"],
            retrieval_context=item["context"],
            context=item["context"],
        )

        test_cases.append(test_case)

    return test_cases


def build_metrics(judge_model=None):
    """Build evaluation metrics using the selected judge model."""

    model_config = (
        {"model": judge_model}
        if judge_model is not None
        else {}
    )

    return [
        FaithfulnessMetric(
            threshold=0.7,
            async_mode=False,
            **model_config,
        ),
        AnswerRelevancyMetric(
            threshold=0.7,
            async_mode=False,
            **model_config,
        ),
        HallucinationMetric(
            threshold=0.7,
            async_mode=False,
            **model_config,
        ),
    ]


def is_rate_limit_error(error):
    """Identify rate-limit failures, including wrapped exceptions."""

    message = str(error).lower()

    indicators = (
        "429",
        "rate limit",
        "ratelimiterror",
        "free-models-per-day",
        "too many requests",
    )

    return any(indicator in message for indicator in indicators)


def run_with_openrouter(test_cases):
    print("\n[EvalForge] Starting evaluation with OpenRouter...")

    return evaluate(
        test_cases=test_cases,
        metrics=build_metrics(),
    )


def run_with_ollama(test_cases):
    model_name = os.getenv("OLLAMA_MODEL_NAME")

    if not model_name:
        raise RuntimeError(
            "OLLAMA_MODEL_NAME is missing. "
            "Set it in your .env file."
        )

    base_url = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    )

    print(
        f"\n[EvalForge] OpenRouter rate limit reached. "
        f"Switching to local Ollama model: {model_name}"
    )

    judge_model = OllamaModel(
        model=model_name,
        base_url=base_url,
        temperature=0,
    )

    return evaluate(
        test_cases=test_cases,
        metrics=build_metrics(judge_model),
    )


def run_evaluation():
    dataset = load_dataset()
    test_cases = create_test_cases(dataset)

    provider = "openrouter"

    try:
        evaluation_result = run_with_openrouter(test_cases)

    except Exception as error:
        if not is_rate_limit_error(error):
            raise

        print(
            "\n[EvalForge] OpenRouter rate limit detected. "
            "Attempting local fallback..."
        )

        # Rerun the complete dataset using one judge model.
        # Do not silently mix providers within the same report.
        evaluation_result = run_with_ollama(test_cases)
        provider = "ollama"

    print(f"\n[EvalForge] Evaluation provider: {provider}")

    report = generate_report(
        evaluation_result,
        dataset,
        provider=provider,
    )

    return {
        "provider": provider,
        "report": report,
    }


if __name__ == "__main__":
    run_evaluation()