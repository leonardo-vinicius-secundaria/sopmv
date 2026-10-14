#include "sa_pd.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <random>
#include <set>
#include <stdexcept>
#include <unordered_set>

namespace sopmv {
namespace {

constexpr double kMissingMandatoryPenalty = 999.0;

struct Evaluation {
    double distance{0.0};
    double reward{0.0};
    double score{0.0};
    bool feasible{false};
    int missing_mandatory{0};
    std::vector<int> sequence;
    std::vector<int> representatives;
    std::vector<int> route;
    std::set<int> served_clusters;
};

bool betterSearchState(const Evaluation& lhs, const Evaluation& rhs) {
    if (lhs.missing_mandatory != rhs.missing_mandatory) {
        return lhs.missing_mandatory < rhs.missing_mandatory;
    }
    if (lhs.score != rhs.score) return lhs.score > rhs.score;
    return lhs.distance < rhs.distance;
}

bool betterFeasible(const Evaluation& lhs, const Evaluation& rhs, bool have_rhs) {
    if (!have_rhs) return true;
    if (lhs.reward != rhs.reward) return lhs.reward > rhs.reward;
    return lhs.distance < rhs.distance;
}

Evaluation evaluateByDynamicProgramming(const Instance& instance,
                                        const std::vector<int>& sequence) {
    Evaluation result;
    result.sequence = sequence;
    result.route = {instance.depot_node_id};
    result.served_clusters.insert(instance.depot_cluster_id);

    std::unordered_set<int> seen;
    for (int cluster_id : sequence) {
        if (cluster_id == instance.depot_cluster_id ||
            !instance.cluster_index.count(cluster_id) || !seen.insert(cluster_id).second) {
            throw std::invalid_argument("sequencia contem conjunto invalido ou repetido");
        }
    }

    const double infinity = std::numeric_limits<double>::infinity();
    std::vector<double> previous;
    std::vector<std::vector<int>> predecessors;
    std::vector<int> best_representatives;
    double best_distance = 0.0;
    int best_prefix = 0;

    // O prefixo vazio e sempre uma rota valida (deposito -> deposito).
    for (std::size_t stage = 0; stage < sequence.size(); ++stage) {
        const Cluster& cluster = instance.clusterById(sequence[stage]);
        std::vector<double> current(cluster.node_ids.size(), infinity);
        std::vector<int> predecessor(cluster.node_ids.size(), -1);
        if (stage == 0) {
            for (std::size_t j = 0; j < cluster.node_ids.size(); ++j) {
                current[j] = instance.distanceById(instance.depot_node_id, cluster.node_ids[j]);
            }
        } else {
            const Cluster& previous_cluster = instance.clusterById(sequence[stage - 1]);
            for (std::size_t j = 0; j < cluster.node_ids.size(); ++j) {
                for (std::size_t i = 0; i < previous_cluster.node_ids.size(); ++i) {
                    const double candidate = previous[i] +
                        instance.distanceById(previous_cluster.node_ids[i], cluster.node_ids[j]);
                    if (candidate < current[j]) {
                        current[j] = candidate;
                        predecessor[j] = static_cast<int>(i);
                    }
                }
            }
        }
        predecessors.push_back(predecessor);
        previous = current;

        double prefix_distance = infinity;
        int final_index = -1;
        for (std::size_t j = 0; j < cluster.node_ids.size(); ++j) {
            const double candidate = current[j] +
                instance.distanceById(cluster.node_ids[j], instance.depot_node_id);
            if (candidate < prefix_distance) {
                prefix_distance = candidate;
                final_index = static_cast<int>(j);
            }
        }
        if (prefix_distance <= instance.tmax + 1e-9 && final_index >= 0) {
            best_prefix = static_cast<int>(stage + 1);
            best_distance = prefix_distance;
            best_representatives.assign(static_cast<std::size_t>(best_prefix), -1);
            int index = final_index;
            for (int s = best_prefix - 1; s >= 0; --s) {
                const Cluster& selected_cluster = instance.clusterById(sequence[static_cast<std::size_t>(s)]);
                best_representatives[static_cast<std::size_t>(s)] =
                    selected_cluster.node_ids[static_cast<std::size_t>(index)];
                index = predecessors[static_cast<std::size_t>(s)][static_cast<std::size_t>(index)];
            }
        }
    }

    result.distance = best_distance;
    result.representatives = best_representatives;
    result.route.clear();
    if (best_prefix > 0) result.route.push_back(instance.depot_node_id);
    for (int node_id : best_representatives) result.route.push_back(node_id);
    result.route.push_back(instance.depot_node_id);
    for (int i = 0; i < best_prefix; ++i) {
        const int cluster_id = sequence[static_cast<std::size_t>(i)];
        const Cluster& cluster = instance.clusterById(cluster_id);
        result.reward += cluster.reward;
        result.served_clusters.insert(cluster_id);
    }
    for (int mandatory_id : instance.mandatory_cluster_ids) {
        if (!result.served_clusters.count(mandatory_id)) ++result.missing_mandatory;
    }
    result.score = result.reward - kMissingMandatoryPenalty * result.missing_mandatory;
    result.feasible = result.missing_mandatory == 0 && result.distance <= instance.tmax + 1e-9;
    return result;
}

std::vector<int> makeInitialSequence(const Instance& instance) {
    std::vector<int> sequence(instance.mandatory_cluster_ids.begin(),
                               instance.mandatory_cluster_ids.end());
    std::vector<int> optional;
    for (const Cluster& cluster : instance.clusters) {
        if (cluster.id != instance.depot_cluster_id &&
            !instance.mandatory_cluster_ids.count(cluster.id)) {
            optional.push_back(cluster.id);
        }
    }
    std::sort(optional.begin(), optional.end());
    sequence.insert(sequence.end(), optional.begin(), optional.end());
    return sequence;
}

void improveMandatoryOrder(const Instance& instance, std::vector<int>& sequence,
                           Evaluation& current) {
    const std::size_t mandatory_count = instance.mandatory_cluster_ids.size();
    for (std::size_t i = 0; i < mandatory_count; ++i) {
        for (std::size_t j = i + 1; j < mandatory_count; ++j) {
            std::swap(sequence[i], sequence[j]);
            Evaluation candidate = evaluateByDynamicProgramming(instance, sequence);
            if (betterSearchState(candidate, current)) {
                current = std::move(candidate);
            } else {
                std::swap(sequence[i], sequence[j]);
            }
        }
    }
}

void makeNeighbor(std::vector<int>& sequence, std::mt19937& generator,
                  bool mandatory_only, std::size_t mandatory_count) {
    const std::size_t limit = mandatory_only ? mandatory_count : sequence.size();
    if (limit < 2) return;
    std::uniform_int_distribution<std::size_t> position(0, limit - 1);
    std::size_t first = position(generator);
    std::size_t second = position(generator);
    while (second == first) second = position(generator);
    std::uniform_int_distribution<int> move(0, 2);
    switch (move(generator)) {
        case 0: {  // insertion
            const int value = sequence[first];
            sequence.erase(sequence.begin() + static_cast<std::ptrdiff_t>(first));
            sequence.insert(sequence.begin() + static_cast<std::ptrdiff_t>(second), value);
            break;
        }
        case 1:  // swap
            std::swap(sequence[first], sequence[second]);
            break;
        default:  // reversal
            if (first > second) std::swap(first, second);
            std::reverse(sequence.begin() + static_cast<std::ptrdiff_t>(first),
                         sequence.begin() + static_cast<std::ptrdiff_t>(second + 1));
            break;
    }
}

void fillSolutionFromEvaluation(Solution& solution, const Evaluation& evaluation,
                                std::int64_t iterations, double elapsed) {
    solution.status = SolveStatus::FeasibleOther;
    solution.solver_status = "SA_PD";
    solution.has_incumbent = true;
    solution.objective = evaluation.reward;
    solution.total_distance = evaluation.distance;
    solution.elapsed_seconds = elapsed;
    solution.explored_nodes = iterations;
    solution.route = evaluation.route;
    solution.sequence = evaluation.sequence;
    solution.representatives = evaluation.representatives;
    solution.served_clusters = evaluation.served_clusters;
    solution.mandatory_satisfied = evaluation.missing_mandatory == 0;
    solution.visited_nodes.insert(evaluation.route.begin(), evaluation.route.end());
    for (std::size_t i = 0; i + 1 < evaluation.route.size(); ++i) {
        solution.selected_arcs.emplace_back(evaluation.route[i], evaluation.route[i + 1]);
    }
}

}  // namespace

Solution solveSA(const Instance& instance, const SAOptions& options) {
    if (options.initial_temperature <= 0.0) {
        throw std::invalid_argument("sa-temperature deve ser positivo");
    }
    if (options.cooling_factor <= 0.0 || options.cooling_factor >= 1.0) {
        throw std::invalid_argument("sa-alpha deve estar entre 0 e 1");
    }
    if (options.iterations_per_temperature <= 0) {
        throw std::invalid_argument("sa-iterations deve ser positivo");
    }
    const double time_limit = options.time_limit_seconds > 0.0
        ? options.time_limit_seconds
        : 1.5 * static_cast<double>(std::max<std::size_t>(1, instance.clusters.size() - 1));

    std::vector<int> current_sequence = makeInitialSequence(instance);
    Evaluation current = evaluateByDynamicProgramming(instance, current_sequence);
    improveMandatoryOrder(instance, current_sequence, current);

    Evaluation best;
    bool have_best = false;
    if (current.feasible) {
        best = current;
        have_best = true;
    }

    std::mt19937 generator(options.seed);
    const auto start = std::chrono::steady_clock::now();
    std::int64_t iterations = 0;
    double temperature = options.initial_temperature;
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < time_limit) {
        for (int step = 0; step < options.iterations_per_temperature; ++step) {
            if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() >= time_limit) {
                break;
            }
            std::vector<int> candidate_sequence = current_sequence;
            makeNeighbor(candidate_sequence, generator, !have_best,
                         instance.mandatory_cluster_ids.size());
            Evaluation candidate = evaluateByDynamicProgramming(instance, candidate_sequence);
            const double delta = candidate.score - current.score;
            bool accept = delta >= 0.0;
            if (!accept && temperature > 0.0) {
                // delta = novo - atual; isto corrige a inconsistência de sinal do pseudocodigo do artigo.
                const double probability = std::exp(delta / temperature);
                std::uniform_real_distribution<double> unit(0.0, 1.0);
                accept = unit(generator) < probability;
            }
            if (accept) {
                current_sequence = std::move(candidate_sequence);
                current = std::move(candidate);
                if (current.feasible && betterFeasible(current, best, have_best)) {
                    best = current;
                    have_best = true;
                }
            }
            ++iterations;
        }
        temperature *= options.cooling_factor;
        if (!std::isfinite(temperature) || temperature < 1e-12) temperature = 1e-12;
    }

    Solution solution;
    solution.mandatory_clusters = instance.mandatory_cluster_ids;
    solution.elapsed_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    solution.explored_nodes = iterations;
    if (have_best) {
        fillSolutionFromEvaluation(solution, best, iterations, solution.elapsed_seconds);
    } else {
        solution.status = SolveStatus::NoFeasibleSolution;
        solution.solver_status = "SA_PD";
        solution.has_incumbent = false;
    }
    return solution;
}

}  // namespace sopmv
