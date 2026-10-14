#pragma once

#include "instance.hpp"
#include "solution.hpp"

namespace sopmv {

// Heuristica deterministica de insercao. Primeiro atende os conjuntos
// obrigatorios pelo menor acrescimo de distancia e, depois, insere conjuntos
// opcionais pela melhor razao recompensa/acrescimo.
Solution solveGreedy(const Instance& instance);

}  // namespace sopmv
