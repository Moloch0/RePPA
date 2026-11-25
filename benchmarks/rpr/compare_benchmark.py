#!/usr/bin/env python3
"""Compare one standardized partition benchmark report with its baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_solver_benchmark import write_json_atomic


def load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def selected_mismatches(
    actual: Any, expected: Any, prefix: str = ""
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [{"field": prefix, "expected": expected, "actual": actual}]
        for key, expected_value in expected.items():
            field = f"{prefix}.{key}" if prefix else key
            if key not in actual:
                mismatches.append(
                    {"field": field, "expected": expected_value, "actual": None}
                )
            else:
                mismatches.extend(
                    selected_mismatches(actual[key], expected_value, field)
                )
        return mismatches
    if actual != expected:
        mismatches.append({"field": prefix, "expected": expected, "actual": actual})
    return mismatches


def performance_check(
    name: str,
    actual: float | int,
    reference: float | int,
    relative_fraction: float,
    absolute_allowance: float | int,
) -> dict[str, Any]:
    allowance = max(reference * relative_fraction, absolute_allowance)
    limit = reference + allowance
    return {
        "name": name,
        "passed": actual <= limit,
        "actual": actual,
        "reference": reference,
        "limit": limit,
    }


def compare_report(
    report: dict[str, Any],
    baseline: dict[str, Any],
    dataset: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    correctness_mismatches: list[dict[str, Any]] = []
    correctness_mismatches.extend(
        selected_mismatches(
            report.get("input_identity"), dataset.get("expected", {}), "input_identity"
        )
    )
    correctness_mismatches.extend(
        selected_mismatches(
            report.get("parameters"), config.get("parameters", {}), "parameters"
        )
    )
    correctness_mismatches.extend(
        selected_mismatches(
            {
                "native_statistics": report.get("native_statistics"),
                "partition_search": report.get("partition_search"),
                "artifact": report.get("artifact", {}).get("summary"),
            },
            baseline.get("expected", {}),
            "result",
        )
    )

    required_profile = config.get("required_build_profile")
    native_build = report.get("environment", {}).get("native_build", {})
    configuration = native_build.get("configuration") or {}
    actual_profile = (configuration.get("values") or {}).get("profile")
    if actual_profile != required_profile:
        correctness_mismatches.append(
            {
                "field": "environment.native_build.configuration.values.profile",
                "expected": required_profile,
                "actual": actual_profile,
            }
        )

    performance = baseline["performance"]
    reference = performance["reference"]
    allowed = performance["allowed_regression"]
    runtime = report["runtime"]
    performance_checks = [
        performance_check(
            "wall_seconds",
            runtime["wall_seconds"],
            reference["wall_seconds"],
            allowed["wall_seconds"]["relative_fraction"],
            allowed["wall_seconds"]["absolute_seconds"],
        ),
        performance_check(
            "process_peak_rss_bytes",
            runtime["process_peak_rss_bytes"],
            reference["process_peak_rss_bytes"],
            allowed["process_peak_rss_bytes"]["relative_fraction"],
            allowed["process_peak_rss_bytes"]["absolute_bytes"],
        ),
    ]
    correctness_passed = not correctness_mismatches
    performance_passed = all(check["passed"] for check in performance_checks)
    return {
        "schema": "rootpart_rpr_benchmark_comparison_v1",
        "passed": correctness_passed and performance_passed,
        "correctness_passed": correctness_passed,
        "performance_passed": performance_passed,
        "dataset_id": dataset.get("id"),
        "config_id": config.get("id"),
        "baseline_id": baseline.get("id"),
        "correctness_mismatches": correctness_mismatches,
        "performance_checks": performance_checks,
    }


def build_parser() -> argparse.ArgumentParser:
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=directory / "baselines" / "production-schema4.json",
    )
    parser.add_argument(
        "--dataset", type=Path, default=directory / "datasets" / "current.json"
    )
    parser.add_argument(
        "--config", type=Path, default=directory / "configs" / "production.json"
    )
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_path = args.report.resolve(strict=True)
    comparison = compare_report(
        load_object(report_path),
        load_object(args.baseline.resolve(strict=True)),
        load_object(args.dataset.resolve(strict=True)),
        load_object(args.config.resolve(strict=True)),
    )
    output = args.output or report_path.with_name("comparison.json")
    write_json_atomic(output, comparison)
    print(json.dumps(comparison, ensure_ascii=False, sort_keys=True))
    if not comparison["correctness_passed"]:
        return 1
    if not comparison["performance_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
