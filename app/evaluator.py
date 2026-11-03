from dotenv import load_dotenv
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    HallucinationMetric,
)
from deepeval.test_case import LLMTestCase

from app.dataset_repository import load_dataset
from app.reporter import generate_report
from app.schemas import MetricsConfiguration

load_dotenv()


class OpenRouterRateLimitError(RuntimeError):
    """Raised when OpenRouter's API quota or rate limit is exceeded."""


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


from app.schemas import MetricsConfiguration


def build_metrics(configuration=None):
    """
    Build DeepEval metrics using the supplied configuration.

    If no configuration is provided, use default settings.
    """

    if configuration is None:
        configuration = MetricsConfiguration()

    elif isinstance(configuration, dict):
        configuration = MetricsConfiguration.model_validate(
            configuration
        )

    metrics = []

    if configuration.faithfulness.enabled:
        metrics.append(
            FaithfulnessMetric(
                threshold=configuration.faithfulness.threshold,
                async_mode=False,
            )
        )

    if configuration.answer_relevancy.enabled:
        metrics.append(
            AnswerRelevancyMetric(
                threshold=configuration.answer_relevancy.threshold,
                async_mode=False,
            )
        )

    if configuration.hallucination.enabled:
        metrics.append(
            HallucinationMetric(
                threshold=configuration.hallucination.threshold,
                async_mode=False,
            )
        )

    return metrics


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


def run_with_openrouter(test_cases, metric_config=None):
    print("\n[EvalForge] Starting evaluation with OpenRouter...")

    metrics = (
        build_metrics()
        if metric_config is None
        else build_metrics(metric_config)
    )

    return evaluate(
        test_cases=test_cases,
        metrics=metrics,
    )


def run_evaluation(metric_config=None):

    if metric_config is None:
        configuration = MetricsConfiguration()

    elif isinstance(metric_config, MetricsConfiguration):
        configuration = metric_config

    else:
        configuration = MetricsConfiguration.model_validate(
            metric_config
        )

    dataset = load_dataset()
    test_cases = create_test_cases(dataset)

    try:
        evaluation_result = run_with_openrouter(
            test_cases,
            configuration,
        )

    except Exception as error:
        if is_rate_limit_error(error):
            message = (
                "OpenRouter API rate limit exceeded. "
                "Please try again later when your free quota resets."
            )

            print(f"\n[EvalForge] {message}")

            raise OpenRouterRateLimitError(message) from error

        raise

    print("\n[EvalForge] Evaluation provider: OpenRouter")

    report = generate_report(
        evaluation_result,
        dataset,
        provider="openrouter",
        metric_configuration=configuration.model_dump(),
    )

    return {
        "provider": "openrouter",
        "report": report,
    }


if __name__ == "__main__":
    try:
        run_evaluation()
    except OpenRouterRateLimitError:
        pass