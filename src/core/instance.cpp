#include "instance.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <limits>
#include <sstream>
#include <unordered_set>

namespace sopmv {
namespace {

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string upper(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value;
}

std::pair<std::string, std::string> splitField(const std::string& line) {
    const auto colon = line.find(':');
    if (colon == std::string::npos) return {upper(trim(line)), {}};
    return {upper(trim(line.substr(0, colon))), trim(line.substr(colon + 1))};
}

int parseInt(const std::string& text, const std::string& field) {
    std::size_t used = 0;
    try {
        const int value = std::stoi(text, &used);
        if (!trim(text.substr(used)).empty()) throw std::invalid_argument("suffix");
        return value;
    } catch (const std::exception&) {
        throw InstanceError("valor inteiro invalido em " + field + ": '" + text + "'");
    }
}

double parseDouble(const std::string& text, const std::string& field) {
    std::size_t used = 0;
    try {
        const double value = std::stod(text, &used);
        if (!trim(text.substr(used)).empty() || !std::isfinite(value)) {
            throw std::invalid_argument("suffix");
        }
        return value;
    } catch (const std::exception&) {
        throw InstanceError("valor numerico invalido em " + field + ": '" + text + "'");
    }
}

std::vector<std::string> tokens(const std::string& line) {
    std::istringstream input(line);
    std::vector<std::string> result;
    for (std::string token; input >> token;) result.push_back(token);
    return result;
}

void buildAndValidate(Instance& instance, int declared_sets) {
    if (instance.name.empty()) throw InstanceError("campo NAME ausente");
    if (instance.dimension <= 0) throw InstanceError("DIMENSION deve ser positivo");
    if (instance.tmax <= 0.0) throw InstanceError("TMAX deve ser positivo");
    if (instance.edge_weight_type.empty()) throw InstanceError("EDGE_WEIGHT_TYPE ausente");
    if (instance.edge_weight_type != "CEIL_2D" && instance.edge_weight_type != "EUC_2D") {
        throw InstanceError("EDGE_WEIGHT_TYPE nao suportado: " + instance.edge_weight_type);
    }
    if (static_cast<int>(instance.nodes.size()) != instance.dimension) {
        throw InstanceError("DIMENSION=" + std::to_string(instance.dimension) +
                            ", mas foram lidos " + std::to_string(instance.nodes.size()) + " nos");
    }
    if (declared_sets <= 0 || static_cast<int>(instance.clusters.size()) != declared_sets) {
        throw InstanceError("SETS nao coincide com a quantidade de conjuntos lidos");
    }

    for (std::size_t i = 0; i < instance.nodes.size(); ++i) {
        const int id = instance.nodes[i].id;
        if (id <= 0 || !instance.node_index.emplace(id, i).second) {
            throw InstanceError("identificador de no invalido ou duplicado: " + std::to_string(id));
        }
    }

    std::unordered_map<int, int> membership;
    std::vector<int> depot_candidates;
    for (std::size_t k = 0; k < instance.clusters.size(); ++k) {
        const Cluster& cluster = instance.clusters[k];
        if (cluster.id < 0 || !instance.cluster_index.emplace(cluster.id, k).second) {
            throw InstanceError("identificador de conjunto invalido ou duplicado: " +
                                std::to_string(cluster.id));
        }
        if (cluster.reward < 0.0) {
            throw InstanceError("recompensa negativa no conjunto " + std::to_string(cluster.id));
        }
        if (cluster.node_ids.empty()) {
            throw InstanceError("conjunto vazio: " + std::to_string(cluster.id));
        }
        if (cluster.reward == 0.0) depot_candidates.push_back(cluster.id);
        for (int node_id : cluster.node_ids) {
            if (!instance.node_index.count(node_id)) {
                throw InstanceError("no inexistente " + std::to_string(node_id) +
                                    " no conjunto " + std::to_string(cluster.id));
            }
            if (!membership.emplace(node_id, cluster.id).second) {
                throw InstanceError("no " + std::to_string(node_id) +
                                    " pertence a mais de um conjunto");
            }
        }
    }
    for (const Node& node : instance.nodes) {
        if (!membership.count(node.id)) {
            throw InstanceError("no " + std::to_string(node.id) + " nao pertence a conjunto algum");
        }
    }
    if (depot_candidates.size() != 1) {
        throw InstanceError("esperado exatamente um conjunto de recompensa zero para o deposito");
    }
    instance.depot_cluster_id = depot_candidates.front();
    const Cluster& depot_cluster = instance.clusterById(instance.depot_cluster_id);
    if (depot_cluster.node_ids.size() != 1) {
        throw InstanceError("o conjunto do deposito deve conter exatamente um no");
    }
    instance.depot_node_id = depot_cluster.node_ids.front();

    const std::size_t n = instance.nodes.size();
    instance.distances.assign(n, std::vector<double>(n, 0.0));
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            const double dx = instance.nodes[i].x - instance.nodes[j].x;
            const double dy = instance.nodes[i].y - instance.nodes[j].y;
            const double euclidean = std::sqrt(dx * dx + dy * dy);
            if (instance.edge_weight_type == "CEIL_2D") {
                instance.distances[i][j] = std::ceil(euclidean);
            } else {
                instance.distances[i][j] = std::floor(euclidean + 0.5);
            }
        }
    }

    std::set<int> embedded;
    for (const Cluster& cluster : instance.clusters) {
        if (cluster.mandatory) embedded.insert(cluster.id);
    }
    applyMandatorySets(instance, embedded);
}

}  // namespace

const Node& Instance::nodeById(int id) const {
    const auto it = node_index.find(id);
    if (it == node_index.end()) throw InstanceError("no inexistente: " + std::to_string(id));
    return nodes.at(it->second);
}

const Cluster& Instance::clusterById(int id) const {
    const auto it = cluster_index.find(id);
    if (it == cluster_index.end()) throw InstanceError("conjunto inexistente: " + std::to_string(id));
    return clusters.at(it->second);
}

double Instance::distanceById(int from_id, int to_id) const {
    return distances.at(node_index.at(from_id)).at(node_index.at(to_id));
}

Instance readInstance(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw InstanceError("nao foi possivel abrir a instancia: " + path);

    enum class Section { Header, Coordinates, Clusters };
    Section section = Section::Header;
    Instance instance;
    int declared_sets = -1;
    bool cluster_has_mandatory_flag = false;
    std::string line;
    int line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (upper(line) == "EOF") break;

        const auto field = splitField(line);
        if (field.first == "NODE_COORD_SECTION") {
            section = Section::Coordinates;
            continue;
        }
        if (field.first == "GTSP_SET_SECTION") {
            section = Section::Clusters;
            const std::string description = upper(field.second);
            cluster_has_mandatory_flag = description.find("MANDATORY") != std::string::npos ||
                                         description.find("REQUIRED") != std::string::npos;
            continue;
        }
        if (field.first == "MANDATORY_SETS") {
            for (const std::string& value : tokens(field.second)) {
                instance.mandatory_cluster_ids.insert(parseInt(value, "MANDATORY_SETS"));
            }
            continue;
        }

        try {
            if (section == Section::Header) {
                if (field.first == "NAME") instance.name = field.second;
                else if (field.first == "DIMENSION") instance.dimension = parseInt(field.second, "DIMENSION");
                else if (field.first == "TMAX") instance.tmax = parseDouble(field.second, "TMAX");
                else if (field.first == "SETS") declared_sets = parseInt(field.second, "SETS");
                else if (field.first == "EDGE_WEIGHT_TYPE") instance.edge_weight_type = upper(field.second);
            } else if (section == Section::Coordinates) {
                const auto values = tokens(line);
                if (values.size() != 3) throw InstanceError("linha de coordenada deve ter 3 campos");
                instance.nodes.push_back({parseInt(values[0], "id do no"),
                                          parseDouble(values[1], "coordenada x"),
                                          parseDouble(values[2], "coordenada y")});
            } else {
                const auto values = tokens(line);
                const std::size_t minimum = cluster_has_mandatory_flag ? 4 : 3;
                if (values.size() < minimum) throw InstanceError("linha de conjunto incompleta");
                Cluster cluster;
                cluster.id = parseInt(values[0], "id do conjunto");
                cluster.reward = parseDouble(values[1], "recompensa do conjunto");
                std::size_t first_node = 2;
                if (cluster_has_mandatory_flag) {
                    const int flag = parseInt(values[2], "indicador mandatory");
                    if (flag != 0 && flag != 1) throw InstanceError("indicador mandatory deve ser 0 ou 1");
                    cluster.mandatory = flag == 1;
                    first_node = 3;
                }
                for (std::size_t i = first_node; i < values.size(); ++i) {
                    cluster.node_ids.push_back(parseInt(values[i], "id de no no conjunto"));
                }
                instance.clusters.push_back(std::move(cluster));
            }
        } catch (const InstanceError& error) {
            throw InstanceError(path + ":" + std::to_string(line_number) + ": " + error.what());
        }
    }

    const std::set<int> header_mandatory = instance.mandatory_cluster_ids;
    buildAndValidate(instance, declared_sets);
    std::set<int> all_mandatory = instance.mandatory_cluster_ids;
    all_mandatory.insert(header_mandatory.begin(), header_mandatory.end());
    applyMandatorySets(instance, all_mandatory);
    return instance;
}

void applyMandatorySets(Instance& instance, const std::set<int>& mandatory_sets) {
    for (int id : mandatory_sets) {
        if (!instance.cluster_index.count(id)) {
            throw InstanceError("conjunto obrigatorio inexistente: " + std::to_string(id));
        }
        if (id == instance.depot_cluster_id) {
            throw InstanceError("o conjunto do deposito nao pode ser marcado como obrigatorio");
        }
    }
    instance.mandatory_cluster_ids = mandatory_sets;
    for (Cluster& cluster : instance.clusters) {
        cluster.mandatory = mandatory_sets.count(cluster.id) != 0;
    }
}

std::set<int> readMandatoryFile(const std::string& path, const Instance& instance) {
    std::ifstream input(path);
    if (!input) throw InstanceError("nao foi possivel abrir o arquivo de obrigatorios: " + path);
    std::set<int> result;
    bool found = false;
    int declared_count = -1;
    std::string source_instance;
    std::string line;
    int line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        const auto field = splitField(line);
        if (field.first == "SOURCE_INSTANCE") {
            source_instance = field.second;
            continue;
        }
        if (field.first == "SELECTED_COUNT") {
            declared_count = parseInt(field.second, path + ":" + std::to_string(line_number));
            continue;
        }
        if (field.first != "MANDATORY_SETS") continue;
        if (found) throw InstanceError("MANDATORY_SETS repetido em " + path);
        found = true;
        for (const std::string& value : tokens(field.second)) {
            const int id = parseInt(value, path + ":" + std::to_string(line_number));
            if (!result.insert(id).second) {
                throw InstanceError("conjunto obrigatorio repetido: " + std::to_string(id));
            }
        }
    }
    if (!found) throw InstanceError("campo MANDATORY_SETS ausente em " + path);
    if (!source_instance.empty() && source_instance != instance.name) {
        throw InstanceError("SOURCE_INSTANCE='" + source_instance +
                            "' nao corresponde a NAME='" + instance.name + "'");
    }
    if (declared_count >= 0 && static_cast<std::size_t>(declared_count) != result.size()) {
        throw InstanceError("SELECTED_COUNT nao coincide com MANDATORY_SETS em " + path);
    }
    for (int id : result) {
        if (!instance.cluster_index.count(id)) {
            throw InstanceError("conjunto obrigatorio inexistente: " + std::to_string(id));
        }
        if (id == instance.depot_cluster_id) {
            throw InstanceError("o conjunto do deposito nao pode ser marcado como obrigatorio");
        }
    }
    return result;
}

}  // namespace sopmv
