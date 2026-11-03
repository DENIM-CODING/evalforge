import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPORTS_DIR = Path(__file__).parent.parent / "reports"


def generate_report(evaluation_result, dataset, provider="unknown"):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    test_results = evaluation_result.test_results

    test_cases = []
    metric_stats = defaultdict(
        lambda: {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "scores": [],
        }
    )

    for index, result in enumerate(test_results):
        dataset_item = dataset[index]

        metric_results = []

        for metric in result.metrics_data:
            metric_name = metric.name

            metric_results.append({
                "name": metric_name,
                "score": metric.score,
                "threshold": metric.threshold,
                "passed": metric.success,
                "reason": metric.reason,
            })

            stats = metric_stats[metric_name]
            stats["total"] += 1

            if metric.success:
                stats["passed"] += 1
            else:
                stats["failed"] += 1

            if metric.score is not None:
                stats["scores"].append(metric.score)

        test_cases.append({
            "id": dataset_item.get("id", f"TC{index + 1:03d}"),
            "input": result.input,
            "actual_output": result.actual_output,
            "expected_output": result.expected_output,
            "passed": result.success,
            "metrics": metric_results,
        })

    metric_summary = {}

    for metric_name, stats in metric_stats.items():
        total = stats["total"]

        metric_summary[metric_name] = {
            "average_score": (
                sum(stats["scores"]) / len(stats["scores"])
                if stats["scores"] else None
            ),
            "pass_rate": (
                stats["passed"] / total * 100
                if total else 0
            ),
            "total": total,
            "passed": stats["passed"],
            "failed": stats["failed"],
        }

    total_tests = len(test_cases)
    passed_tests = sum(
        1 for test in test_cases if test["passed"]
    )

    report = {
        "project": "EvalForge",
        "provider": provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": total_tests - passed_tests,
            "pass_rate": (
                passed_tests / total_tests * 100
                if total_tests else 0
            ),
        },
        "metrics": metric_summary,
        "test_cases": test_cases,
    }

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = REPORTS_DIR / f"evaluation_{timestamp}.json"

    report["report_path"] = str(report_path)

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print(f"\nEvaluation report saved: {report_path}")

    return report