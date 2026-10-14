#pragma once

#include "instance.hpp"
#include "solution.hpp"

#include <string>

namespace sopmv {

struct ValidationResult {
    bool valid{false};
    double distance{};
    double reward{};
    std::set<int> visited_nodes;
    std::set<int> served_clusters;
    std::string message;
};

ValidationResult validateSolution(const Instance& instance,
                                  const Solution& solution,
                                  double tolerance = 1e-6);

}  // namespace sopmv
