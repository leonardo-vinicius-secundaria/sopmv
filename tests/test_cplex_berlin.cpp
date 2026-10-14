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
    const auto instance = sopmv::readInstance((source / "data/berlin52/sop/11berlin52_T40_p1.sop").string());
    assert(instance.tmax == 1616.0);
    assert(instance.mandatory_cluster_ids.empty());

    sopmv::SolverOptions options;
    options.time_limit_seconds = 600.0;
    options.threads = 1;
    options.mip_gap = 0.0;
    options.random_seed = 202601;
    options.log_level = 0;
    const auto solution = sopmv::solveExact(instance, options);
    assert(solution.status == sopmv::SolveStatus::Optimal);
    assert(solution.has_incumbent);
    assert(std::fabs(solution.objective - 37.0) < 1e-6);
    assert(solution.relative_gap <= 1e-9);
    assert(sopmv::validateSolution(instance, solution).valid);
    std::cout << "test_cplex_berlin: OK; objective=" << solution.objective
              << "; distance=" << solution.total_distance << '\n';
}
