#pragma once

#include <cstdint>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace sopmv {

struct Node {
    int id{};
    double x{};
    double y{};
};

struct Cluster {
    int id{};
    double reward{};
    std::vector<int> node_ids;
    bool mandatory{false};
};

struct Instance {
    std::string name;
    std::string edge_weight_type;
    int dimension{};
    double tmax{};
    int depot_node_id{};
    int depot_cluster_id{};
    std::vector<Node> nodes;
    std::vector<Cluster> clusters;
    std::set<int> mandatory_cluster_ids;

    std::unordered_map<int, std::size_t> node_index;
    std::unordered_map<int, std::size_t> cluster_index;
    std::vector<std::vector<double>> distances;

    const Node& nodeById(int id) const;
    const Cluster& clusterById(int id) const;
    double distanceById(int from_id, int to_id) const;
};

class InstanceError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

Instance readInstance(const std::string& path);
std::set<int> readMandatoryFile(const std::string& path, const Instance& instance);
void applyMandatorySets(Instance& instance, const std::set<int>& mandatory_sets);

}  // namespace sopmv
