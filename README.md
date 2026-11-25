# rootpart

`rootpart` partitions a sparse reference graph into rooted blocks.

## Installation

Install the Python package directly from the tagged public repository:

```bash
python -m pip install \
  "rootpart @ git+https://github.com/Moloch0/rootpart.git@v0.1.0"
```

The C++ library supports normal CMake installation and package discovery:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
cmake --install build --prefix /your/install/prefix
```

Consumers can then use `find_package(rootpart CONFIG REQUIRED)` and link
`rootpart::rootpart`.

The library has no sequence, structure, peptide, database, or artifact
semantics.  Its input is:

- an undirected sparse reference graph;
- two directed admissibility bits per reference edge, declaring whether either
  endpoint may represent the other;
- solver configuration for the pairwise precision/recall objective.

Its output is the selected roots, one root mapping per node, an exact
partition audit, and solver statistics.  The default solver is
Relax–Project–Refine (RPR).

## Sparse input contract

The native interface consumes symmetric CSR arrays:

- `offsets`: unsigned 64-bit row offsets;
- `nodes`: unsigned 32-bit neighboring node IDs;
- `admissibility`: one unsigned byte parallel to `nodes`;

For a CSR arc `source -> neighbor`, admissibility bit `0x01` means that
`source` may represent `neighbor`; bit `0x02` means that `neighbor` may
represent `source`. Reverse CSR arcs must contain the corresponding swapped
bits. Rows are strictly sorted, the graph is symmetric, and self-loops and
duplicate edges are rejected.

Python exposes the same boundary without PepClust-specific objects:

```python
from rootpart import partition_csr

result = partition_csr(
    offsets,
    nodes,
    admissibility,
    recall_weight="1/2",
    min_delta="1/100",
    threads=8,
    max_epochs=5,
    initialization="asc",
)
```

`result` contains `roots`, `root_of`, `audit`, `rounds`, and `provenance`.
The audit and every round expose the exact optimized `objective` in addition
to pairwise precision, recall, and F1.
