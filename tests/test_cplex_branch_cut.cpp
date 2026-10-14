#include "instance.hpp"
#include "solution_validator.hpp"
#include "sopmv_model.hpp"

#include <cassert>
#include <cmath>
#include <filesystem>
#include <iostream>

#ifndef TEST_SOURCE_DIR
#error TEST_SOURCE_DIR must be defined
#endif

int main() {
    const std::filesystem::path source(TEST_SOURCE_DIR);
    auto instance = sopmv::readInstance((source / "tests/data/small.sop").string());
    sopmv::SolverOptions options;
    options.time_limit_seconds = 60.0;
    options.threads = 1;
    options.mip_gap = 0.0;
    options.random_seed = 202601;
    options.log_level = 0;

    const auto sop = sopmv::solveExactBranchAndCut(instance, options);
    assert(sop.status == sopmv::SolveStatus::Optimal);
    assert(sop.has_incumbent);
    assert(std::fabs(sop.objective - 8.0) < 1e-6);
    assert(sopmv::validateSolution(instance, sop).valid);

    sopmv::applyMandatorySets(instance, {1});
    const auto sopmv = sopmv::solveExactBranchAndCut(instance, options);
    assert(sopmv.status == sopmv::SolveStatus::Optimal);
    assert(std::fabs(sopmv.objective - 5.0) < 1e-6);
    assert(sopmv::validateSolution(instance, sopmv).valid);

    sopmv::applyMandatorySets(instance, {1, 2});
    const auto infeasible = sopmv::solveExactBranchAndCut(instance, options);
    assert(infeasible.status == sopmv::SolveStatus::Infeasible);
    assert(!infeasible.has_incumbent);

    std::cout << "test_cplex_branch_cut: OK\n";
}
