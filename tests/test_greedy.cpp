#include "greedy.hpp"
#include "instance.hpp"
#include "solution_validator.hpp"

#include <cassert>
#include <filesystem>
#include <iostream>

#ifndef TEST_SOURCE_DIR
#error TEST_SOURCE_DIR must be defined
#endif

int main() {
    const std::filesystem::path source(TEST_SOURCE_DIR);
    const std::string path = (source / "tests/data/small.sop").string();

    auto sop = sopmv::readInstance(path);
    auto sop_solution = sopmv::solveGreedy(sop);
    assert(sop_solution.has_incumbent);
    assert(sopmv::validateSolution(sop, sop_solution).valid);

    auto feasible_sopmv = sopmv::readInstance(path);
    sopmv::applyMandatorySets(feasible_sopmv, {1});
    auto feasible_solution = sopmv::solveGreedy(feasible_sopmv);
    assert(feasible_solution.has_incumbent);
    assert(feasible_solution.mandatory_satisfied);
    assert(sopmv::validateSolution(feasible_sopmv, feasible_solution).valid);

    auto infeasible_sopmv = sopmv::readInstance(path);
    sopmv::applyMandatorySets(infeasible_sopmv, {1, 2});
    auto infeasible_solution = sopmv::solveGreedy(infeasible_sopmv);
    assert(!infeasible_solution.has_incumbent);
    assert(infeasible_solution.status == sopmv::SolveStatus::NoFeasibleSolution);

    std::cout << "test_greedy: OK\n";
}
