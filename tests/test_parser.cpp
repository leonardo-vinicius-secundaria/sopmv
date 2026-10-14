#include "instance.hpp"
#include "sopmv_generator.hpp"

#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <numeric>

#ifndef TEST_SOURCE_DIR
#error TEST_SOURCE_DIR must be defined
#endif

int main() {
    const std::filesystem::path source(TEST_SOURCE_DIR);
    const auto berlin = sopmv::readInstance((source / "data/berlin52/sop/11berlin52_T40_p1.sop").string());
    assert(berlin.name == "11berlin52_T40_p1");
    assert(berlin.dimension == 52);
    assert(berlin.nodes.size() == 52);
    assert(berlin.clusters.size() == 12);
    assert(berlin.depot_node_id == 1);
    assert(berlin.depot_cluster_id == 0);
    assert(berlin.tmax == 1616.0);
    assert(berlin.edge_weight_type == "CEIL_2D");
    assert(berlin.clusterById(4).node_ids.size() == 20);
    assert(berlin.clusterById(1).node_ids.front() == 13);
    assert(berlin.distanceById(1, 2) == 667.0);
    double reward_sum = 0.0;
    for (const auto& cluster : berlin.clusters) reward_sum += cluster.reward;
    assert(reward_sum == 51.0);
    assert(berlin.mandatory_cluster_ids.empty());

    const auto inline_mv = sopmv::readInstance(
        (source / "tests/data/small_inline_mandatory.sop").string());
    assert(inline_mv.mandatory_cluster_ids == std::set<int>{1});

    const auto generated1 = sopmv::generateMandatorySets(berlin, 0.20, 202601);
    const auto generated2 = sopmv::generateMandatorySets(berlin, 0.20, 202601);
    assert(generated1.selected_count == 2);
    assert(generated1.mandatory_sets == generated2.mandatory_sets);
    assert(!generated1.mandatory_sets.count(berlin.depot_cluster_id));

    const std::filesystem::path mandatory_path =
        std::filesystem::temp_directory_path() / "sopmv_test_mandatory.mv";
    std::error_code ignored;
    std::filesystem::remove(mandatory_path, ignored);
    sopmv::writeMandatoryFile(mandatory_path.string(), berlin, generated1);
    assert(sopmv::readMandatoryFile(mandatory_path.string(), berlin) == generated1.mandatory_sets);
    std::filesystem::remove(mandatory_path, ignored);

    std::cout << "test_parser: OK\n";
}
