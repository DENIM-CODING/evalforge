from app.evaluator import build_metrics


def test_default_configuration_builds_all_metrics():

    metrics = build_metrics()

    assert len(metrics) == 3


def test_disabled_metric_is_not_included():

    config = {
        "faithfulness": {
            "enabled": True,
            "threshold": 0.8,
        },
        "answer_relevancy": {
            "enabled": False,
            "threshold": 0.7,
        },
        "hallucination": {
            "enabled": True,
            "threshold": 0.6,
        },
    }

    metrics = build_metrics(config)

    assert len(metrics) == 2


def test_custom_thresholds_are_applied():

    config = {
        "faithfulness": {
            "enabled": True,
            "threshold": 0.9,
        },
        "answer_relevancy": {
            "enabled": False,
            "threshold": 0.7,
        },
        "hallucination": {
            "enabled": False,
            "threshold": 0.7,
        },
    }

    metrics = build_metrics(config)

    assert len(metrics) == 1
    assert metrics[0].threshold == 0.9


def test_invalid_threshold_is_rejected():

    import pytest
    from pydantic import ValidationError
    from app.schemas import MetricsConfiguration

    config = {
        "faithfulness": {
            "enabled": True,
            "threshold": 1.5,
        },
    }

    with pytest.raises(ValidationError):
        MetricsConfiguration(**config)


def test_all_disabled_metrics_are_rejected():

    import pytest
    from pydantic import ValidationError
    from app.schemas import MetricsConfiguration

    config = {
        "faithfulness": {"enabled": False},
        "answer_relevancy": {"enabled": False},
        "hallucination": {"enabled": False},
    }

    with pytest.raises(ValidationError):
        MetricsConfiguration(**config)