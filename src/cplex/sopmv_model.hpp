#pragma once

#include "instance.hpp"
#include "solution.hpp"

namespace sopmv {

struct SolverOptions {
    double time_limit_seconds{3600.0};
    int threads{1};
    double mip_gap{0.0};
    int random_seed{0};
    int log_level{2};
};

Solution solveExact(const Instance& instance, const SolverOptions& options);

// Variante branch-and-cut: substitui o fluxo das restricoes (7)-(8) por
// restricoes de eliminacao de subciclos adicionadas sob demanda.
Solution solveExactBranchAndCut(const Instance& instance, const SolverOptions& options);

}  // namespace sopmv
