#include "instance.hpp"
#include "solution.hpp"
#include "solution_validator.hpp"

#include <cassert>
#include <filesystem>
#include <iostream>

#ifndef TEST_SOURCE_DIR
#error TEST_SOURCE_DIR must be defined
#endif

namespace {

sopmv::Solution knownSolution() {
    sopmv::Solution solution;
    solution.status = sopmv::SolveStatus::Optimal;
    solution.has_incumbent = true;
    solution.objective = 8.0;
    solution.route = {1, 3, 1};
    solution.visited_nodes = {1, 3};
    solution.served_clusters = {0, 2};
    solution.selected_arcs = {{1, 3}, {3, 1}};
    return solution;
}

}  // namespace

int main() {
    const std::filesystem::path source(TEST_SOURCE_DIR);
    auto instance = sopmv::readInstance((source / "tests/data/small.sop").string());

    auto solution = knownSolution();
    const auto valid = sopmv::validateSolution(instance, solution);
    assert(valid.valid);
    assert(valid.distance == 4.0);
    assert(valid.reward == 8.0);

    auto disconnected = solution;
    disconnected.selected_arcs.emplace_back(2, 3);
    assert(!sopmv::validateSolution(instance, disconnected).valid);

    auto overcounted = solution;
    overcounted.objective = 16.0;
    assert(!sopmv::validateSolution(instance, overcounted).valid);

    sopmv::applyMandatorySets(instance, {1});
    const auto missing_mandatory = sopmv::validateSolution(instance, solution);
    assert(!missing_mandatory.valid);

    std::cout << "test_small_instance: OK\n";
}
