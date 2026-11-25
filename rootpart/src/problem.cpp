#include "rootpart/rootpart.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <vector>

namespace rootpart {
namespace {

constexpr std::uint8_t kSourceRepresentsNeighbor = 1u << 0;
constexpr std::uint8_t kNeighborRepresentsSource = 1u << 1;

std::uint8_t forward_bits(Admissibility value) {
    std::uint8_t result = 0;
    if (contains(value, Admissibility::first_represents_second)) {
        result |= kSourceRepresentsNeighbor;
    }
    if (contains(value, Admissibility::second_represents_first)) {
        result |= kNeighborRepresentsSource;
    }
    return result;
}

std::uint8_t reverse_bits(Admissibility value) {
    std::uint8_t result = 0;
    if (contains(value, Admissibility::second_represents_first)) {
        result |= kSourceRepresentsNeighbor;
    }
    if (contains(value, Admissibility::first_represents_second)) {
        result |= kNeighborRepresentsSource;
    }
    return result;
}

}  // namespace

SparseProblem make_sparse_problem(
    std::uint64_t node_count,
    std::span<const UndirectedEdge> input_edges) {
    if (node_count > std::numeric_limits<NodeId>::max()) {
        throw std::invalid_argument(
            "rootpart supports at most 2^32-1 nodes");
    }

    std::vector<UndirectedEdge> edges(input_edges.begin(), input_edges.end());
    std::sort(edges.begin(), edges.end(), [](const auto& left, const auto& right) {
        return left.first < right.first ||
            (left.first == right.first && left.second < right.second);
    });

    std::vector<std::uint64_t> degree(static_cast<std::size_t>(node_count), 0);
    std::optional<std::pair<NodeId, NodeId>> previous;
    for (const auto& edge : edges) {
        if (edge.first >= edge.second || edge.second >= node_count) {
            throw std::invalid_argument(
                "rootpart edges must satisfy first < second < node_count");
        }
        const auto key = std::pair{edge.first, edge.second};
        if (previous == key) {
            throw std::invalid_argument(
                "rootpart reference graph contains a duplicate edge");
        }
        previous = key;
        ++degree[edge.first];
        ++degree[edge.second];
    }

    SparseProblem problem;
    problem.offsets.resize(static_cast<std::size_t>(node_count) + 1, 0);
    for (std::size_t node = 0; node < node_count; ++node) {
        if (degree[node] >
            std::numeric_limits<std::uint64_t>::max() - problem.offsets[node]) {
            throw std::overflow_error("rootpart CSR offset overflow");
        }
        problem.offsets[node + 1] = problem.offsets[node] + degree[node];
    }
    if (problem.offsets.back() >
        static_cast<std::uint64_t>(std::numeric_limits<std::size_t>::max())) {
        throw std::overflow_error("rootpart CSR exceeds process address space");
    }

    problem.nodes.resize(static_cast<std::size_t>(problem.offsets.back()));
    problem.arc_admissibility.resize(problem.nodes.size());
    auto next = problem.offsets;
    for (const auto& edge : edges) {
        const auto forward = next[edge.first]++;
        problem.nodes[forward] = edge.second;
        problem.arc_admissibility[forward] = forward_bits(edge.admissibility);

        const auto reverse = next[edge.second]++;
        problem.nodes[reverse] = edge.first;
        problem.arc_admissibility[reverse] = reverse_bits(edge.admissibility);
    }
    problem.reference_edges = edges.size();
    return problem;
}

std::span<const NodeId> SparseProblem::neighbors(NodeId node) const {
    if (node >= node_count()) {
        throw std::out_of_range("rootpart node is outside the sparse graph");
    }
    return std::span(nodes).subspan(
        offsets[node], offsets[node + 1] - offsets[node]);
}

}  // namespace rootpart
