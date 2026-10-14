#include "ils.hpp"
#include "instance.hpp"
#include "solution_validator.hpp"

#include <cassert>
#include <filesystem>
#include <iostream>

#ifndef TEST_SOURCE_DIR
#error TEST_SOURCE_DIR must be defined
#endif

int main() {
    const auto path = (std::filesystem::path(TEST_SOURCE_DIR) / "tests/data/small.sop").string();
    sopmv::ILSOptions options;
    options.max_iterations = 100;
    options.time_limit_seconds = 1.0;
    options.seed = 42;

    auto sop = sopmv::readInstance(path);
    auto solution = sopmv::solveILS(sop, options);
    assert(solution.has_incumbent);
    assert(sopmv::validateSolution(sop, solution).valid);

    auto sopmv = sopmv::readInstance(path);
    sopmv::applyMandatorySets(sopmv, {1});
    solution = sopmv::solveILS(sopmv, options);
    assert(solution.has_incumbent);
    assert(solution.mandatory_satisfied);
    assert(sopmv::validateSolution(sopmv, solution).valid);

    auto infeasible = sopmv::readInstance(path);
    sopmv::applyMandatorySets(infeasible, {1, 2});
    solution = sopmv::solveILS(infeasible, options);
    assert(!solution.has_incumbent);
    std::cout << "test_ils: OK\n";
}
