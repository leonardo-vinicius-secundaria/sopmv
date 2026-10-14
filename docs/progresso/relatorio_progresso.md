# Relatório de progresso do TCC

## Set Orienteering Problem with Mandatory Visits (SOPMV)

**Documento de referência:** Lin, S.-W.; Guo, S.; Wu, W.-J. *Applying the Simulated Annealing Algorithm to the Set Orienteering Problem with Mandatory Visits*. Mathematics, v. 12, art. 3089, 2024. DOI: 10.3390/math12193089. Arquivo local: `docs/referencias/lin_guo_wu_2024.pdf`.

## 1. Resumo do progresso

O trabalho desenvolvido até o momento tem como objeto o **Set Orienteering Problem with Mandatory Visits (SOPMV)**. O problema é definido sobre um conjunto de vértices agrupados em *clusters* (ou conjuntos), cada conjunto associado a uma recompensa. Uma solução escolhe uma rota fechada que parte do depósito e retorna a ele, visita representantes de alguns conjuntos e maximiza a recompensa total coletada, respeitando um limite máximo de deslocamento. No SOPMV, além disso, um subconjunto dos conjuntos deve obrigatoriamente ser atendido.

A principal diferença entre as duas variantes estudadas é, portanto:

- **SOP:** todos os conjuntos lucrativos são opcionais;
- **SOPMV:** parte dos conjuntos lucrativos é obrigatória e os demais continuam opcionais.

O artigo de Lin, Guo e Wu (2024) foi adotado como referência central para a definição do problema, a formulação matemática e o uso combinado de *Simulated Annealing* e programação dinâmica. A partir dessa base, foi construído um ambiente computacional em C++17 composto por:

1. leitor e validador de instâncias SOP/SOPMV;
2. gerador reprodutível de conjuntos obrigatórios;
3. modelo exato em CPLEX;
4. heurística construtiva gulosa;
5. meta-heurística Iterated Local Search (ILS), inicializada pelo guloso;
6. adaptação do algoritmo SA com avaliação por programação dinâmica, denominada SA_PD;
7. validador independente das soluções e rotinas para execução de baterias experimentais.

O fluxo de pesquisa seguido foi:

1. estudo da definição do SOP e de sua extensão SOPMV;
2. interpretação e implementação de uma formulação MILP no CPLEX;
3. implementação de uma construção gulosa rápida;
4. desenvolvimento do ILS para melhorar as soluções do guloso;
5. adaptação do SA_PD a partir do método proposto no artigo;
6. validação das soluções por uma rotina independente dos resolvedores;
7. experimentação nas famílias derivadas de `11berlin52` e `vm1084`.

### 1.1 Definição matemática resumida

Sejam (V) o conjunto de vértices, (S_k \subseteq V) o conjunto de vértices do *cluster* (k), (p_k) sua recompensa, (d_{ij}) a distância entre os vértices (i) e (j), (T_{max}) o orçamento de viagem e (M) o conjunto dos *clusters* obrigatórios. O objetivo é maximizar

\[
\max \sum_k p_k z_k,
\]

em que (z_k=1) indica que o conjunto (k) foi atendido. A solução deve formar uma rota conectada que sai do depósito e retorna a ele, obedecer a

\[
\sum_{i \neq j} d_{ij}x_{ij} \leq T_{max}
\]

e satisfazer (z_k=1) para todo (k\in M). Na implementação, variáveis de arco (x_{ij}), de visita (y_i) e de atendimento (z_k) são ligadas por restrições de grau e de associação entre vértices e conjuntos. Um fluxo de uma mercadoria elimina subciclos desconectados.

### 1.2 Esclarecimento sobre precedência e número de veículos

O SOPMV estudado no artigo significa **Set Orienteering Problem with Mandatory Visits**, e não um problema de precedência. A formulação e os algoritmos implementados não contêm relações do tipo “o conjunto A deve ser visitado antes do conjunto B”. A sequência das visitas é otimizada, mas não há precedência externa entre pares de conjuntos.

Da mesma forma, a implementação atual resolve uma **rota de veículo único**. Nos nomes das instâncias, `MV10`, `MV20` e `MV30` indicam aproximadamente 10%, 20% e 30% de conjuntos com visita obrigatória (*mandatory visits*); não indicam 10, 20 ou 30 veículos. Uma extensão para múltiplos veículos exigiria outra formulação e operadores específicos de alocação entre rotas.

## 2. Funcionamento do algoritmo guloso

O algoritmo guloso é uma heurística construtiva determinística. Sua função é produzir rapidamente uma solução viável, além de fornecer a solução inicial do ILS.

### 2.1 Representação da solução

A rota começa como `depósito → depósito`. Para cada conjunto selecionado, o algoritmo armazena:

- o identificador do conjunto;
- o vértice escolhido como representante desse conjunto;
- a posição do representante na rota.

Cada inserção é avaliada pelo aumento de distância

\[
\Delta d = d_{i,v}+d_{v,j}-d_{i,j},
\]

em que o novo vértice (v) é colocado entre dois vértices consecutivos (i) e (j). A inserção somente é aceita se a distância resultante não ultrapassar (T_{max}).

### 2.2 Construção para o SOP

Quando não há conjuntos obrigatórios, todos os conjuntos lucrativos são candidatos opcionais. Em cada passo, o algoritmo:

1. examina todos os conjuntos ainda não atendidos;
2. testa todos os vértices representantes de cada conjunto;
3. testa todas as posições de inserção na rota corrente;
4. descarta inserções que violem (T_{max});
5. escolhe a inserção com maior razão (p_k/\max(\Delta d,\varepsilon));
6. aplica melhorias locais na rota;
7. repete o processo enquanto existir alguma inserção viável.

Como critérios de desempate, são considerados, nessa ordem, maior recompensa, menor aumento de distância e identificadores menores. Isso torna a execução reprodutível.

### 2.3 Construção para o SOPMV

No SOPMV, a construção possui duas fases:

1. **Fase obrigatória:** os conjuntos de (M) são inseridos primeiro. A cada iteração é escolhida a combinação conjunto–representante–posição com o menor aumento de distância. Se nenhum conjunto obrigatório restante puder ser inserido sem violar o orçamento, o algoritmo encerra sem solução viável.
2. **Fase opcional:** depois que todos os obrigatórios estão na rota, os conjuntos opcionais são inseridos pela razão recompensa/custo incremental usada no SOP.

Após cada inserção, duas melhorias são executadas até a estabilização:

- **troca de representante:** para cada conjunto visitado, procura-se outro vértice do mesmo conjunto que reduza o custo entre seus vizinhos na rota;
- **2-opt:** inverte-se um segmento da rota quando a troca de duas arestas reduz a distância.

Essa estratégia preserva a viabilidade e libera espaço no orçamento para novas inserções. Entretanto, por tomar decisões locais irrevogáveis, o guloso pode escolher cedo um conjunto com boa razão imediata e impedir combinações posteriores de maior recompensa total.

## 3. Funcionamento do Iterated Local Search (ILS)

O ILS foi desenvolvido para superar a principal limitação do guloso: a dificuldade de desfazer escolhas iniciais. Seu funcionamento pode ser resumido em quatro etapas.

### 3.1 Solução inicial

O ILS chama o algoritmo guloso e usa sua solução viável como estado inicial, solução corrente e melhor solução conhecida. Caso o guloso não consiga construir uma solução que contenha todos os conjuntos obrigatórios, a implementação atual também não inicia a busca ILS.

### 3.2 Busca local

A busca local combina três mecanismos:

1. escolha de representantes de menor custo dentro dos conjuntos já visitados;
2. movimentos 2-opt sobre a ordem de visita;
3. reinserção de conjuntos ainda não atendidos pela melhor razão recompensa/custo incremental.

As soluções são comparadas primeiro pela recompensa total. Em caso de empate, vence a rota de menor distância.

### 3.3 Perturbação

Em cada iteração, o algoritmo cria uma cópia da solução corrente e aplica uma perturbação. Um número limitado de conjuntos opcionais é removido aleatoriamente e, quando possível, um segmento da sequência é invertido. Os conjuntos obrigatórios nunca são removidos.

A busca local é executada novamente sobre a solução perturbada. Os conjuntos recém-removidos ficam temporariamente excluídos na primeira tentativa de inserção, o que evita que a perturbação seja imediatamente desfeita e favorece a exploração de outra região do espaço de soluções.

### 3.4 Aceitação e reinício

Se o candidato for melhor que a solução corrente, ele é aceito. A melhor solução global é atualizada sempre que houver aumento de recompensa ou, em empate, redução de distância. A cada 20 iterações, a busca retorna à melhor solução conhecida, reduzindo a deriva para regiões pouco promissoras. A execução termina pelo limite de tempo ou pelo número máximo de iterações.

Assim, o ILS alterna intensificação, pela busca local, e diversificação, pelas remoções e inversões aleatórias.

## 4. Adaptação do SA_PD

O SA_PD foi implementado como método comparativo adicional e segue a ideia central do artigo: o *Simulated Annealing* explora diferentes ordens de conjuntos, enquanto uma programação dinâmica escolhe os representantes dos conjuntos para uma ordem dada.

A representação é uma permutação dos conjuntos. Para avaliá-la, a programação dinâmica calcula, estágio a estágio, o menor custo para chegar a cada representante possível do conjunto corrente. Em seguida, determina o maior prefixo da sequência que ainda permite retornar ao depósito sem ultrapassar (T_{max}). A recompensa desse prefixo define a qualidade da solução.

Os vizinhos são produzidos por inserção, troca ou inversão de posições. Movimentos que melhoram a pontuação são aceitos; movimentos de piora podem ser aceitos com probabilidade

\[
P(\text{aceitar})=\exp(\Delta/T),
\]

para (\Delta=\text{pontuação nova}-\text{pontuação atual}<0). A temperatura é reduzida geometricamente. Essa aceitação probabilística permite escapar de ótimos locais.

Para o SOPMV, o estado recebe uma penalização elevada para cada conjunto obrigatório ausente do prefixo viável:

\[
\text{score}=\text{recompensa}-P\times\text{número de obrigatórios ausentes}.
\]

Enquanto nenhuma solução viável foi encontrada, a vizinhança prioriza a reorganização dos obrigatórios. A melhor solução reportada sempre deve atender todos eles. A implementação também corrige explicitamente o sinal da regra de aceitação do pseudocódigo do artigo, usando (\Delta=novo-atual).

Nos experimentos de `11berlin52`, os parâmetros usados foram temperatura inicial 16, fator de resfriamento 0,93, 80.000 iterações por temperatura, semente 20260928 e limite de 3 segundos por execução.

## 5. Papel do CPLEX e validação

O CPLEX implementa um modelo MILP e constitui o método exato do projeto. Sua função é fornecer soluções certificadas e limites superiores para avaliar as heurísticas. Contudo, é necessário distinguir dois casos:

- quando o CPLEX termina com estado **Optimal** e *gap* zero, o valor ótimo foi comprovado;
- quando termina por limite de tempo, o valor incumbente é apenas a melhor solução encontrada pelo CPLEX, e o *best bound* informa que ainda existe uma lacuna de otimalidade.

Portanto, o CPLEX é um *baseline* exato pela natureza do modelo, mas uma execução curta não é automaticamente uma fronteira ótima.

Todas as soluções reportadas como viáveis foram verificadas por um validador independente. Ele reconstrói a distância e a recompensa, verifica a partida e o retorno ao depósito, a correspondência entre rota e arcos, o limite (T_{max}), os conjuntos atendidos e a presença de todos os obrigatórios.

## 6. Experimentos e resultados

### 6.1 Família `11berlin52`

A bateria consolidada possui 32 casos: oito instâncias SOP e 24 variantes SOPMV, com percentuais solicitados de 10%, 20% e 30% de conjuntos obrigatórios. Cada caso foi executado com CPLEX, SA_PD, Guloso e ILS, totalizando 128 execuções. O CPLEX recebeu 10 segundos; SA_PD e ILS, aproximadamente 3 segundos; o guloso não possui limite ativo relevante e terminou em frações de milissegundo.

Dos 32 casos, 27 tiveram solução viável encontrada por todos os métodos. Nos cinco restantes, nenhum dos quatro resolveu uma rota viável: o CPLEX comprovou inviabilidade em quatro casos e terminou sem incumbente em um caso. Consequentemente, esse caso isolado não pode ser declarado inviável apenas com os dados atuais.

| Método | Soluções encontradas | Melhor valor ou empate entre os quatro métodos | Tempo médio em casos viáveis | Desvio médio para o melhor valor observado |
|---|---:|---:|---:|---:|
| CPLEX | 27/32 | 2/27 | 10,003 s | 19,50% |
| SA_PD | 27/32 | 26/27 | 3,000 s | 0,15% |
| Guloso | 27/32 | 9/27 | 0,000053 s | 3,67% |
| ILS | 27/32 | 27/27 | 3,000 s | 0,00% |

O “melhor valor observado” é o maior objetivo obtido pelos quatro métodos em cada caso; ele não deve ser chamado de ótimo quando não existe certificado do CPLEX.

Os resultados evidenciam três comportamentos:

1. **Velocidade do Guloso.** O guloso foi cerca de 56,9 mil vezes mais rápido que ILS/SA_PD nos casos viáveis. Essa velocidade veio acompanhada de um desvio médio de 3,67% e apenas nove empates com o melhor valor observado.
2. **Qualidade do ILS.** O ILS atingiu o melhor valor observado nos 27 casos viáveis. Isso mostra que as perturbações corrigiram escolhas locais do construtivo dentro do limite de 3 segundos.
3. **Competitividade do SA_PD.** O SA_PD empatou com o melhor resultado em 26 dos 27 casos e teve desvio médio de apenas 0,15%, confirmando a eficácia da combinação SA + programação dinâmica nessa família.

O CPLEX encontrou incumbentes válidas nos 27 casos viáveis, mas todas essas execuções terminaram pelo limite de 10 segundos. Assim, seus resultados nesta bateria não são ótimos comprovados. O desvio elevado do incumbente do CPLEX em relação às heurísticas demonstra que o tempo de 10 segundos é insuficiente para uma comparação conclusiva de otimalidade, embora ilustre a dificuldade do MILP em produzir rapidamente boas incumbentes.

### 6.2 Família `vm1084`

A bateria consolidada disponível para `vm1084` contém 20 casos: cinco SOP e 15 SOPMV, divididos igualmente entre percentuais solicitados de 10%, 20% e 30%. Nessa bateria foram registrados ILS, Guloso e CPLEX; **não há resultados de SA_PD no arquivo consolidado**, portanto não é possível comparar os quatro métodos nessa família sem executar experimentos adicionais.

| Grupo | Casos | Viáveis pelo Guloso e pelo ILS | Objetivo médio do Guloso nos casos viáveis | Objetivo médio do ILS nos casos viáveis |
|---|---:|---:|---:|---:|
| SOP | 5 | 5 | 20.960,8 | 22.119,6 |
| SOPMV10 | 5 | 5 | 22.114,6 | 22.834,2 |
| SOPMV20 | 5 | 4 | 19.037,8 | 19.834,5 |
| SOPMV30 | 5 | 2 | 23.849,0 | 24.105,5 |

Entre os 16 casos em que ambos produziram solução, o ILS superou o Guloso em todos. O ganho relativo médio foi de 4,54%, com mediana de 2,65%. O tempo médio nos casos viáveis foi de 2,007 s para o ILS e 0,239 s para o Guloso, ou seja, o ILS consumiu aproximadamente 8,4 vezes mais tempo em troca de melhor qualidade.

O CPLEX não encontrou incumbente em nenhum dos 20 casos dentro do limite usado, cujo tempo médio observado foi 3,425 s. Esse resultado não prova inviabilidade: o estado registrado foi `NoFeasibleSolution`, e não `Infeasible`. Logo, nessa bateria o CPLEX não fornece valores de objetivo ou *gaps* para servir de fronteira quantitativa.

A redução de 5/5 soluções encontradas em SOPMV10 para 4/5 em SOPMV20 e 2/5 em SOPMV30 é compatível com o aumento da dificuldade de construção causado por mais visitas obrigatórias. Entretanto, `NoFeasibleSolutionFound` no Guloso ou no ILS significa apenas falha da heurística em construir uma solução; sem prova exata, não significa que a instância seja matematicamente inviável.

### 6.3 Limitações da comparação atual

Os resultados atuais permitem comparar qualidade e tempo dos métodos, mas ainda possuem limitações metodológicas:

- o limite de 10 segundos do CPLEX em `11berlin52` não foi suficiente para provar otimalidade nos casos viáveis;
- o limite do CPLEX em `vm1084` foi de aproximadamente 3,4 segundos em média e não produziu incumbentes;
- SA_PD ainda não aparece na bateria consolidada de `vm1084`;
- SA_PD e ILS são estocásticos, mas a tabela consolidada usa uma única semente por caso;
- os objetivos variam muito entre instâncias, especialmente em `vm1084`; por isso, médias brutas de objetivo devem ser interpretadas dentro de cada grupo, e comparações pareadas ou desvios relativos são mais informativos.

## 7. Conclusões parciais

O projeto já dispõe de uma cadeia experimental completa para o SOPMV: leitura das instâncias, geração reprodutível de obrigatórios, quatro resolvedores, validação independente e consolidação dos resultados.

Na família `11berlin52`, o ILS apresentou a melhor qualidade empírica, igualando o melhor objetivo observado em todos os 27 casos com solução. O SA_PD ficou muito próximo, com 26 melhores resultados ou empates. O Guloso confirmou seu papel de construtivo extremamente rápido e de boa qualidade inicial, embora inferior às meta-heurísticas. O CPLEX, sob o limite curto utilizado, não certificou ótimos nos casos viáveis e encontrou incumbentes piores que as heurísticas na maior parte deles.

Na família `vm1084`, o crescimento do problema tornou o contraste ainda mais claro: o Guloso produziu soluções rapidamente, e o ILS melhorou todas as 16 soluções pareadas, com ganho médio de 4,54%. O CPLEX não encontrou incumbentes no limite adotado. Isso sustenta a utilidade prática das heurísticas para instâncias grandes, mas ainda não permite medir o *gap* em relação ao ótimo.

## 8. Próximas etapas recomendadas

1. Executar o SA_PD nos mesmos 20 casos de `vm1084` para completar a comparação entre os quatro métodos.
2. Aumentar substancialmente o limite de tempo do CPLEX e registrar incumbente, melhor limite e *gap* relativo; para `vm1084`, considerar *warm start* com a solução do ILS.
3. Repetir SA_PD e ILS com múltiplas sementes e reportar média, mediana, desvio-padrão, melhor e pior resultado.
4. Usar comparações pareadas por instância e separar claramente “*gap* para o ótimo comprovado” de “desvio para o melhor valor observado”.
5. Avaliar uma fase de reparo ou reinícios no ILS quando o guloso não encontra uma construção viável, pois a implementação atual depende da viabilidade da solução inicial.
6. Documentar hardware, compilador, versão do CPLEX, número de *threads* e limites de tempo de forma uniforme para garantir reprodutibilidade.

## 9. Fontes dos dados deste relatório

- Artigo de referência: `docs/referencias/lin_guo_wu_2024.pdf`;
- resultados consolidados de `11berlin52`: `experiments/berlin52_comparacao_4_solvers/results_4_solvers.csv` e `experiments/berlin52_comparacao_4_solvers/summary_4_solvers.csv`;
- comparação por instância: `experiments/berlin52_comparacao_4_solvers/comparison_by_instance.csv`;
- resultados consolidados de `vm1084`: `experiments/vm1084_comparacao/resultados.csv`;
- implementações: `src/cplex/sopmv_model.cpp`, `src/greedy/greedy.cpp`, `src/ils/ils.cpp` e `src/sa_pd/sa_pd.cpp`.
