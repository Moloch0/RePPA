#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace reppa {

using NodeId = std::uint32_t;

enum class Admissibility : std::uint8_t {
    none = 0,
    first_represents_second = 1u << 0,
    second_represents_first = 1u << 1,
    bidirectional = first_represents_second | second_represents_first,
};

[[nodiscard]] constexpr Admissibility operator|(
    Admissibility left,
    Admissibility right) noexcept {
    return static_cast<Admissibility>(
        static_cast<std::uint8_t>(left) |
        static_cast<std::uint8_t>(right));
}

[[nodiscard]] constexpr bool contains(
    Admissibility value,
    Admissibility direction) noexcept {
    const auto bits = static_cast<std::uint8_t>(direction);
    return (static_cast<std::uint8_t>(value) & bits) == bits;
}

// Canonical sparse-graph edge. first must be smaller than second.  The two
// direction bits describe only representability; the undirected edge itself
// belongs to the reference graph used by the partition objective.
struct UndirectedEdge {
    NodeId first{};
    NodeId second{};
    Admissibility admissibility{Admissibility::bidirectional};
};

struct SparseProblemView {
    std::span<const std::uint64_t> offsets;
    std::span<const NodeId> nodes;
    std::span<const std::uint8_t> arc_admissibility;
    std::uint64_t reference_edges{};

    [[nodiscard]] std::size_t node_count() const noexcept {
        return offsets.empty() ? 0 : offsets.size() - 1;
    }
};

// Symmetric CSR used by the solver. arc_admissibility is parallel to nodes:
// bit 0 means the CSR-row source may represent the neighboring node, and bit 1
// means the neighboring node may represent the CSR-row source.
struct SparseProblem {
    std::vector<std::uint64_t> offsets;
    std::vector<NodeId> nodes;
    std::vector<std::uint8_t> arc_admissibility;
    std::uint64_t reference_edges{};

    [[nodiscard]] std::size_t node_count() const noexcept {
        return offsets.empty() ? 0 : offsets.size() - 1;
    }

    [[nodiscard]] std::span<const NodeId> neighbors(NodeId node) const;
    [[nodiscard]] SparseProblemView view() const noexcept {
        return {offsets, nodes, arc_admissibility, reference_edges};
    }
};

[[nodiscard]] SparseProblem make_sparse_problem(
    std::uint64_t node_count,
    std::span<const UndirectedEdge> edges);

enum class TerminationReason : std::uint8_t {
    no_strict_improvement,
    min_delta_reached,
    max_epochs_reached,
    objective_undefined_no_reference_edges,
    objective_undefined_no_admissible_pairs,
};

struct ExactRatio {
    std::uint64_t numerator{};
    std::uint64_t denominator{1};

    [[nodiscard]] bool operator==(const ExactRatio&) const noexcept = default;
};

struct Metrics {
    std::optional<ExactRatio> objective;
    std::optional<ExactRatio> precision;
    std::optional<ExactRatio> recall;
    std::optional<ExactRatio> f1;
};

struct RoundStatistics {
    std::uint32_t round{};
    Metrics candidate;
    std::uint64_t relax_wall_ns{};
    std::uint64_t project_wall_ns{};
    std::uint64_t legal_wall_ns{};
    std::uint64_t total_wall_ns{};
    bool accepted{};
};

struct SolverConfig {
    std::string recall_weight{"1/2"};
    std::string min_delta{"1/100"};
    std::uint32_t threads{48};
    std::uint32_t max_epochs{5};
    std::string initialization{"asc"};
};

struct SolverStatistics {
    std::vector<RoundStatistics> rounds;
    TerminationReason termination_reason{TerminationReason::max_epochs_reached};
};

struct PartitionAudit {
    ExactRatio recall_weight;
    std::uint64_t reference_edges{};
    std::uint64_t true_positive_edges{};
    std::uint64_t predicted_pairs{};
    std::optional<ExactRatio> objective;
    std::optional<ExactRatio> precision;
    std::optional<ExactRatio> recall;
    std::optional<ExactRatio> f1;
};

struct SolverProvenance {
    std::string solver{"relax_project_refine"};
    std::uint32_t solver_version{1};
    std::string selected_initialization;
    std::string requested_initialization;
    std::string objective_policy{"exact_pairwise_f_beta"};
    std::string feasibility_policy{"pairwise_representative_admissibility"};
    std::string numerical_policy{"exact_integer_cross_multiplication"};
    std::string optimality_claim{"heuristic_local_optimum"};
    bool deterministic_reduction{true};
    std::uint32_t max_epochs{};
    ExactRatio min_delta;
    std::string termination_reason;
};

struct PartitionResult {
    std::vector<NodeId> representatives;
    std::vector<NodeId> representative_of;
    PartitionAudit audit;
    SolverProvenance provenance;
    SolverStatistics statistics;
};

[[nodiscard]] ExactRatio parse_unit_exact_ratio(
    const std::string& text,
    const char* parameter_name);

[[nodiscard]] const char* to_string(TerminationReason reason) noexcept;

[[nodiscard]] PartitionResult partition(
    SparseProblemView problem,
    const SolverConfig& config = {});

[[nodiscard]] inline PartitionResult partition(
    const SparseProblem& problem,
    const SolverConfig& config = {}) {
    return partition(problem.view(), config);
}

}  // namespace reppa
