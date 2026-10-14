#include "sopmv_generator.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <filesystem>
#include <limits>
#include <random>
#include <stdexcept>
#include <vector>

namespace sopmv {
namespace {

std::uint32_t boundedRandom(std::mt19937& engine, std::uint32_t bound) {
    if (bound == 0) throw std::invalid_argument("limite aleatorio igual a zero");
    const std::uint64_t range = static_cast<std::uint64_t>(std::mt19937::max()) + 1ULL;
    const std::uint64_t limit = range - range % bound;
    std::uint32_t value;
    do {
        value = engine();
    } while (static_cast<std::uint64_t>(value) >= limit);
    return value % bound;
}

}  // namespace

GenerationResult generateMandatorySets(const Instance& instance,
                                       double ratio,
                                       std::uint32_t seed) {
    if (!std::isfinite(ratio) || ratio < 0.0 || ratio > 1.0) {
        throw InstanceError("ratio deve estar no intervalo [0, 1]");
    }
    std::vector<int> eligible;
    for (const Cluster& cluster : instance.clusters) {
        if (cluster.id != instance.depot_cluster_id) eligible.push_back(cluster.id);
    }
    std::sort(eligible.begin(), eligible.end());

    GenerationResult result;
    result.requested_ratio = ratio;
    result.seed = seed;
    result.eligible_count = eligible.size();
    result.selected_count = static_cast<std::size_t>(
        std::floor(ratio * static_cast<double>(eligible.size()) + 0.5));

    std::mt19937 engine(seed);
    for (std::size_t i = eligible.size(); i > 1; --i) {
        const std::size_t j = boundedRandom(engine, static_cast<std::uint32_t>(i));
        std::swap(eligible[i - 1], eligible[j]);
    }
    for (std::size_t i = 0; i < result.selected_count; ++i) {
        result.mandatory_sets.insert(eligible[i]);
    }
    return result;
}

void writeMandatoryFile(const std::string& output_path,
                        const Instance& instance,
                        const GenerationResult& result) {
    std::ifstream existing(output_path);
    if (existing.good()) {
        throw InstanceError("o arquivo de saida ja existe; nao sera sobrescrito: " + output_path);
    }
    std::ofstream output(output_path);
    if (!output) throw InstanceError("nao foi possivel criar: " + output_path);
    output << "NAME: " << std::filesystem::path(output_path).stem().string() << "\n"
           << "SOURCE_INSTANCE: " << instance.name << "\n"
           << "REQUESTED_RATIO: " << result.requested_ratio << "\n"
           << "ROUNDING_RULE: floor(ratio * eligible_sets + 0.5)\n"
           << "ELIGIBLE_SETS: " << result.eligible_count << "\n"
           << "SELECTED_COUNT: " << result.selected_count << "\n"
           << "SEED: " << result.seed << "\n"
           << "MANDATORY_SETS:";
    for (int id : result.mandatory_sets) output << ' ' << id;
    output << '\n';
    if (!output) throw InstanceError("erro ao gravar: " + output_path);
}

}  // namespace sopmv
