#include "sopmv_model.hpp"

#include <ilcplex/ilocplex.h>
ILOSTLBEGIN

#include <cmath>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace sopmv {
namespace {

std::string solverStatusText(IloCplex& cplex) {
    std::ostringstream output;
    output << cplex.getStatus() << " (CPLEX code "
           << static_cast<int>(cplex.getCplexStatus()) << ')';
    return output.str();
}

// Em uma solucao inteira, as restricoes de grau decompoem os vertices
// visitados em ciclos dirigidos disjuntos. Para cada ciclo que nao contem o
// deposito, adiciona sum_{i,j em S} x_ij <= |S| - 1.
ILOLAZYCONSTRAINTCALLBACK5(SubtourEliminationCallback,
                           IloBoolVarArray, x,
                           IloIntArray, arc_from,
                           IloIntArray, arc_to,
                           IloInt, node_count,
                           IloInt, depot) {
    IloNumArray values(getEnv());
    getValues(values, x);

    std::vector<IloInt> successor(static_cast<std::size_t>(node_count), -1);
    std::vector<bool> selected(static_cast<std::size_t>(node_count), false);
    for (IloInt a = 0; a < x.getSize(); ++a) {
        if (values[a] > 0.5) {
            successor[static_cast<std::size_t>(arc_from[a])] = arc_to[a];
            selected[static_cast<std::size_t>(arc_from[a])] = true;
            selected[static_cast<std::size_t>(arc_to[a])] = true;
        }
    }

    std::vector<bool> processed(static_cast<std::size_t>(node_count), false);
    for (IloInt start = 0; start < node_count; ++start) {
        if (!selected[static_cast<std::size_t>(start)] ||
            processed[static_cast<std::size_t>(start)]) {
            continue;
        }

        std::vector<IloInt> cycle;
        IloInt current = start;
        while (current >= 0 && !processed[static_cast<std::size_t>(current)]) {
            processed[static_cast<std::size_t>(current)] = true;
            cycle.push_back(current);
            current = successor[static_cast<std::size_t>(current)];
        }

        bool contains_depot = false;
        std::vector<bool> in_cycle(static_cast<std::size_t>(node_count), false);
        for (IloInt node : cycle) {
            in_cycle[static_cast<std::size_t>(node)] = true;
            if (node == depot) contains_depot = true;
        }
        if (contains_depot || cycle.empty()) continue;

        IloExpr internal_arcs(getEnv());
        for (IloInt a = 0; a < x.getSize(); ++a) {
            if (in_cycle[static_cast<std::size_t>(arc_from[a])] &&
                in_cycle[static_cast<std::size_t>(arc_to[a])]) {
                internal_arcs += x[a];
            }
        }
        add(internal_arcs <= static_cast<IloNum>(cycle.size() - 1));
        internal_arcs.end();
    }
    values.end();
}

}  // namespace

Solution solveExactBranchAndCut(const Instance& instance, const SolverOptions& options) {
    if (options.time_limit_seconds <= 0.0) throw std::invalid_argument("time-limit deve ser positivo");
    if (options.threads <= 0) throw std::invalid_argument("threads deve ser positivo");
    if (options.mip_gap < 0.0) throw std::invalid_argument("mip-gap nao pode ser negativo");
    if (options.log_level < 0 || options.log_level > 5) {
        throw std::invalid_argument("log-level deve estar entre 0 e 5");
    }

    IloEnv env;
    Solution solution;
    try {
        const IloInt n = static_cast<IloInt>(instance.nodes.size());
        const IloInt cluster_count = static_cast<IloInt>(instance.clusters.size());
        const IloInt depot = static_cast<IloInt>(instance.node_index.at(instance.depot_node_id));

        IloIntArray arc_from(env);
        IloIntArray arc_to(env);
        std::vector<std::vector<IloInt>> arc_index(
            static_cast<std::size_t>(n), std::vector<IloInt>(static_cast<std::size_t>(n), -1));
        for (IloInt i = 0; i < n; ++i) {
            for (IloInt j = 0; j < n; ++j) {
                if (i == j) continue;
                arc_index[static_cast<std::size_t>(i)][static_cast<std::size_t>(j)] = arc_from.getSize();
                arc_from.add(i);
                arc_to.add(j);
            }
        }

        IloModel model(env, "SOP-SOPMV-Branch-and-Cut");
        IloBoolVarArray x(env, arc_from.getSize());
        IloBoolVarArray y(env, n);
        IloBoolVarArray z(env, cluster_count);

        IloExpr objective(env);
        for (IloInt k = 0; k < cluster_count; ++k) {
            if (instance.clusters[static_cast<std::size_t>(k)].id != instance.depot_cluster_id) {
                objective += instance.clusters[static_cast<std::size_t>(k)].reward * z[k];
            }
        }
        model.add(IloMaximize(env, objective));
        objective.end();

        for (IloInt i = 0; i < n; ++i) {
            IloExpr outgoing(env);
            IloExpr incoming(env);
            for (IloInt j = 0; j < n; ++j) {
                if (i == j) continue;
                outgoing += x[arc_index[static_cast<std::size_t>(i)][static_cast<std::size_t>(j)]];
                incoming += x[arc_index[static_cast<std::size_t>(j)][static_cast<std::size_t>(i)]];
            }
            model.add(outgoing == y[i]);
            model.add(incoming == y[i]);
            outgoing.end();
            incoming.end();
        }
        model.add(y[depot] == 1);

        for (IloInt k = 0; k < cluster_count; ++k) {
            IloExpr visits(env);
            const Cluster& cluster = instance.clusters[static_cast<std::size_t>(k)];
            for (int node_id : cluster.node_ids) {
                visits += y[static_cast<IloInt>(instance.node_index.at(node_id))];
            }
            model.add(z[k] <= visits);
            model.add(visits <= static_cast<IloNum>(cluster.node_ids.size()) * z[k]);
            if (cluster.id == instance.depot_cluster_id ||
                instance.mandatory_cluster_ids.count(cluster.id)) {
                model.add(z[k] == 1);
            }
            visits.end();
        }

        IloExpr route_cost(env);
        for (IloInt a = 0; a < arc_from.getSize(); ++a) {
            route_cost += instance.distances[static_cast<std::size_t>(arc_from[a])]
                                               [static_cast<std::size_t>(arc_to[a])] * x[a];
        }
        model.add(route_cost <= instance.tmax);
        route_cost.end();

        IloCplex cplex(model);
        cplex.use(SubtourEliminationCallback(env, x, arc_from, arc_to, n, depot));
        cplex.setParam(IloCplex::Param::Threads, options.threads);
        cplex.setParam(IloCplex::Param::TimeLimit, options.time_limit_seconds);
        cplex.setParam(IloCplex::Param::MIP::Tolerances::MIPGap, options.mip_gap);
        cplex.setParam(IloCplex::Param::RandomSeed, options.random_seed);
        cplex.setParam(IloCplex::Param::MIP::Display, options.log_level);
        if (options.log_level == 0) {
            cplex.setOut(env.getNullStream());
            cplex.setWarning(env.getNullStream());
        }

        const double start = cplex.getCplexTime();
        cplex.solve();
        solution.elapsed_seconds = cplex.getCplexTime() - start;
        solution.solver_status = "BRANCH_AND_CUT; " + solverStatusText(cplex);
        solution.explored_nodes = static_cast<std::int64_t>(cplex.getNnodes64());
        solution.mandatory_clusters = instance.mandatory_cluster_ids;

        const IloAlgorithm::Status algorithm_status = cplex.getStatus();
        solution.has_incumbent = cplex.isPrimalFeasible();
        if (algorithm_status == IloAlgorithm::Optimal) {
            solution.status = SolveStatus::Optimal;
        } else if (algorithm_status == IloAlgorithm::Infeasible) {
            solution.status = SolveStatus::Infeasible;
        } else if (solution.has_incumbent && cplex.getCplexStatus() == IloCplex::AbortTimeLim) {
            solution.status = SolveStatus::FeasibleTimeLimit;
        } else if (solution.has_incumbent) {
            solution.status = SolveStatus::FeasibleOther;
        } else {
            solution.status = SolveStatus::NoFeasibleSolution;
        }

        if (solution.has_incumbent) {
            solution.objective = cplex.getObjValue();
            solution.best_bound = cplex.getBestObjValue();
            solution.relative_gap = cplex.getMIPRelativeGap();
            std::vector<int> successor(static_cast<std::size_t>(n), -1);
            for (IloInt a = 0; a < arc_from.getSize(); ++a) {
                if (cplex.getValue(x[a]) > 0.5) {
                    const int from_id = instance.nodes[static_cast<std::size_t>(arc_from[a])].id;
                    const int to_id = instance.nodes[static_cast<std::size_t>(arc_to[a])].id;
                    solution.selected_arcs.emplace_back(from_id, to_id);
                    successor[static_cast<std::size_t>(arc_from[a])] = arc_to[a];
                }
            }
            solution.total_distance = 0.0;
            for (const auto& arc : solution.selected_arcs) {
                solution.total_distance += instance.distanceById(arc.first, arc.second);
            }
            IloInt current = depot;
            solution.route.push_back(instance.nodes[static_cast<std::size_t>(current)].id);
            for (IloInt step = 0; step <= n; ++step) {
                const int next = successor[static_cast<std::size_t>(current)];
                if (next < 0) break;
                solution.route.push_back(instance.nodes[static_cast<std::size_t>(next)].id);
                current = next;
                if (current == depot) break;
            }
            for (IloInt i = 0; i < n; ++i) {
                if (cplex.getValue(y[i]) > 0.5) {
                    solution.visited_nodes.insert(instance.nodes[static_cast<std::size_t>(i)].id);
                }
            }
            for (IloInt k = 0; k < cluster_count; ++k) {
                if (cplex.getValue(z[k]) > 0.5) {
                    solution.served_clusters.insert(instance.clusters[static_cast<std::size_t>(k)].id);
                }
            }
            solution.mandatory_satisfied = true;
            for (int id : instance.mandatory_cluster_ids) {
                if (!solution.served_clusters.count(id)) solution.mandatory_satisfied = false;
            }
        }

        env.end();
        return solution;
    } catch (const IloException& error) {
        const std::string message = error.getMessage();
        env.end();
        throw std::runtime_error("erro do CPLEX: " + message);
    } catch (...) {
        env.end();
        throw;
    }
}

}  // namespace sopmv
