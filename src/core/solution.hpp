#pragma once

#include <cstdint>
#include <limits>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace sopmv {

enum class SolveStatus {
    Optimal,
    FeasibleTimeLimit,
    FeasibleOther,
    Infeasible,
    NoFeasibleSolution,
    Error
};

inline const char* statusName(SolveStatus status) {
    switch (status) {
        case SolveStatus::Optimal: return "Optimal";
        case SolveStatus::FeasibleTimeLimit: return "FeasibleTimeLimit";
        case SolveStatus::FeasibleOther: return "Feasible";
        case SolveStatus::Infeasible: return "Infeasible";
        case SolveStatus::NoFeasibleSolution: return "NoFeasibleSolution";
        case SolveStatus::Error: return "Error";
    }
    return "Error";
}

struct Solution {
    SolveStatus status{SolveStatus::Error};
    std::string solver_status;
    bool has_incumbent{false};
    double objective{std::numeric_limits<double>::quiet_NaN()};
    double best_bound{std::numeric_limits<double>::quiet_NaN()};
    double relative_gap{std::numeric_limits<double>::quiet_NaN()};
    double elapsed_seconds{};
    std::int64_t explored_nodes{};
    double total_distance{std::numeric_limits<double>::quiet_NaN()};
    std::vector<int> route;
    // Ordem de conjuntos usada pelo metodo (o CPLEX pode deixar este campo vazio).
    std::vector<int> sequence;
    std::vector<int> representatives;
    std::set<int> visited_nodes;
    std::set<int> served_clusters;
    std::set<int> mandatory_clusters;
    std::vector<std::pair<int, int>> selected_arcs;
    bool mandatory_satisfied{false};
    bool valid{false};
    std::string validation_message;
};

}  // namespace sopmv
