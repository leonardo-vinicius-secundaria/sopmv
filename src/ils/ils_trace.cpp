#include "ils.hpp"

#include "greedy.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <random>
#include <set>
#include <vector>
#include <iostream>

using namespace std;

namespace sopmv {
namespace {

constexpr double kTolerance = 1e-9;

struct State {
    vector<int> sequence;
    vector<int> representatives;
    double distance{};
    double reward{};
};

struct Insertion {
    bool found{false};
    int cluster{-1};
    int node{-1};
    size_t position{};
    double delta{};
    double reward{};
};

vector<int> routeOf(const Instance& instance, const State& state) {
    vector<int> route{instance.depot_node_id};
    route.insert(route.end(), state.representatives.begin(), state.representatives.end());
    route.push_back(instance.depot_node_id);
    return route;
}

double routeDistance(const Instance& instance, const State& state) {
    const auto route = routeOf(instance, state);
    double total = 0.0;
    for (size_t i = 0; i + 1 < route.size(); ++i) {
        total += instance.distanceById(route[i], route[i + 1]);
    }
    return total;
}

template <typename Range>
void printRange(const char* name, const Range& values) {
    cout << "    " << name << " = [";
    bool first = true;
    for (const auto& value : values) {
        if (!first) cout << ", ";
        cout << value;
        first = false;
    }
    cout << "]\n";
}

void printState(const Instance& instance, const State& state, const char* title) {
    cout << "\n[ESTADO] " << title << "\n";
    cout << "    Cada coluna i liga sequence[i] ao representatives[i].\n";
    cout << "    indice          = [";
    for (size_t i = 0; i < state.sequence.size(); ++i) {
        if (i != 0) cout << ", ";
        cout << i;
    }
    cout << "]\n";
    printRange("sequence        (clusters)", state.sequence);
    printRange("representatives (nos)     ", state.representatives);
    printRange("rota: deposito + nos + deposito", routeOf(instance, state));
    cout << "    recompensa=" << state.reward << " distancia=" << state.distance
              << " tmax=" << instance.tmax << "\n";
}

void recompute(const Instance& instance, State& state) {
    state.distance = routeDistance(instance, state);
    state.reward = 0.0;
    for (int id : state.sequence) state.reward += instance.clusterById(id).reward;
}

bool better(const State& lhs, const State& rhs) {
    if (lhs.reward > rhs.reward + kTolerance) return true;
    return fabs(lhs.reward - rhs.reward) <= kTolerance &&
           lhs.distance + kTolerance < rhs.distance;
}

void improveRepresentatives(const Instance& instance, State& state,
                            int64_t& evaluations) {
    bool changed = true;
    while (changed) {
        changed = false;
        for (size_t i = 0; i < state.sequence.size(); ++i) {
            const int previous = i == 0 ? instance.depot_node_id
                                        : state.representatives[i - 1];
            const int next = i + 1 == state.sequence.size() ? instance.depot_node_id
                                                             : state.representatives[i + 1];
            int best_node = state.representatives[i];
            double best_cost = instance.distanceById(previous, best_node) +
                               instance.distanceById(best_node, next);
            for (int node : instance.clusterById(state.sequence[i]).node_ids) {
                ++evaluations;
                const double cost = instance.distanceById(previous, node) +
                                    instance.distanceById(node, next);
                if (cost + kTolerance < best_cost) {
                    best_cost = cost;
                    best_node = node;
                }
            }
            if (best_node != state.representatives[i]) {
                state.representatives[i] = best_node;
                changed = true;
            }
        }
    }
    state.distance = routeDistance(instance, state);
}

void improveTwoOpt(const Instance& instance, State& state, int64_t& evaluations) {
    bool changed = true;
    while (changed && state.sequence.size() >= 2) {
        changed = false;
        const auto route = routeOf(instance, state);
        double best_gain = 0.0;
        size_t best_first = 0, best_last = 0;
        for (size_t first = 1; first + 1 < route.size(); ++first) {
            for (size_t last = first + 1; last + 1 < route.size(); ++last) {
                ++evaluations;
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
        if (best_gain > kTolerance) {
            reverse(state.sequence.begin() + static_cast<ptrdiff_t>(best_first - 1),
                         state.sequence.begin() + static_cast<ptrdiff_t>(best_last));
            reverse(state.representatives.begin() + static_cast<ptrdiff_t>(best_first - 1),
                         state.representatives.begin() + static_cast<ptrdiff_t>(best_last));
            changed = true;
        }
    }
    state.distance = routeDistance(instance, state);
}

Insertion bestInsertion(const Instance& instance, const State& state,
                        const set<int>& excluded, int64_t& evaluations) {
    const auto route = routeOf(instance, state);
    set<int> served(state.sequence.begin(), state.sequence.end());
    Insertion best;
    double best_ratio = -1.0;
    for (const Cluster& cluster : instance.clusters) {
        if (cluster.id == instance.depot_cluster_id || served.count(cluster.id) ||
            excluded.count(cluster.id)) continue;
        for (int node : cluster.node_ids) {
            for (size_t position = 0; position + 1 < route.size(); ++position) {
                ++evaluations;
                const double delta = instance.distanceById(route[position], node) +
                                     instance.distanceById(node, route[position + 1]) -
                                     instance.distanceById(route[position], route[position + 1]);
                if (state.distance + delta > instance.tmax + kTolerance) continue;
                const double ratio = cluster.reward / max(delta, kTolerance);
                if (!best.found || ratio > best_ratio + kTolerance ||
                    (fabs(ratio - best_ratio) <= kTolerance && cluster.reward > best.reward)) {
                    best = {true, cluster.id, node, position, delta, cluster.reward};
                    best_ratio = ratio;
                }
            }
        }
    }
    return best;
}

void insert(State& state, const Insertion& move) {
    state.sequence.insert(state.sequence.begin() + static_cast<ptrdiff_t>(move.position),
                          move.cluster);
    state.representatives.insert(
        state.representatives.begin() + static_cast<ptrdiff_t>(move.position), move.node);
    state.distance += move.delta;
    state.reward += move.reward;
}

void localSearch(const Instance& instance, State& state, const set<int>& initially_excluded,
                 int64_t& evaluations) {
    improveRepresentatives(instance, state, evaluations);
    improveTwoOpt(instance, state, evaluations);
    // Na primeira insercao, evita desfazer imediatamente a perturbacao.
    set<int> excluded = initially_excluded;
    bool first = true;
    while (true) {
        const Insertion move = bestInsertion(instance, state, excluded, evaluations);
        if (!move.found) {
            if (first && !excluded.empty()) {
                excluded.clear();
                first = false;
                continue;
            }
            break;
        }
        insert(state, move);
        excluded.clear();
        first = false;
        improveRepresentatives(instance, state, evaluations);
        improveTwoOpt(instance, state, evaluations);
    }
    recompute(instance, state);
}

set<int> perturb(const Instance& instance, State& state, int strength,
                      mt19937& rng) {
    cout << "[TRACE] perturbacao: inicio clusters=" << state.sequence.size()
              << " forca=" << strength << "\n";
    printState(instance, state, "entrada de perturb");
    vector<size_t> removable;
    printRange("removable:::::::", removable);
    cout << "tamanho da instancia::::" << state.sequence.size() << "\n";
    for (size_t i = 0; i < state.sequence.size(); ++i) {
        const int cluster = state.sequence[i];
        const bool mandatory = instance.mandatory_cluster_ids.count(cluster) != 0;
        cout << "  examina indice=" << i << " cluster=" << cluster
                  << (mandatory ? " -> obrigatorio, nao pode remover\n"
                                : " -> opcional, guarda o INDICE em removable\n");
        if (!mandatory) removable.push_back(i);
    }
    printRange("removable antes de shuffle (indices)", removable);
    shuffle(removable.begin(), removable.end(), rng);
    printRange("removable depois de shuffle", removable);
    cout << "  resize mantem no maximo strength=" << strength << " indices.\n";
    removable.resize(min(removable.size(), static_cast<size_t>(strength)));
    printRange("removable depois de resize", removable);
    cout << "  Ordena indices do maior para o menor para erase nao deslocar"
                 " os indices ainda pendentes.\n";
    sort(removable.rbegin(), removable.rend());
    printRange("removable em ordem decrescente", removable);
    set<int> removed;
    printRange("removed logo apos a declaracao (ainda vazio)", removed);
    for (size_t index : removable) {
        cout << "\n  ERASE indice=" << index << ": remove cluster=" << state.sequence[index]
                  << " e seu no representante=" << state.representatives[index] << "\n"
                  << "  begin()+index localiza o elemento; erase apaga exatamente esse elemento.\n";
        removed.insert(state.sequence[index]);
        state.sequence.erase(state.sequence.begin() + static_cast<ptrdiff_t>(index));
        state.representatives.erase(state.representatives.begin() + static_cast<ptrdiff_t>(index));
        printState(instance, state, "depois deste erase (distancia/recompensa ainda serao recalculadas)");
    }
    printRange("removed (IDs dos clusters, nao indices)", removed);
    if (state.sequence.size() >= 2) {
        uniform_int_distribution<size_t> pick(0, state.sequence.size() - 1);
        cout << "\n  pick e um sorteador uniforme de indices entre 0 e "
                  << state.sequence.size() - 1 << ".\n";
        size_t first = pick(rng), last = pick(rng);
        cout << "  dois sorteios: first=" << first << " last=" << last << "\n";
        if (first > last) swap(first, last);
        cout << "  apos garantir first <= last: first=" << first << " last=" << last << "\n"
                  << "  reverse recebe [begin()+first, begin()+last+1). O parenteses ')'"
                     " indica que last+1 nao entra; assim, last entra.\n";
        printState(instance, state, "antes do reverse aleatorio de perturb");
        reverse(state.sequence.begin() + static_cast<ptrdiff_t>(first),
                     state.sequence.begin() + static_cast<ptrdiff_t>(last + 1));
        reverse(state.representatives.begin() + static_cast<ptrdiff_t>(first),
                     state.representatives.begin() + static_cast<ptrdiff_t>(last + 1));
        printState(instance, state, "depois do reverse aleatorio de perturb");
    } else {
        cout << "  Nao faz reverse: sobraram menos de 2 clusters.\n";
    }
    recompute(instance, state);
    cout << "[TRACE] perturbacao: removeu=" << removed.size()
              << " clusters_restantes=" << state.sequence.size() << "\n";
    printState(instance, state, "saida de perturb, apos recompute");
    return removed;
}

Solution toSolution(const Instance& instance, const State& state, double elapsed,
                    int64_t evaluations, int iterations) {
    Solution solution;
    solution.status = SolveStatus::FeasibleOther;
    solution.solver_status = "ILS iterations=" + to_string(iterations);
    solution.has_incumbent = true;
    solution.objective = state.reward;
    solution.total_distance = state.distance;
    solution.elapsed_seconds = elapsed;
    solution.explored_nodes = evaluations;
    solution.sequence = state.sequence;
    solution.representatives = state.representatives;
    solution.route = routeOf(instance, state);
    solution.mandatory_clusters = instance.mandatory_cluster_ids;
    solution.served_clusters.insert(instance.depot_cluster_id);
    solution.served_clusters.insert(state.sequence.begin(), state.sequence.end());
    solution.visited_nodes.insert(solution.route.begin(), solution.route.end());
    for (size_t i = 0; i + 1 < solution.route.size(); ++i)
        solution.selected_arcs.emplace_back(solution.route[i], solution.route[i + 1]);
    solution.mandatory_satisfied = all_of(
        instance.mandatory_cluster_ids.begin(), instance.mandatory_cluster_ids.end(),
        [&](int id) { return solution.served_clusters.count(id); });
    return solution;
}

}  // namespace

Solution solveILS(const Instance& instance, const ILSOptions& options) {
    const auto start = chrono::steady_clock::now();
    Solution initial = solveGreedy(instance);
    cout << "[TRACE] construcao gulosa: clusters=" << initial.sequence.size()
              << " recompensa=" << initial.objective << " distancia=" << initial.total_distance
              << " viavel=" << (initial.has_incumbent ? "sim" : "nao") << "\n";
    if (!initial.has_incumbent) {
        initial.solver_status = "ILS_NO_FEASIBLE_INITIAL_SOLUTION";
        return initial;
    }
    State best{initial.sequence, initial.representatives, initial.total_distance, initial.objective};
    State current = best;
    int64_t evaluations = 0;
    mt19937 rng(options.seed);
    int iterations = 0;
    for (; iterations < options.max_iterations; ++iterations) {
        const double elapsed = chrono::duration<double>(
            chrono::steady_clock::now() - start).count();
        if (options.time_limit_seconds > 0.0 && elapsed >= options.time_limit_seconds) break;
        State candidate = current;
        printState(instance, candidate, "candidate antes de chamar perturb");
        cout << "[TRACE] iteracao " << iterations + 1 << ": comeca current reward="
                  << current.reward << " distance=" << current.distance << "\n";
        const set<int> removed = perturb(instance, candidate,
                                              options.perturbation_strength, rng);
        localSearch(instance, candidate, removed, evaluations);
        if (better(candidate, best)) best = candidate;
        // Aceita melhora; a cada 20 iteracoes reinicia da melhor solucao.
        if (better(candidate, current)) current = candidate;
        else if ((iterations + 1) % 20 == 0) current = best;
        else current = candidate;  // caminhada permite atravessar otimos locais.
        cout << "[TRACE] iteracao " << iterations + 1 << ": best reward="
                  << best.reward << " distance=" << best.distance << "\n";
    }
    const double elapsed = chrono::duration<double>(
        chrono::steady_clock::now() - start).count();
    return toSolution(instance, best, elapsed, evaluations, iterations);
}

}  // namespace sopmv

