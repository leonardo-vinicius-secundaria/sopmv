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

}  // namespace

Solution solveExact(const Instance& instance, const SolverOptions& options) {
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

        std::vector<IloInt> arc_from;
        std::vector<IloInt> arc_to;
        std::vector<std::vector<IloInt>> arc_index(
            static_cast<std::size_t>(n), std::vector<IloInt>(static_cast<std::size_t>(n), -1));
        for (IloInt i = 0; i < n; ++i) {
            for (IloInt j = 0; j < n; ++j) {
                if (i == j) continue;
                arc_index[i][j] = static_cast<IloInt>(arc_from.size());
                arc_from.push_back(i);
                arc_to.push_back(j);
            }
        }

        IloModel model(env, "SOP-SOPMV-SCF");
        IloBoolVarArray x(env, static_cast<IloInt>(arc_from.size()));
        IloBoolVarArray y(env, n);
        IloBoolVarArray z(env, cluster_count);
        IloNumVarArray flow(env, static_cast<IloInt>(arc_from.size()), 0.0,
                            static_cast<IloNum>(n - 1), ILOFLOAT);

        IloExpr objective(env);
        for (IloInt k = 0; k < cluster_count; ++k) {
            if (instance.clusters[k].id != instance.depot_cluster_id) {
                objective += instance.clusters[k].reward * z[k];
            }
        }
        model.add(IloMaximize(env, objective));
        objective.end();

        for (IloInt i = 0; i < n; ++i) {
            IloExpr outgoing(env);
            IloExpr incoming(env);
            for (IloInt j = 0; j < n; ++j) {
                if (i == j) continue;
                outgoing += x[arc_index[i][j]];
                incoming += x[arc_index[j][i]];
            }
            model.add(outgoing == y[i]);
            model.add(incoming == y[i]);
            outgoing.end();
            incoming.end();
        }
        model.add(y[depot] == 1);

        for (IloInt k = 0; k < cluster_count; ++k) {
            IloExpr visits(env);
            for (int node_id : instance.clusters[k].node_ids) {
                visits += y[static_cast<IloInt>(instance.node_index.at(node_id))];
            }
            model.add(z[k] <= visits);
            model.add(visits <= static_cast<IloNum>(instance.clusters[k].node_ids.size()) * z[k]);
            if (instance.clusters[k].id == instance.depot_cluster_id ||
                instance.mandatory_cluster_ids.count(instance.clusters[k].id)) {
                model.add(z[k] == 1);
            }
            visits.end();
        }

        IloExpr route_cost(env);
        for (IloInt a = 0; a < static_cast<IloInt>(arc_from.size()); ++a) {
            route_cost += instance.distances[arc_from[a]][arc_to[a]] * x[a];
            model.add(flow[a] <= static_cast<IloNum>(n - 1) * x[a]);
        }
        model.add(route_cost <= instance.tmax);
        route_cost.end();

        for (IloInt i = 0; i < n; ++i) {
            IloExpr balance(env);
            for (IloInt j = 0; j < n; ++j) {
                if (i == j) continue;
                if (i == depot) {
                    balance += flow[arc_index[i][j]] - flow[arc_index[j][i]];
                } else {
                    balance += flow[arc_index[j][i]] - flow[arc_index[i][j]];
                }
            }
            if (i == depot) {
                for (IloInt v = 0; v < n; ++v) {
                    if (v != depot) balance -= y[v];
                }
                model.add(balance == 0);
            } else {
                model.add(balance == y[i]);
            }
            balance.end();
        }

        IloCplex cplex(model);
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
        solution.solver_status = solverStatusText(cplex);
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
            for (IloInt a = 0; a < static_cast<IloInt>(arc_from.size()); ++a) {
                if (cplex.getValue(x[a]) > 0.5) {
                    const int from_id = instance.nodes[arc_from[a]].id;
                    const int to_id = instance.nodes[arc_to[a]].id;
                    solution.selected_arcs.emplace_back(from_id, to_id);
                    successor[arc_from[a]] = arc_to[a];
                }
            }
            solution.total_distance = 0.0;
            for (const auto& arc : solution.selected_arcs) {
                solution.total_distance += instance.distanceById(arc.first, arc.second);
            }
            IloInt current = depot;
            solution.route.push_back(instance.nodes[current].id);
            for (IloInt step = 0; step <= n; ++step) {
                const int next = successor[current];
                if (next < 0) break;
                solution.route.push_back(instance.nodes[next].id);
                current = next;
                if (current == depot) break;
            }
            for (IloInt i = 0; i < n; ++i) {
                if (cplex.getValue(y[i]) > 0.5) solution.visited_nodes.insert(instance.nodes[i].id);
            }
            for (IloInt k = 0; k < cluster_count; ++k) {
                if (cplex.getValue(z[k]) > 0.5) {
                    solution.served_clusters.insert(instance.clusters[k].id);
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
