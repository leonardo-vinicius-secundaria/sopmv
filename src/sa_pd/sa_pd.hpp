#pragma once

#include "instance.hpp"
#include "solution.hpp"

#include <cstdint>
#include <vector>

namespace sopmv {

struct SAOptions {
    double initial_temperature{16.0};
    double cooling_factor{0.93};
    int iterations_per_temperature{80000};
    // Zero usa o padrao do artigo: 1.5 * numero de conjuntos lucrativos.
    double time_limit_seconds{0.0};
    std::uint32_t seed{202601U};
};

// Resolve SOP/SOPMV com simulated annealing e avaliacao por programacao dinamica.
// A busca nao chama o CPLEX.
Solution solveSA(const Instance& instance, const SAOptions& options);

}  // namespace sopmv
