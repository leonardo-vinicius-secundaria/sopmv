#pragma once

#include "instance.hpp"

#include <cstdint>
#include <set>
#include <string>

namespace sopmv {

struct GenerationResult {
    double requested_ratio{};
    std::uint32_t seed{};
    std::size_t eligible_count{};
    std::size_t selected_count{};
    std::set<int> mandatory_sets;
};

GenerationResult generateMandatorySets(const Instance& instance,
                                       double ratio,
                                       std::uint32_t seed);
void writeMandatoryFile(const std::string& output_path,
                        const Instance& instance,
                        const GenerationResult& result);

}  // namespace sopmv
