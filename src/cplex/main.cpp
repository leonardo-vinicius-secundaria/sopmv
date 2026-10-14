#include "instance.hpp"
#include "solution_validator.hpp"
#include "sopmv_model.hpp"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {

struct CliOptions {
    std::string instance_path;
    std::string mandatory_path;
    std::string csv_path{"results.csv"};
    sopmv::SolverOptions solver;
};

void usage(const char* program) {
    std::cerr
        << "Uso: " << program << " --instance ARQUIVO [opcoes]\n"
        << "  --mandatory-file ARQUIVO.mv\n"
        << "  --time-limit SEGUNDOS   (padrao: 3600)\n"
        << "  --threads N             (padrao: 1)\n"
        << "  --mip-gap VALOR         (padrao: 0.0)\n"
        << "  --seed N                (padrao: 0)\n"
        << "  --log-level N           (0..5; padrao: 2)\n"
        << "  --csv ARQUIVO           (padrao: results.csv)\n";
}

CliOptions parseOptions(int argc, char** argv) {
    CliOptions options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            usage(argv[0]);
            std::exit(0);
        }
        if (i + 1 >= argc) throw std::invalid_argument("valor ausente para " + arg);
        const std::string value = argv[++i];
        if (arg == "--instance") options.instance_path = value;
        else if (arg == "--mandatory-file") options.mandatory_path = value;
        else if (arg == "--time-limit") options.solver.time_limit_seconds = std::stod(value);
        else if (arg == "--threads") options.solver.threads = std::stoi(value);
        else if (arg == "--mip-gap") options.solver.mip_gap = std::stod(value);
        else if (arg == "--seed") options.solver.random_seed = std::stoi(value);
        else if (arg == "--log-level") options.solver.log_level = std::stoi(value);
        else if (arg == "--csv") options.csv_path = value;
        else throw std::invalid_argument("opcao desconhecida: " + arg);
    }
    if (options.instance_path.empty()) throw std::invalid_argument("--instance e obrigatorio");
    if (options.csv_path.empty()) throw std::invalid_argument("--csv nao pode ser vazio");
    return options;
}

template <typename Range>
std::string join(const Range& values, const std::string& separator, int excluded = -1) {
    std::ostringstream output;
    bool first = true;
    for (const auto& value : values) {
        if (value == excluded) continue;
        if (!first) output << separator;
        output << value;
        first = false;
    }
    return output.str();
}

std::string joinRoute(const std::vector<int>& route) {
    return join(route, " -> ");
}

std::string csvEscape(const std::string& value) {
    std::string escaped{"\""};
    for (char c : value) {
        if (c == '\"') escaped += '\"';
        escaped += c;
    }
    escaped += '\"';
    return escaped;
}

std::string numberOrEmpty(double value) {
    if (!std::isfinite(value)) return {};
    std::ostringstream output;
    output << std::setprecision(15) << value;
    return output.str();
}

void appendCsv(const std::string& path,
               const sopmv::Instance& instance,
               const sopmv::Solution& solution) {
    bool write_header = true;
    {
        std::ifstream current(path, std::ios::binary | std::ios::ate);
        write_header = !current || current.tellg() == 0;
    }
    std::ofstream output(path, std::ios::app);
    if (!output) throw std::runtime_error("nao foi possivel abrir CSV para escrita: " + path);
    if (write_header) {
        output << "instance,variant,mandatory_ratio,mandatory_sets,status,solver_status,objective,"
                  "best_bound,gap,elapsed_seconds,tree_nodes,total_distance,tmax,route,visited_nodes,"
                  "served_sets,mandatory_satisfied,solution_valid,validation_message\n";
    }
    const std::size_t eligible = instance.clusters.size() - 1;
    const double ratio = eligible == 0 ? 0.0 :
        static_cast<double>(instance.mandatory_cluster_ids.size()) / static_cast<double>(eligible);
    output << csvEscape(instance.name) << ','
           << (instance.mandatory_cluster_ids.empty() ? "SOP" : "SOPMV") << ','
           << std::setprecision(15) << ratio << ','
           << csvEscape(join(instance.mandatory_cluster_ids, ";")) << ','
           << sopmv::statusName(solution.status) << ','
           << csvEscape(solution.solver_status) << ','
           << numberOrEmpty(solution.objective) << ','
           << numberOrEmpty(solution.best_bound) << ','
           << numberOrEmpty(solution.relative_gap) << ','
           << solution.elapsed_seconds << ','
           << solution.explored_nodes << ','
           << numberOrEmpty(solution.total_distance) << ','
           << instance.tmax << ','
           << csvEscape(join(solution.route, ";")) << ','
           << csvEscape(join(solution.visited_nodes, ";")) << ','
           << csvEscape(join(solution.served_clusters, ";", instance.depot_cluster_id)) << ','
           << (solution.mandatory_satisfied ? "true" : "false") << ','
           << (solution.valid ? "true" : "false") << ','
           << csvEscape(solution.validation_message) << '\n';
    if (!output) throw std::runtime_error("erro ao gravar CSV: " + path);
}

void printSolution(const sopmv::Instance& instance, const sopmv::Solution& solution) {
    std::cout << std::fixed << std::setprecision(6)
              << "Instancia: " << instance.name << '\n'
              << "Problema: " << (instance.mandatory_cluster_ids.empty() ? "SOP" : "SOPMV") << '\n'
              << "Status: " << sopmv::statusName(solution.status) << '\n'
              << "Status CPLEX: " << solution.solver_status << '\n'
              << "Tempo: " << solution.elapsed_seconds << " s\n"
              << "Nos da arvore: " << solution.explored_nodes << '\n'
              << "TMAX: " << instance.tmax << '\n'
              << "Conjuntos obrigatorios: " << join(instance.mandatory_cluster_ids, ", ") << '\n';
    if (!solution.has_incumbent) {
        std::cout << "Solucao viavel: nao\n";
        return;
    }
    std::cout << "Objetivo: " << solution.objective << '\n'
              << "Best bound: " << solution.best_bound << '\n'
              << "Gap: " << 100.0 * solution.relative_gap << "%\n"
              << "Distancia: " << solution.total_distance << '\n'
              << "Rota: " << joinRoute(solution.route) << '\n'
              << "Nos visitados: " << join(solution.visited_nodes, ", ") << '\n'
              << "Conjuntos atendidos: "
              << join(solution.served_clusters, ", ", instance.depot_cluster_id) << '\n'
              << "Obrigatorios atendidos: " << (solution.mandatory_satisfied ? "sim" : "nao") << '\n'
              << "Solucao valida: " << (solution.valid ? "sim" : "nao")
              << " (" << solution.validation_message << ")\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const CliOptions options = parseOptions(argc, argv);
        sopmv::Instance instance = sopmv::readInstance(options.instance_path);
        if (!options.mandatory_path.empty()) {
            std::set<int> mandatory = instance.mandatory_cluster_ids;
            const std::set<int> from_file = sopmv::readMandatoryFile(options.mandatory_path, instance);
            mandatory.insert(from_file.begin(), from_file.end());
            sopmv::applyMandatorySets(instance, mandatory);
            instance.name = std::filesystem::path(options.mandatory_path).stem().string();
        }

#ifdef SOPMV_BRANCH_AND_CUT
        sopmv::Solution solution = sopmv::solveExactBranchAndCut(instance, options.solver);
#else
        sopmv::Solution solution = sopmv::solveExact(instance, options.solver);
#endif
        if (solution.has_incumbent) {
            const sopmv::ValidationResult validation = sopmv::validateSolution(instance, solution);
            solution.valid = validation.valid;
            solution.validation_message = validation.message;
            if (validation.valid) {
                solution.total_distance = validation.distance;
                solution.mandatory_satisfied = true;
            }
        } else {
            solution.validation_message = "sem incumbente; validacao nao aplicavel";
        }
        printSolution(instance, solution);
        appendCsv(options.csv_path, instance, solution);
        std::cout << "CSV: " << options.csv_path << '\n';
        if (solution.has_incumbent && !solution.valid) {
            std::cerr << "Erro de validacao: " << solution.validation_message << '\n';
            return 3;
        }
        return solution.status == sopmv::SolveStatus::Infeasible ? 4 : 0;
    } catch (const sopmv::InstanceError& error) {
        std::cerr << "Erro na instancia: " << error.what() << '\n';
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "Erro: " << error.what() << '\n';
        return 1;
    }
}
