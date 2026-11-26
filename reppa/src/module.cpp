#include "reppa/reppa.hpp"

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <optional>
#include <stdexcept>
#include <string>
#include <cstring>

namespace py = pybind11;

namespace {

py::object ratio_object(const std::optional<reppa::ExactRatio>& ratio) {
    if (!ratio.has_value()) return py::none();
    return py::make_tuple(ratio->numerator, ratio->denominator);
}

py::dict result_dict(const reppa::PartitionResult& result) {
    const auto vector_array = [](const std::vector<reppa::NodeId>& values) {
        py::array_t<reppa::NodeId> array(values.size());
        if (!values.empty()) {
            std::memcpy(
                array.mutable_data(),
                values.data(),
                values.size() * sizeof(reppa::NodeId));
        }
        return array;
    };
    py::dict audit;
    audit["recall_weight"] = py::make_tuple(
        result.audit.recall_weight.numerator,
        result.audit.recall_weight.denominator);
    audit["reference_edges"] = result.audit.reference_edges;
    audit["true_positive_edges"] = result.audit.true_positive_edges;
    audit["predicted_pairs"] = result.audit.predicted_pairs;
    audit["objective"] = ratio_object(result.audit.objective);
    audit["precision"] = ratio_object(result.audit.precision);
    audit["recall"] = ratio_object(result.audit.recall);
    audit["f1"] = ratio_object(result.audit.f1);

    py::list rounds;
    for (const auto& round : result.statistics.rounds) {
        py::dict value;
        value["round"] = round.round;
        value["objective"] = ratio_object(round.candidate.objective);
        value["precision"] = ratio_object(round.candidate.precision);
        value["recall"] = ratio_object(round.candidate.recall);
        value["f1"] = ratio_object(round.candidate.f1);
        value["relax_wall_ns"] = round.relax_wall_ns;
        value["project_wall_ns"] = round.project_wall_ns;
        value["legal_wall_ns"] = round.legal_wall_ns;
        value["total_wall_ns"] = round.total_wall_ns;
        value["accepted"] = round.accepted;
        rounds.append(std::move(value));
    }

    py::dict provenance;
    provenance["solver"] = result.provenance.solver;
    provenance["solver_version"] = result.provenance.solver_version;
    provenance["selected_initialization"] =
        result.provenance.selected_initialization;
    provenance["requested_initialization"] =
        result.provenance.requested_initialization;
    provenance["objective_policy"] = result.provenance.objective_policy;
    provenance["feasibility_policy"] = result.provenance.feasibility_policy;
    provenance["numerical_policy"] = result.provenance.numerical_policy;
    provenance["optimality_claim"] = result.provenance.optimality_claim;
    provenance["deterministic_reduction"] =
        result.provenance.deterministic_reduction;
    provenance["max_epochs"] = result.provenance.max_epochs;
    provenance["min_delta"] = py::make_tuple(
        result.provenance.min_delta.numerator,
        result.provenance.min_delta.denominator);
    provenance["termination_reason"] =
        result.provenance.termination_reason;

    py::dict output;
    output["representatives"] = vector_array(result.representatives);
    output["representative_of"] = vector_array(result.representative_of);
    output["audit"] = std::move(audit);
    output["rounds"] = std::move(rounds);
    output["provenance"] = std::move(provenance);
    return output;
}

}  // namespace

PYBIND11_MODULE(_core, module) {
    module.doc() =
        "Representative Partitioning with Pairwise Admissibility solver";
    module.def(
        "partition_csr",
        [](py::array_t<std::uint64_t,
                       py::array::c_style | py::array::forcecast> offsets,
           py::array_t<std::uint32_t,
                       py::array::c_style | py::array::forcecast> nodes,
           py::array_t<std::uint8_t,
                       py::array::c_style | py::array::forcecast> admissibility,
           const std::string& recall_weight,
           const std::string& min_delta,
           std::uint32_t threads,
           std::uint32_t max_epochs,
           const std::string& initialization) {
            if (offsets.ndim() != 1 || nodes.ndim() != 1 ||
                admissibility.ndim() != 1) {
                throw std::invalid_argument(
                    "offsets, nodes, and admissibility must be one-dimensional");
            }
            reppa::SparseProblemView problem{
                std::span(offsets.data(), static_cast<std::size_t>(offsets.size())),
                std::span(nodes.data(), static_cast<std::size_t>(nodes.size())),
                std::span(
                    admissibility.data(),
                    static_cast<std::size_t>(admissibility.size())),
                static_cast<std::uint64_t>(nodes.size() / 2)};
            reppa::PartitionResult result;
            {
                py::gil_scoped_release release;
                result = reppa::partition(
                    problem,
                    {.recall_weight = recall_weight,
                     .min_delta = min_delta,
                     .threads = threads,
                     .max_epochs = max_epochs,
                     .initialization = initialization});
            }
            return result_dict(result);
        },
        py::arg("offsets"),
        py::arg("nodes"),
        py::arg("admissibility"),
        py::arg("recall_weight") = "1/2",
        py::arg("min_delta") = "1/100",
        py::arg("threads") = 1,
        py::arg("max_epochs") = 5,
        py::arg("initialization") = "asc");
}
