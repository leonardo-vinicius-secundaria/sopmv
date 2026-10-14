# Resolvedores SOP/SOPMV: CPLEX, guloso e SA-PD

Implementação C++17 do Set Orienteering Problem (SOP) e do Set Orienteering Problem with Mandatory Visits (SOPMV), com quatro métodos comparáveis: modelo MILP exato em IBM ILOG CPLEX, heurística gulosa de inserção, Iterated Local Search (ILS) e Simulated Annealing com avaliação por programação dinâmica (SA-PD). Sem conjuntos obrigatórios, os executáveis resolvem SOP; com pelo menos um conjunto obrigatório, resolvem SOPMV.

## Organização do repositório

```text
data/           instâncias de entrada, separadas por família e variante
src/            código C++, separado em núcleo e resolvedores
tests/          testes automatizados e suas pequenas instâncias
scripts/        geração de instâncias e execução de experimentos
experiments/    resultados, entradas históricas e execuções arquivadas
visualization/  dashboard para inspeção dos resultados
docs/           relatórios e referências bibliográficas
build/          executáveis e demais artefatos de compilação
archive/        versões antigas preservadas apenas para consulta
```

Novos resultados devem ser criados dentro de `experiments/`, em uma pasta cujo
nome identifique a família e a finalidade do experimento. Instâncias reutilizáveis
devem permanecer em `data/`; arquivos compilados pertencem somente a `build/`.

## Formato de instância observado

O arquivo original `data/berlin52/sop/11berlin52_T40_p1.sop` foi preservado. Seu conteúdo, e não apenas o nome, declara:

- `NAME: 11berlin52_T40_p1`;
- `DIMENSION: 52`;
- `TMAX: 1616`;
- `SETS: 12` (conjunto `0` do depósito mais 11 conjuntos lucrativos);
- `EDGE_WEIGHT_TYPE: CEIL_2D`;
- depósito: nó `1`, único nó do conjunto `0`, cuja recompensa é zero;
- conjuntos numerados de `0` a `11` e lucro total 51.

Há diferenças relevantes em relação a variantes comuns de TSPLIB: `TYPE` aparece como `TSP`, não há `DEPOT_SECTION`, não há cardinalidade nas linhas dos conjuntos e não há marcador `EOF`. O depósito é identificado pelo único conjunto de recompensa zero, que deve conter exatamente um nó. O parser não extrai `T40`, `p1`, dimensão ou depósito do nome do arquivo.

Cada nó deve aparecer exatamente uma vez nos conjuntos. O parser também rejeita identificadores duplicados ou inexistentes, conjunto vazio, `TMAX` não positivo, tipo de distância não suportado, conjunto obrigatório inexistente e obrigatoriedade do conjunto do depósito.

São aceitos `CEIL_2D`, calculado por

```text
ceil(sqrt((xi-xj)^2 + (yi-yj)^2))
```

e `EUC_2D`, com o arredondamento TSPLIB `floor(distância + 0.5)`.

## Conjuntos obrigatórios

Há duas representações suportadas:

1. Uma coluna explicitamente nomeada `mandatory` ou `required` no descritor de `GTSP_SET_SECTION`, imediatamente depois do lucro. Exemplo:

   ```text
   GTSP_SET_SECTION: set_id set_profit mandatory id-vertex-list
   3 5 1 8 9 10
   ```

2. Um arquivo auxiliar que contenha `MANDATORY_SETS:`. O formato gerado pelo projeto é:

   ```text
   NAME: 11berlin52_T40_p1_MV20_seed202601
   SOURCE_INSTANCE: 11berlin52_T40_p1
   REQUESTED_RATIO: 0.2
   ROUNDING_RULE: floor(ratio * eligible_sets + 0.5)
   ELIGIBLE_SETS: 11
   SELECTED_COUNT: 2
   SEED: 202601
   MANDATORY_SETS: 3 11
   ```

Se as duas formas forem usadas, os conjuntos são unidos. Sem nenhuma delas, `M` é vazio e o problema é SOP. O leitor confere `SOURCE_INSTANCE` e `SELECTED_COUNT` quando esses campos estão presentes.

O gerador exclui o conjunto do depósito, começa pela lista ordenada de conjuntos elegíveis e usa Fisher–Yates com `std::mt19937` e amostragem limitada por rejeição. Assim, uma mesma instância, proporção e semente produzem a mesma lista nesta implementação. A quantidade é `floor(ratio * quantidade_elegível + 0.5)` (arredondamento ao inteiro mais próximo, com empate para cima). O gerador se recusa a sobrescrever um arquivo existente.

## Formulação MILP

Para todo arco dirigido não diagonal, `x[i,j]` indica seu uso. `y[i]` indica visita ao nó e `z[k]` indica atendimento ao conjunto. O objetivo maximiza `sum(p[k] z[k])`, sem recompensa para o depósito.

O modelo contém os dois graus iguais a `y[i]`, fixa `y[d]=1`, liga conjuntos e nós por

```text
z[k] <= sum(i em S[k]) y[i]
sum(i em S[k]) y[i] <= |S[k]| z[k]
```

e fixa `z[k]=1` para `k` obrigatório. Não é imposta a visita de exatamente um nó por conjunto. O orçamento é `sum(d[i,j] x[i,j]) <= TMAX`.

Para eliminar subciclos desconectados, há um fluxo de uma mercadoria `f[i,j]`, com `0 <= f[i,j] <= (|N|-1)x[i,j]`. Cada nó visitado diferente do depósito consome uma unidade; o depósito envia `sum(i != d)y[i]`. Em conjunto com os graus, isso produz uma única rota simples que começa e termina no depósito. Variáveis `x[i,i]` não são criadas.

A variante `sopmv_cplex_branch_cut` mantém as demais restrições e substitui esse fluxo por cortes de eliminação de subciclo sob demanda. Quando uma solução inteira contém um ciclo `S` desconectado do depósito, o callback adiciona `sum(i,j em S, i != j) x[i,j] <= |S|-1`.

## Compilação

### Make (disponível no ambiente validado)

```bash
make CPLEX_ROOT_DIR=/caminho/para/CPLEX_Studio129
```

Sem `CPLEX_ROOT_DIR`, são compilados o parser, o gerador, o guloso, o ILS, o SA-PD e os testes independentes do CPLEX. Com a variável, também são compilados `build/bin/sopmv_cplex`, `build/bin/sopmv_cplex_branch_cut` e os testes exatos. O primeiro mantém a formulação de fluxo original; o segundo elimina subciclos sob demanda por callback.

### CMake 3.16 ou posterior

```bash
cmake -S . -B build \
  -DCPLEX_ROOT_DIR=/caminho/para/CPLEX_Studio129 \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Não há caminho absoluto de CPLEX gravado nos arquivos de build. A arquitetura padrão do Makefile é `x86-64_linux`; ela pode ser alterada com `CPLEX_ARCH`.

## Execução

SOP clássico:

```bash
build/bin/sopmv_cplex \
  --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --time-limit 3600 --threads 1 --mip-gap 0 \
  --seed 202601 --log-level 2 \
  --csv results.csv
```

SOPMV:

```bash
build/bin/sopmv_cplex \
  --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --mandatory-file data/berlin52/mandatory_sets/11berlin52_T40_p1_MV20_seed202601.mv \
  --time-limit 3600 --threads 1 --mip-gap 0 \
  --seed 202601 --log-level 2 \
  --csv results.csv
```

Para executar a formulação branch-and-cut, use os mesmos argumentos trocando apenas o executável por `build/bin/sopmv_cplex_branch_cut`.

Geração reprodutível:

```bash
build/bin/generate_sopmv \
  --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --ratio 0.20 --seed 202601 \
  --output data/berlin52/mandatory_sets/11berlin52_T40_p1_MV20_seed202601.mv
```

### Simulated Annealing + Programação Dinâmica

O executável independente `build/bin/sopmv_sa` resolve SOP e SOPMV sem chamar o CPLEX
durante a busca. A sequência de conjuntos, a escolha de um representante por
conjunto e a rota são avaliadas pela programação dinâmica. Os parâmetros padrão
são `T0=16`, `alpha=0.93`, `80000` iterações por temperatura, limite de
`1.5 * número de conjuntos lucrativos` segundos e semente `202601`.

```bash
build/bin/sopmv_sa --instance data/berlin52/sop/11berlin52_T40_p1.sop --seed 202601
build/bin/sopmv_sa --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --mandatory-sets "3 4" --seed 202601
```

Os parâmetros podem ser sobrescritos com `--sa-temperature`, `--sa-alpha`,
`--sa-iterations`, `--sa-time-limit` e `--seed`. `--mandatory-file` também é
aceito, assim como `--mandatory-sets` para uma execução rápida sem criar um
arquivo auxiliar.

### Heurística gulosa

O executável `build/bin/sopmv_greedy` não depende do CPLEX e é determinístico. Ele
insere primeiro os conjuntos obrigatórios pelo menor aumento de distância e,
depois, escolhe conjuntos opcionais pela maior razão entre recompensa e custo
incremental. Cada passo examina todos os representantes e posições possíveis;
uma busca local de representantes e 2-opt reduz a rota após cada inserção.

```bash
build/bin/sopmv_greedy --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --csv experiments/smoke_tests/greedy.csv
build/bin/sopmv_greedy --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --mandatory-sets "3 4" --csv experiments/smoke_tests/greedy.csv
```

Como se trata de uma heurística construtiva, `NoFeasibleSolution` significa que
o método não conseguiu construir uma rota viável; não é uma prova de
inviabilidade.

### Iterated Local Search (ILS)

O executável `build/bin/sopmv_ils` parte da solução gulosa, aplica busca local sobre
representantes, ordem (2-opt) e inserções, e repete ciclos de perturbação e
busca local. Conjuntos obrigatórios nunca são removidos pela perturbação.

```bash
build/bin/sopmv_ils --instance data/berlin52/sop/11berlin52_T40_p1.sop \
  --ils-time-limit 10 --ils-iterations 10000 --ils-perturbation 2 \
  --seed 202601 --csv experiments/smoke_tests/ils.csv
```

Também são aceitos `--mandatory-file` e `--mandatory-sets`.

### Atalho para comparações

O script `scripts/run_comparison.sh` compila o projeto, executa CPLEX, guloso e SA-PD no
SOP sem obrigatórios, gera ou reutiliza um arquivo `.mv`, repete os três métodos
na variante SOPMV e acumula as linhas em `experiments/smoke_tests/comparacao.csv`:

```bash
./scripts/run_comparison.sh --cplex-root /caminho/para/CPLEX_Studio129
```

O SA-PD usa por padrão seu limite de `1.5 * número de conjuntos lucrativos`.
Use `--sa-time-limit SEGUNDOS` para fixar outro limite; `--time-limit` continua
sendo o limite do CPLEX.

O padrão é razão 20% e semente 202601. Reexecutá-lo com os mesmos argumentos
reutiliza exatamente o mesmo arquivo e os mesmos conjuntos. Para outra seleção
reprodutível, informe outra semente; para definir os conjuntos manualmente:

```bash
./scripts/run_comparison.sh --cplex-root /caminho/para/CPLEX_Studio129 --seed 202602
./scripts/run_comparison.sh --cplex-root /caminho/para/CPLEX_Studio129 --mandatory-sets "4 7"
```

O segundo comando não sorteia nada: torna os conjuntos 4 e 7 obrigatórios.

Parâmetros do resolvedor: `--time-limit`, `--threads`, `--mip-gap`, `--seed`, `--log-level` (0 a 5) e `--csv`. Os padrões são uma thread, gap zero, 3600 segundos, semente zero, log 2 e `results.csv`.

O CSV é criado com cabeçalho ou recebe uma nova linha se já existir. Campos de solução ficam vazios quando não há incumbente; nenhum valor de variável é consultado nessa situação. A saída distingue ótimo, viável interrompido por tempo, outro viável, inviável, sem solução viável e erro.

## Validação e testes

Execute tudo com:

```bash
make test CPLEX_ROOT_DIR=/caminho/para/CPLEX_Studio129
```

O validador é independente do modelo Concert. Ele reconstrói distância e recompensa e confere depósito nas duas pontas, correspondência entre rota e arcos, ausência de arcos/subciclos fora da rota, orçamento, obrigatórios, objetivo e contabilização única de cada recompensa.

Resultados obtidos localmente com g++ 9.4.0, CPLEX 12.9.0.0, uma thread e gap zero:

- parser real, coluna `mandatory`, arquivo auxiliar e reprodutibilidade do gerador: passou;
- validações positiva e negativas da instância sintética: passaram;
- sintética SOP: ótimo 8;
- sintética SOPMV com conjunto 1 obrigatório: ótimo 5 e obrigatório atendido;
- sintética com conjuntos 1 e 2 obrigatórios: inviável, como esperado;
- `11berlin52_T40_p1`, sem obrigatórios: ótimo 37, best bound 37, gap 0, distância 1612 e validação independente aprovada;
- guloso em `11berlin52_T40_p1`, sem obrigatórios: recompensa 37, distância 986 e validação independente aprovada;
- variante real MV20 gerada com semente 202601 (`M={3,11}`): inviável para `TMAX=1616`, comprovado pelo CPLEX. O gerador não tenta garantir viabilidade.

Os arquivos auxiliares de 10%, 20% e 30% com semente 202601 estão em `data/berlin52/mandatory_sets/`, separados da instância SOP original.
