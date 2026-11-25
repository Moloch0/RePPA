#!/usr/bin/env python3
"""Low-level runner for one production partition benchmark invocation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the historical rootpart.partition_csr pipeline once and preserve "
            "its audit and search provenance with resource measurements."
        )
    )
    parser.add_argument("node_universe", type=Path)
    parser.add_argument("reference_graph", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--recall-weight", default="1/2")
    parser.add_argument("--max-epochs", type=int, default=5)
    parser.add_argument("--min-delta", default="0.01")
    parser.add_argument(
        "--initialization",
        choices=("desc", "asc", "local"),
        default="asc",
    )
    parser.add_argument("--threads", type=int, default=48)
    parser.add_argument("--progress", action="store_true")
    return parser


def peak_rss_bytes(usage: resource.struct_rusage) -> int:
    # Linux reports KiB; macOS and the BSD family report bytes.
    scale = 1 if sys.platform == "darwin" else 1024
    return int(usage.ru_maxrss) * scale


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def build_configuration() -> dict[str, Any] | None:
    repository = Path(__file__).resolve().parents[2]
    path = repository / "build" / ".rootpart_build_config"
    if not path.is_file():
        return None
    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            key, separator, value = line.rstrip("\n").partition("=")
            if separator:
                values[key] = value
    return {"path": str(path), "values": values}


def native_build_provenance() -> dict[str, Any]:
    specification = importlib.util.find_spec("rootpart._core")
    if specification is None or specification.origin is None:
        return {"path": None, "sha256": None}
    path = Path(specification.origin).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    status = path.stat()
    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "size_bytes": status.st_size,
        "mtime_ns": status.st_mtime_ns,
        "configuration": build_configuration(),
    }


def input_identity(node_universe: Path, reference_graph: Path) -> dict[str, Any]:
    node_universe_metadata = load_json(node_universe / "metadata.json")
    reference_graph_metadata = load_json(reference_graph / "metadata.json")
    reference_graph_manifest = load_json(reference_graph / "manifest.json")
    return {
        "node_universe": {
            "artifact_type": node_universe_metadata.get("artifact_type"),
            "schema_version": node_universe_metadata.get("schema_version"),
            "complete": node_universe_metadata.get("complete"),
            "node_universe_identity_fnv1a64": node_universe_metadata.get(
                "node_universe_identity_fnv1a64"
            ),
            "source_identity_fnv1a64": node_universe_metadata.get(
                "source_identity_fnv1a64"
            ),
            "node_count": node_universe_metadata.get("node_count"),
        },
        "reference_graph": {
            "artifact_type": reference_graph_metadata.get("artifact_type"),
            "schema_version": reference_graph_metadata.get("schema_version"),
            "complete": reference_graph_metadata.get("complete"),
            "manifest_schema_version": reference_graph_manifest.get("schema_version"),
            "node_universe_identity_fnv1a64": reference_graph_manifest.get(
                "node_universe_identity_fnv1a64"
            ),
            "relation_semantics_hash_fnv1a64": reference_graph_manifest.get(
                "relation_semantics_hash_fnv1a64"
            ),
            "node_count": reference_graph_manifest.get("node_count"),
            "relation_edges": reference_graph_manifest.get("relation_edges"),
        },
    }


def artifact_summary(artifact: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name in (
        "roots.tsv",
        "root_of.tsv",
        "diagnostics.summary.tsv",
    ):
        path = artifact / name
        status = path.stat()
        files[name] = {
            "sha256": sha256_file(path),
            "size_bytes": status.st_size,
        }
    return {
        "root_count": metadata.get("root_set", {}).get("count"),
        "root_identity_fnv1a64": metadata.get(
            "root_set", {}
        ).get("identity_fnv1a64"),
        "admissible_membership_count": metadata.get("admissibility_coverage", {}).get(
            "membership_count"
        ),
        "termination_reason": metadata.get("partition_search", {}).get(
            "termination_reason"
        ),
        "files": files,
    }


def main() -> int:
    args = build_parser().parse_args()
    if args.threads < 1:
        raise ValueError("--threads must be at least 1")
    if args.max_epochs < 1:
        raise ValueError("--max-epochs must be at least 1")

    node_universe = args.node_universe.resolve(strict=True)
    reference_graph = args.reference_graph.resolve(strict=True)
    output = args.output.resolve(strict=False)
    output.mkdir(parents=True, exist_ok=False)
    artifact = output / "artifact"

    from rootpart import __version__, partition_csr

    parameters = {
        "recall_weight": args.recall_weight,
        "max_epochs": args.max_epochs,
        "min_delta": args.min_delta,
        "initialization": args.initialization,
        "threads": args.threads,
        "progress": args.progress,
    }
    started_at = datetime.now(timezone.utc).isoformat()
    before = resource.getrusage(resource.RUSAGE_SELF)
    begin_ns = time.perf_counter_ns()
    try:
        statistics = partition_csr(
            node_universe,
            reference_graph,
            artifact,
            recall_weight=args.recall_weight,
            max_epochs=args.max_epochs,
            min_delta=args.min_delta,
            initialization=args.initialization,
            threads=args.threads,
            progress=args.progress,
        )
    except BaseException as error:
        after = resource.getrusage(resource.RUSAGE_SELF)
        failure = {
            "schema": "rootpart_rpr_benchmark_failure_v3",
            "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {"node_universe": str(node_universe), "reference_graph": str(reference_graph)},
            "parameters": parameters,
            "runtime": {
                "wall_seconds": (time.perf_counter_ns() - begin_ns) / 1e9,
                "user_cpu_seconds": after.ru_utime - before.ru_utime,
                "system_cpu_seconds": after.ru_stime - before.ru_stime,
                "process_peak_rss_bytes": peak_rss_bytes(after),
            },
            "error": {"type": type(error).__name__, "message": str(error)},
        }
        write_json_atomic(output / "benchmark.failure.json", failure)
        raise

    end_ns = time.perf_counter_ns()
    after = resource.getrusage(resource.RUSAGE_SELF)
    metadata_path = artifact / "metadata.json"
    with metadata_path.open("r", encoding="utf-8") as stream:
        metadata = json.load(stream)

    report = {
        "schema": "rootpart_rpr_benchmark_v3",
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "rootpart_version": __version__,
            "python": sys.version,
            "platform": platform.platform(),
            "native_build": native_build_provenance(),
        },
        "inputs": {"node_universe": str(node_universe), "reference_graph": str(reference_graph)},
        "input_identity": input_identity(node_universe, reference_graph),
        "parameters": parameters,
        "runtime": {
            "wall_seconds": (end_ns - begin_ns) / 1e9,
            "user_cpu_seconds": after.ru_utime - before.ru_utime,
            "system_cpu_seconds": after.ru_stime - before.ru_stime,
            "process_peak_rss_bytes": peak_rss_bytes(after),
        },
        "native_statistics": statistics,
        "partition_audit": metadata.get("partition_audit"),
        "partition_search": metadata.get("partition_search"),
        "artifact": {
            "path": str(artifact),
            "metadata_path": str(metadata_path),
            "summary": artifact_summary(artifact, metadata),
        },
    }
    write_json_atomic(output / "benchmark.json", report)

    search = report["partition_search"] or {}
    audit = report["partition_audit"] or {}
    print(
        json.dumps(
            {
                "benchmark": str(output / "benchmark.json"),
                "wall_seconds": report["runtime"]["wall_seconds"],
                "process_peak_rss_bytes": report["runtime"][
                    "process_peak_rss_bytes"
                ],
                "termination_reason": search.get("termination_reason"),
                "initial_incumbent": search.get("initial_incumbent"),
                "root_count": metadata.get("root_set", {}).get(
                    "count"
                ),
                "reference_edges": audit.get("reference_edges"),
                "true_positive_edges": audit.get("true_positive_edges"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
