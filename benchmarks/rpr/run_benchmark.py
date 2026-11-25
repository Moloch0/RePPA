#!/usr/bin/env python3
"""Run the standardized production partition benchmark exactly once."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from compare_benchmark import compare_report, load_object
from run_solver_benchmark import build_configuration, input_identity, write_json_atomic


BENCHMARK_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY = BENCHMARK_DIRECTORY.parents[1]

EXPECTED_SCHEMAS = {
    "dataset": "rootpart_rpr_dataset_v1",
    "config": "rootpart_rpr_benchmark_config_v1",
    "baseline": "rootpart_rpr_benchmark_baseline_v1",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="new output directory; defaults to results/TIMESTAMP-production",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=BENCHMARK_DIRECTORY / "datasets" / "current.json",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=BENCHMARK_DIRECTORY / "configs" / "production.json",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BENCHMARK_DIRECTORY / "baselines" / "production-schema4.json",
    )
    parser.add_argument("--node_universe", type=Path, help="override the dataset node_universe path")
    parser.add_argument("--reference_graph", type=Path, help="override the dataset reference_graph path")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate inputs and print the command without running partition",
    )
    parser.add_argument(
        "--skip-comparison",
        action="store_true",
        help="write benchmark.json without applying the baseline gate",
    )
    return parser


def resolve_dataset_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPOSITORY / path
    return path.resolve(strict=True)


def require_contract(
    dataset: dict[str, Any], config: dict[str, Any], baseline: dict[str, Any]
) -> None:
    documents = {"dataset": dataset, "config": config, "baseline": baseline}
    for name, document in documents.items():
        expected_schema = EXPECTED_SCHEMAS[name]
        if document.get("schema") != expected_schema:
            raise ValueError(
                f"{name} schema must be {expected_schema!r}, "
                f"got {document.get('schema')!r}"
            )
    if dataset.get("path_base") != "repository":
        raise ValueError("dataset path_base must be 'repository'")
    if baseline.get("dataset_id") != dataset.get("id"):
        raise ValueError("baseline dataset_id does not match the selected dataset")
    if baseline.get("config_id") != config.get("id"):
        raise ValueError("baseline config_id does not match the selected config")


def require_selected_values(
    actual: Any, expected: Any, prefix: str = ""
) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise ValueError(f"{prefix}: expected an object, got {actual!r}")
        for key, expected_value in expected.items():
            field = f"{prefix}.{key}" if prefix else key
            if key not in actual:
                raise ValueError(f"{field}: missing")
            require_selected_values(actual[key], expected_value, field)
        return
    if actual != expected:
        raise ValueError(f"{prefix}: expected {expected!r}, got {actual!r}")


def standard_command(
    node_universe: Path,
    reference_graph: Path,
    output: Path,
    parameters: dict[str, Any],
    progress_override: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(BENCHMARK_DIRECTORY / "run_solver_benchmark.py"),
        str(node_universe),
        str(reference_graph),
        str(output),
        "--recall-weight",
        str(parameters["recall_weight"]),
        "--max-epochs",
        str(parameters["max_epochs"]),
        "--min-delta",
        str(parameters["min_delta"]),
        "--initialization",
        str(parameters["initialization"]),
        "--threads",
        str(parameters["threads"]),
    ]
    if progress_override or parameters.get("progress", False):
        command.append("--progress")
    return command


def main() -> int:
    args = build_parser().parse_args()
    dataset_path = args.dataset.resolve(strict=True)
    config_path = args.config.resolve(strict=True)
    baseline_path = args.baseline.resolve(strict=True)
    dataset = load_object(dataset_path)
    config = load_object(config_path)
    baseline = load_object(baseline_path)
    require_contract(dataset, config, baseline)

    node_universe = (
        args.node_universe.resolve(strict=True)
        if args.node_universe
        else resolve_dataset_path(dataset["node_universe"])
    )
    reference_graph = (
        args.reference_graph.resolve(strict=True)
        if args.reference_graph
        else resolve_dataset_path(dataset["reference_graph"])
    )
    observed_identity = input_identity(node_universe, reference_graph)
    require_selected_values(observed_identity, dataset.get("expected", {}), "input")

    build = build_configuration()
    actual_profile = None if build is None else build["values"].get("profile")
    required_profile = config.get("required_build_profile")
    if actual_profile != required_profile:
        raise RuntimeError(
            f"benchmark requires build profile {required_profile!r}, "
            f"but found {actual_profile!r}"
        )

    output = args.output
    if output is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = BENCHMARK_DIRECTORY / "results" / f"{stamp}-production"
    output = output.resolve(strict=False)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")

    command = standard_command(
        node_universe, reference_graph, output, config["parameters"], args.progress
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dataset_id": dataset.get("id"),
                    "config_id": config.get("id"),
                    "build_profile": actual_profile,
                    "input_identity": observed_identity,
                    "output": str(output),
                    "command": command,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        subprocess.run(
            command,
            check=True,
            timeout=config["timeout_seconds"],
            cwd=REPOSITORY,
        )
    except subprocess.TimeoutExpired as error:
        output.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            output / "benchmark.launch.failure.json",
            {
                "schema": "rootpart_rpr_benchmark_launch_failure_v1",
                "reason": "timeout",
                "timeout_seconds": config["timeout_seconds"],
                "command": command,
            },
        )
        raise RuntimeError(
            f"partition benchmark exceeded {config['timeout_seconds']} seconds"
        ) from error

    report_path = output / "benchmark.json"
    report = load_object(report_path)
    report["benchmark_spec"] = {
        "dataset_id": dataset.get("id"),
        "dataset_file": str(dataset_path),
        "config_id": config.get("id"),
        "config_file": str(config_path),
        "baseline_id": baseline.get("id"),
        "baseline_file": str(baseline_path),
        "single_measurement": True,
    }
    write_json_atomic(report_path, report)

    if args.skip_comparison:
        return 0
    comparison = compare_report(report, baseline, dataset, config)
    write_json_atomic(output / "comparison.json", comparison)
    print(json.dumps(comparison, ensure_ascii=False, sort_keys=True))
    if not comparison["correctness_passed"]:
        return 1
    if not comparison["performance_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
