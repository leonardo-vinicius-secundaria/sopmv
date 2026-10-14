#pragma once

#include "instance.hpp"
#include "solution.hpp"

#include <cstdint>

namespace sopmv {

struct ILSOptions {
    int max_iterations{10000};
    int perturbation_strength{2};
    double time_limit_seconds{10.0};
    std::uint32_t seed{202601};
};

// Iterated Local Search: construcao gulosa, busca local, perturbacao e
// reinicio da busca local, mantendo sempre a melhor solucao encontrada.
Solution solveILS(const Instance& instance, const ILSOptions& options = {});

}  // namespace sopmv
