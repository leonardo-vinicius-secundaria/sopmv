#include "greedy.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <limits>
#include <set>
#include <utility>
#include <vector>

namespace sopmv {
namespace {

constexpr double kTolerance = 1e-9;

struct Candidate {
    bool found{false};
    int cluster_id{-1};
    int node_id{-1};
    std::size_t position{};
    double delta{std::numeric_limits<double>::infinity()};
    double reward{};
};

double routeDistance(const Instance& instance, const std::vector<int>& route) {
    double distance = 0.0;
    for (std::size_t i = 0; i + 1 < route.size(); ++i) {
        distance += instance.distanceById(route[i], route[i + 1]);
    }
    return distance;
}

double insertionDelta(const Instance& instance, const std::vector<int>& route,
                      std::size_t position, int node_id) {
    const int from = route[position];
    const int to = route[position + 1];
    return instance.distanceById(from, node_id) + instance.distanceById(node_id, to) -
           instance.distanceById(from, to);
}

bool betterMandatory(const Candidate& candidate, const Candidate& best) {
    if (!best.found) return true;
    if (std::fabs(candidate.delta - best.delta) > kTolerance) {
        return candidate.delta < best.delta;
    }
    if (candidate.cluster_id != best.cluster_id) return candidate.cluster_id < best.cluster_id;
    if (candidate.node_id != best.node_id) return candidate.node_id < best.node_id;
    return candidate.position < best.position;
}

bool betterOptional(const Candidate& candidate, const Candidate& best) {
    if (!best.found) return true;
    const double candidate_denominator = std::max(candidate.delta, kTolerance);
    const double best_denominator = std::max(best.delta, kTolerance);
    const double candidate_ratio = candidate.reward / candidate_denominator;
    const double best_ratio = best.reward / best_denominator;
    if (std::fabs(candidate_ratio - best_ratio) > kTolerance) {
        return candidate_ratio > best_ratio;
    }
    if (std::fabs(candidate.reward - best.reward) > kTolerance) {
        return candidate.reward > best.reward;
    }
    if (std::fabs(candidate.delta - best.delta) > kTolerance) {
        return candidate.delta < best.delta;
    }
    if (candidate.cluster_id != best.cluster_id) return candidate.cluster_id < best.cluster_id;
    if (candidate.node_id != best.node_id) return candidate.node_id < best.node_id;
    return candidate.position < best.position;
}

Candidate bestInsertion(const Instance& instance, const std::vector<int>& route,
                        const std::set<int>& eligible, double current_distance,
                        bool mandatory_phase, std::int64_t& evaluations) {
    Candidate best;
    for (int cluster_id : eligible) {
        const Cluster& cluster = instance.clusterById(cluster_id);
        for (int node_id : cluster.node_ids) {
            for (std::size_t position = 0; position + 1 < route.size(); ++position) {
                ++evaluations;
                Candidate candidate;
                candidate.found = true;
                candidate.cluster_id = cluster_id;
                candidate.node_id = node_id;
                candidate.position = position;
                candidate.delta = insertionDelta(instance, route, position, node_id);
                candidate.reward = cluster.reward;
                if (current_distance + candidate.delta > instance.tmax + kTolerance) continue;
                if ((mandatory_phase && betterMandatory(candidate, best)) ||
                    (!mandatory_phase && betterOptional(candidate, best))) {
                    best = candidate;
                }
            }
        }
    }
    return best;
}

void applyInsertion(std::vector<int>& route, std::vector<int>& sequence,
                    std::vector<int>& representatives, const Candidate& candidate) {
    const auto route_position = route.begin() + static_cast<std::ptrdiff_t>(candidate.position + 1);
    route.insert(route_position, candidate.node_id);
    const auto sequence_position = sequence.begin() + static_cast<std::ptrdiff_t>(candidate.position);
    sequence.insert(sequence_position, candidate.cluster_id);
    const auto representative_position =
        representatives.begin() + static_cast<std::ptrdiff_t>(candidate.position);
    representatives.insert(representative_position, candidate.node_id);
}

bool improveRepresentatives(const Instance& instance, const std::vector<int>& sequence,
                            std::vector<int>& representatives, std::vector<int>& route) {
    bool improved = false;
    for (std::size_t i = 0; i < sequence.size(); ++i) {
        const int previous = route[i];
        const int next = route[i + 2];
        int best_node = route[i + 1];
        double best_cost = instance.distanceById(previous, best_node) +
                           instance.distanceById(best_node, next);
        for (int node_id : instance.clusterById(sequence[i]).node_ids) {
            const double cost = instance.distanceById(previous, node_id) +
                                instance.distanceById(node_id, next);
            if (cost + kTolerance < best_cost ||
                (std::fabs(cost - best_cost) <= kTolerance && node_id < best_node)) {
                best_cost = cost;
                best_node = node_id;
            }
        }
        if (best_node != route[i + 1]) {
            route[i + 1] = best_node;
            representatives[i] = best_node;
            improved = true;
        }
    }
    return improved;
}

bool improveTwoOpt(const Instance& instance, std::vector<int>& route,
                   std::vector<int>& sequence, std::vector<int>& representatives) {
    if (sequence.size() < 2) return false;
    double best_gain = 0.0;
    std::size_t best_first = 0;
    std::size_t best_last = 0;
    for (std::size_t first = 1; first + 1 < route.size(); ++first) {
        for (std::size_t last = first + 1; last + 1 < route.size(); ++last) {
            const double old_edges = instance.distanceById(route[first - 1], route[first]) +
                                     instance.distanceById(route[last], route[last + 1]);
            const double new_edges = instance.distanceById(route[first - 1], route[last]) +
                                     instance.distanceById(route[first], route[last + 1]);
            const double gain = old_edges - new_edges;
            if (gain > best_gain + kTolerance) {
                best_gain = gain;
                best_first = first;
                best_last = last;
            }
        }
    }
    if (best_gain <= kTolerance) return false;
    std::reverse(route.begin() + static_cast<std::ptrdiff_t>(best_first),
                 route.begin() + static_cast<std::ptrdiff_t>(best_last + 1));
    std::reverse(sequence.begin() + static_cast<std::ptrdiff_t>(best_first - 1),
                 sequence.begin() + static_cast<std::ptrdiff_t>(best_last));
    std::reverse(representatives.begin() + static_cast<std::ptrdiff_t>(best_first - 1),
                 representatives.begin() + static_cast<std::ptrdiff_t>(best_last));
    return true;
}

void localImprove(const Instance& instance, std::vector<int>& route,
                  std::vector<int>& sequence, std::vector<int>& representatives) {
    bool changed = true;
    while (changed) {
        changed = improveRepresentatives(instance, sequence, representatives, route);
        if (improveTwoOpt(instance, route, sequence, representatives)) changed = true;
    }
}

void fillSolution(Solution& solution, const Instance& instance,
                  const std::vector<int>& route, const std::vector<int>& sequence,
                  const std::vector<int>& representatives, double elapsed,
                  std::int64_t evaluations) {
    solution.status = SolveStatus::FeasibleOther;
    solution.solver_status = "GREEDY_INSERTION";
    solution.has_incumbent = true;
    solution.elapsed_seconds = elapsed;
    solution.explored_nodes = evaluations;
    solution.sequence = sequence;
    solution.representatives = representatives;
    solution.route = sequence.empty() ? std::vector<int>{instance.depot_node_id} : route;
    solution.total_distance = sequence.empty() ? 0.0 : routeDistance(instance, route);
    solution.objective = 0.0;
    solution.served_clusters.insert(instance.depot_cluster_id);
    for (int cluster_id : sequence) {
        solution.objective += instance.clusterById(cluster_id).reward;
        solution.served_clusters.insert(cluster_id);
    }
    solution.visited_nodes.insert(solution.route.begin(), solution.route.end());
    for (std::size_t i = 0; i + 1 < solution.route.size(); ++i) {
        solution.selected_arcs.emplace_back(solution.route[i], solution.route[i + 1]);
    }
    solution.mandatory_satisfied = std::all_of(
        instance.mandatory_cluster_ids.begin(), instance.mandatory_cluster_ids.end(),
        [&](int id) { return solution.served_clusters.count(id) != 0; });
}

}  // namespace

Solution solveGreedy(const Instance& instance) {
    const auto start = std::chrono::steady_clock::now();
    std::vector<int> route{instance.depot_node_id, instance.depot_node_id};
    std::vector<int> sequence;
    std::vector<int> representatives;
    std::set<int> remaining_mandatory = instance.mandatory_cluster_ids;
    std::set<int> remaining_optional;
    for (const Cluster& cluster : instance.clusters) {
        if (cluster.id != instance.depot_cluster_id &&
            !remaining_mandatory.count(cluster.id)) {
            remaining_optional.insert(cluster.id);
        }
    }

    std::int64_t evaluations = 0;
    double distance = 0.0;
    while (!remaining_mandatory.empty()) {
        const Candidate candidate = bestInsertion(instance, route, remaining_mandatory,
                                                  distance, true, evaluations);
        if (!candidate.found) {
            Solution solution;
            solution.status = SolveStatus::NoFeasibleSolution;
            solution.solver_status = "GREEDY_NO_FEASIBLE_CONSTRUCTION";
            solution.mandatory_clusters = instance.mandatory_cluster_ids;
            solution.elapsed_seconds = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - start).count();
            solution.explored_nodes = evaluations;
            return solution;
        }
        applyInsertion(route, sequence, representatives, candidate);
        remaining_mandatory.erase(candidate.cluster_id);
        localImprove(instance, route, sequence, representatives);
        distance = routeDistance(instance, route);
    }

    while (!remaining_optional.empty()) {
        const Candidate candidate = bestInsertion(instance, route, remaining_optional,
                                                  distance, false, evaluations);
        if (!candidate.found) break;
        applyInsertion(route, sequence, representatives, candidate);
        remaining_optional.erase(candidate.cluster_id);
        localImprove(instance, route, sequence, representatives);
        distance = routeDistance(instance, route);
    }

    Solution solution;
    solution.mandatory_clusters = instance.mandatory_cluster_ids;
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
    fillSolution(solution, instance, route, sequence, representatives, elapsed, evaluations);
    return solution;
}

}  // namespace sopmv
