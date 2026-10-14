#include "greedy.hpp"
#include "instance.hpp"
#include "solution_validator.hpp"

#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
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
    std::string mandatory_sets;
    std::string csv_path{"results.csv"};
};

void usage(const char* program) {
    std::cerr
        << "Uso: " << program << " --instance ARQUIVO [opcoes]\n"
        << "  --mandatory-file ARQUIVO.mv\n"
        << "  --mandatory-sets \"ID ID ...\"\n"
        << "  --csv ARQUIVO          (padrao: results.csv)\n";
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
        else if (arg == "--mandatory-sets") options.mandatory_sets = value;
        else if (arg == "--csv") options.csv_path = value;
        else throw std::invalid_argument("opcao desconhecida: " + arg);
    }
    if (options.instance_path.empty()) throw std::invalid_argument("--instance e obrigatorio");
    if (options.csv_path.empty()) throw std::invalid_argument("--csv nao pode ser vazio");
    if (!options.mandatory_path.empty() && !options.mandatory_sets.empty()) {
        throw std::invalid_argument("use --mandatory-file ou --mandatory-sets, nao ambos");
    }
    return options;
}

std::set<int> parseMandatorySets(const std::string& text) {
    std::set<int> result;
    std::string normalized = text;
    for (char& character : normalized) if (character == ',') character = ' ';
    std::istringstream input(normalized);
    for (int id = 0; input >> id;) result.insert(id);
    if (input.fail() && !input.eof()) {
        throw std::invalid_argument("--mandatory-sets contem valor invalido: " + text);
    }
    return result;
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

void appendCsv(const std::string& path, const sopmv::Instance& instance,
               const sopmv::Solution& solution) {
    std::ifstream current(path, std::ios::binary | std::ios::ate);
    const bool write_header = !current || current.tellg() == 0;
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
           << (solution.has_incumbent ? sopmv::statusName(solution.status) : "NoFeasibleSolutionFound") << ','
           << csvEscape(solution.solver_status) << ','
           << numberOrEmpty(solution.objective) << ",,,"
           << solution.elapsed_seconds << ',' << solution.explored_nodes << ','
           << numberOrEmpty(solution.total_distance) << ',' << instance.tmax << ','
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
              << "Variante: " << (instance.mandatory_cluster_ids.empty() ? "SOP" : "SOPMV") << '\n'
              << "Metodo: GREEDY_INSERTION\n"
              << "Status: " << sopmv::statusName(solution.status) << '\n'
              << "TMAX: " << instance.tmax << '\n'
              << "Conjuntos obrigatorios: " << join(instance.mandatory_cluster_ids, ", ") << '\n';
    if (!solution.has_incumbent) {
        std::cout << "NoFeasibleSolutionFound\n"
                  << "Tempo de execucao: " << solution.elapsed_seconds << " s\n"
                  << "Insercoes avaliadas: " << solution.explored_nodes << '\n'
                  << "Validador: nao aplicavel\n";
        return;
    }
    std::cout << "Recompensa: " << solution.objective << '\n'
              << "Distancia da rota: " << solution.total_distance << '\n'
              << "Sequencia de conjuntos: " << join(solution.sequence, ", ") << '\n'
              << "Representantes: " << join(solution.representatives, ", ") << '\n'
              << "Rota de nos: " << join(solution.route, " -> ") << '\n'
              << "Tempo de execucao: " << solution.elapsed_seconds << " s\n"
              << "Insercoes avaliadas: " << solution.explored_nodes << '\n'
              << "Atendimento dos obrigatorios: " << (solution.mandatory_satisfied ? "sim" : "nao") << '\n'
              << "Validador: " << (solution.valid ? "valido" : "invalido")
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
        } else if (!options.mandatory_sets.empty()) {
            sopmv::applyMandatorySets(instance, parseMandatorySets(options.mandatory_sets));
        }

        sopmv::Solution solution = sopmv::solveGreedy(instance);
        if (solution.has_incumbent) {
            const sopmv::ValidationResult validation = sopmv::validateSolution(instance, solution);
            solution.valid = validation.valid;
            solution.validation_message = validation.message;
            if (validation.valid) {
                solution.total_distance = validation.distance;
                solution.visited_nodes = validation.visited_nodes;
                solution.served_clusters = validation.served_clusters;
            }
        } else {
            solution.validation_message = "NoFeasibleSolutionFound";
        }
        printSolution(instance, solution);
        appendCsv(options.csv_path, instance, solution);
        std::cout << "CSV: " << options.csv_path << '\n';
        return solution.has_incumbent && !solution.valid ? 3 : 0;
    } catch (const sopmv::InstanceError& error) {
        std::cerr << "Erro na instancia: " << error.what() << '\n';
        return 2;
    } catch (const std::exception& error) {
        std::cerr << "Erro: " << error.what() << '\n';
        return 1;
    }
}
