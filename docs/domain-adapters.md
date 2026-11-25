# Domain adapter boundary

`rootpart` is intentionally independent of any application domain. A consumer
adapts its own data to three solver inputs:

- a fixed node universe;
- an undirected sparse reference graph;
- directed root-to-member admissibility on each reference edge.

The solver returns selected roots, one root mapping per node, an exact
partition audit, and RPR statistics. Reading domain artifacts, deriving
admissibility, and writing domain-specific outputs remain responsibilities of
the consuming library.

This boundary allows multiple consumers to share the same partition stage
without adding peptide, sequence, structure, database, or artifact semantics
to `rootpart`.
