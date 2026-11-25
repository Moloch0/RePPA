# Benchmark datasets

`current.json` names the production-scale node universe and reference graph used by the
standard partition benchmark. Paths are repository-relative; the multi-gigabyte
artifacts themselves remain under `benchmarks/work/` and are not copied here.

The manifest also records the node universe fingerprint, source FASTA fingerprint,
node count, reference graph relation-semantics hash, and edge count. `run_benchmark.py`
checks these values before timing begins. A path that exists but identifies
different data is therefore rejected.

To replace the standard dataset:

1. Create a complete node universe and its matching complete reference graph.
2. Update paths and expected identities in `current.json`.
3. Run the benchmark once and inspect semantic output before changing the
   baseline.
4. Update `baselines/production-schema4.json` only when the new expected result
   has been accepted deliberately.

`--node universe` and `--reference graph` may override the configured paths for relocation,
but the configured identities are still enforced. This makes moving immutable
artifacts safe without weakening reproducibility.
