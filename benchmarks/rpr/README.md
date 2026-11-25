# RPR partition production benchmark

This directory contains the standardized, single-measurement benchmark for the
historical `rootpart.partition_csr()` pipeline. It measures RPR partitioning only: node universe
and reference graph construction are outside the timed region.

## Layout

```text
rpr/
├── baselines/production-schema4.json  correctness and performance reference
├── configs/production.json           solver parameters, build profile, timeout
├── datasets/current.json              immutable input paths and identities
├── datasets/README.md                 dataset replacement rules
├── compare_benchmark.py               standalone baseline comparison
├── run_benchmark.py                   standard entry point
├── run_solver_benchmark.py            low-level one-run measurement
└── results/                            generated, ignored benchmark outputs
```

The three versioned JSON files define one benchmark contract. Changing an input
artifact, solver parameter, or expected result requires a deliberate update to
that contract rather than an ad hoc command-line variation.

## Build

Build the native extension with the required release profile:

```bash
ROOTPART_BUILD_PROFILE=release \
CXX=/public/home/luoliheng/miniconda3/envs/lightning_env/bin/x86_64-conda-linux-gnu-c++ \
/public/home/luoliheng/miniconda3/envs/lightning_env/bin/python \
  -m pip install -e . --no-build-isolation
```

The runner checks `build/.rootpart_build_config` before starting. A missing
configuration or a profile other than `release` is rejected.

## Run once

From the repository root:

```bash
/public/home/luoliheng/miniconda3/envs/lightning_env/bin/python \
  benchmarks/rpr/run_benchmark.py
```

This performs exactly one measurement. The default output directory is
`benchmarks/rpr/results/TIMESTAMP-production`. An explicit new directory can
be supplied as the positional argument:

```bash
/public/home/luoliheng/miniconda3/envs/lightning_env/bin/python \
  benchmarks/rpr/run_benchmark.py \
  benchmarks/rpr/results/20261021-production
```

Use `--dry-run` to validate the dataset identity, release build, configuration,
and generated command without invoking partition. The output directory must not
already exist, so a previous measurement cannot be overwritten silently.

## Output and gate

Each completed run contains:

```text
RUN/
├── artifact/
│   ├── root_of.tsv
│   ├── diagnostics.summary.tsv
│   ├── metadata.json
│   └── roots.tsv
├── benchmark.json
└── comparison.json
```

`benchmark.json` records wall time, process peak RSS, native round timings,
partition audit/search provenance, input identities, native-extension SHA-256,
build configuration, and SHA-256 for the three stable result files.

`comparison.json` applies two independent gates:

- Correctness requires exact input identities, solver parameters, `T`, `P`,
  `m`, root identity/count, admissibility coverage membership count, termination
  reason, and result-file hashes.
- Performance allows wall-time growth of the larger of 3% or 2 seconds, and
  peak-RSS growth of the larger of 5% or 256 MiB, relative to the checked-in
  single-run reference.

Exit code `0` means both gates passed, `1` means correctness changed, and `2`
means correctness passed but the performance limit was exceeded. Machine load
can affect a single timing result; a code change should be investigated before
updating the baseline.

An existing report can be checked again without rerunning partition:

```bash
/public/home/luoliheng/miniconda3/envs/lightning_env/bin/python \
  benchmarks/rpr/compare_benchmark.py RUN/benchmark.json
```

## Reference

The current baseline uses the 2026-10-21 schema-4 production input with the
`asc` initialization, 48 OpenMP threads, and the release profile. Its
2026-11-06 standard run took 17.483 seconds and 5,026,648,064 bytes peak RSS.
It produced 1,296,308 roots with identity `405b31f5f3e12f32`,
13,130,585 admissibility coverage memberships, and final F1 `9546452/22700421`
(approximately 0.420541).

Generated runs under `results/` are disposable, ignored artifacts. After their
measurements and decisions have been summarized in `RESULTS.md`, they may be
removed. The reproducible runners, dataset/configuration contract, compact
baseline expectations, and result summary are the maintained source artifacts.
