#include "instance.hpp"
#include "sopmv_generator.hpp"

#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

struct Options {
    std::string instance;
    std::string output;
    double ratio{-1.0};
    std::uint32_t seed{};
    bool seed_set{false};
};

void usage(const char* program) {
    std::cerr << "Uso: " << program
              << " --instance ARQUIVO --ratio R --seed S --output ARQUIVO.mv\n";
}

Options parseOptions(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            usage(argv[0]);
            std::exit(0);
        }
        if (i + 1 >= argc) throw std::invalid_argument("valor ausente para " + arg);
        const std::string value = argv[++i];
        if (arg == "--instance") options.instance = value;
        else if (arg == "--output") options.output = value;
        else if (arg == "--ratio") options.ratio = std::stod(value);
        else if (arg == "--seed") {
            const unsigned long parsed = std::stoul(value);
            if (parsed > UINT32_MAX) throw std::invalid_argument("seed fora do intervalo uint32");
            options.seed = static_cast<std::uint32_t>(parsed);
            options.seed_set = true;
        } else {
            throw std::invalid_argument("opcao desconhecida: " + arg);
        }
    }
    if (options.instance.empty() || options.output.empty() || options.ratio < 0.0 || !options.seed_set) {
        throw std::invalid_argument("--instance, --ratio, --seed e --output sao obrigatorios");
    }
    return options;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parseOptions(argc, argv);
        const sopmv::Instance instance = sopmv::readInstance(options.instance);
        const auto generated = sopmv::generateMandatorySets(instance, options.ratio, options.seed);
        sopmv::writeMandatoryFile(options.output, instance, generated);
        std::cout << "Arquivo criado: " << options.output << "\nConjuntos obrigatorios:";
        for (int id : generated.mandatory_sets) std::cout << ' ' << id;
        std::cout << "\nQuantidade: " << generated.selected_count << '/' << generated.eligible_count << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Erro: " << error.what() << '\n';
        usage(argv[0]);
        return 2;
    }
}
