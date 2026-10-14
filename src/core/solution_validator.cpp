#include "solution_validator.hpp"

#include <algorithm>
#include <cmath>
#include <set>
#include <sstream>

namespace sopmv {
namespace {

ValidationResult failure(const std::string& message) {
    ValidationResult result;
    result.message = message;
    return result;
}

}  // namespace

ValidationResult validateSolution(const Instance& instance,
                                  const Solution& solution,
                                  double tolerance) {
    if (!solution.has_incumbent) return failure("a solucao nao possui incumbente");
    // Uma rota vazia e valida para SOP: o deposito e o unico no visitado.
    if (solution.route.empty()) return failure("a rota deve conter o deposito");
    if (solution.route.front() != instance.depot_node_id ||
        solution.route.back() != instance.depot_node_id) {
        return failure("a rota nao comeca e termina no deposito");
    }

    std::set<std::pair<int, int>> selected(solution.selected_arcs.begin(), solution.selected_arcs.end());
    if (selected.size() != solution.selected_arcs.size()) {
        return failure("ha arcos selecionados duplicados");
    }

    ValidationResult result;
    result.visited_nodes.insert(instance.depot_node_id);
    std::set<std::pair<int, int>> route_arcs;
    for (std::size_t p = 0; p + 1 < solution.route.size(); ++p) {
        const int from = solution.route[p];
        const int to = solution.route[p + 1];
        if (!instance.node_index.count(from) || !instance.node_index.count(to)) {
            return failure("a rota contem no inexistente");
        }
        if (from == to) return failure("a rota contem arco diagonal");
        const std::pair<int, int> arc{from, to};
        if (!selected.count(arc)) return failure("transicao da rota nao corresponde a arco selecionado");
        if (!route_arcs.insert(arc).second) return failure("a rota repete um arco");
        result.distance += instance.distanceById(from, to);
        if (to != instance.depot_node_id && !result.visited_nodes.insert(to).second) {
            return failure("a rota revisita um no e forma ciclo nao simples");
        }
    }
    if (route_arcs != selected) {
        return failure("existem arcos selecionados fora da rota do deposito (subciclo ou componente desconectada)");
    }
    if (result.distance > instance.tmax + tolerance) {
        return failure("distancia recalculada excede TMAX");
    }

    for (const Cluster& cluster : instance.clusters) {
        bool served = false;
        for (int node_id : cluster.node_ids) {
            if (result.visited_nodes.count(node_id)) {
                served = true;
                break;
            }
        }
        if (served) {
            result.served_clusters.insert(cluster.id);
            if (cluster.id != instance.depot_cluster_id) result.reward += cluster.reward;
        }
    }
    for (int mandatory : instance.mandatory_cluster_ids) {
        if (!result.served_clusters.count(mandatory)) {
            return failure("conjunto obrigatorio nao atendido: " + std::to_string(mandatory));
        }
    }
    if (std::fabs(result.reward - solution.objective) > tolerance) {
        std::ostringstream message;
        message << "recompensa recalculada " << result.reward
                << " difere do objetivo " << solution.objective;
        return failure(message.str());
    }
    if (result.visited_nodes != solution.visited_nodes) {
        return failure("lista de nos visitados diverge da rota");
    }
    if (result.served_clusters != solution.served_clusters) {
        return failure("lista de conjuntos atendidos diverge da rota");
    }

    result.valid = true;
    result.message = "solucao valida";
    return result;
}

}  // namespace sopmv
