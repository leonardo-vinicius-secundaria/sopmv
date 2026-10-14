# Relatório de progresso do Trabalho de Conclusão de Curso

## Set Orienteering Problem with Mandatory Visits

Este relatório apresenta o progresso do Trabalho de Conclusão de Curso sobre o Set Orienteering Problem with Mandatory Visits, representado pela sigla S O P M V.

O trabalho utiliza como principal referência o artigo de Lin, Guo e Wu, publicado em 2024. O título do artigo, em tradução livre, é: Aplicação do algoritmo Simulated Annealing ao problema de orientação por conjuntos com visitas obrigatórias.

## 1. Apresentação do problema

O problema estudado envolve um conjunto de pontos que podem ser visitados. Esses pontos são organizados em grupos, chamados de conjuntos ou clusters. Cada conjunto oferece uma recompensa quando pelo menos um de seus pontos é visitado.

O objetivo é construir uma rota que comece no depósito, visite alguns pontos e termine novamente no depósito. A rota deve obter a maior recompensa possível sem ultrapassar o limite máximo de deslocamento.

Esse limite recebe o nome de T M A X. Ele representa o orçamento máximo de viagem. Em outras palavras, a soma de todas as distâncias percorridas na rota deve ser menor ou igual ao T M A X.

Por exemplo, se o T M A X for igual a cem, uma rota com distância total igual a noventa e cinco será permitida. Uma rota com distância igual a cento e cinco não será permitida.

O principal desafio é encontrar um equilíbrio. Visitar mais conjuntos pode aumentar a recompensa, mas também aumenta a distância percorrida. Por isso, nem sempre é possível visitar todos os conjuntos.

Existem duas variantes principais neste trabalho.

Na primeira variante, chamada de S O P, todos os conjuntos com recompensa são opcionais. O algoritmo escolhe quais conjuntos vale a pena visitar.

Na segunda variante, chamada de S O P M V, alguns conjuntos possuem visita obrigatória. Esses conjuntos precisam aparecer na rota, mesmo que possuam uma relação menos vantajosa entre recompensa e distância. Depois de atender os conjuntos obrigatórios, o algoritmo pode incluir conjuntos opcionais caso ainda exista espaço no limite de viagem.

## 2. Esclarecimentos importantes

A sigla S O P M V significa Set Orienteering Problem with Mandatory Visits. Em português, significa problema de orientação por conjuntos com visitas obrigatórias.

Esse problema não possui restrições de precedência. Isso significa que não existe uma regra dizendo, por exemplo, que o conjunto A deve ser visitado antes do conjunto B. A ordem das visitas é escolhida pelos algoritmos com o objetivo de melhorar a rota.

A implementação atual trabalha com apenas um veículo e uma rota. Nos nomes das instâncias aparecem termos como M V dez, M V vinte e M V trinta. Esses termos representam aproximadamente dez, vinte e trinta por cento de conjuntos obrigatórios. Eles não representam a quantidade de veículos.

## 3. Progresso realizado

O desenvolvimento do trabalho ocorreu em etapas.

Primeiro, foi estudada a definição do problema e o artigo de referência.

Depois, foi implementado um leitor de instâncias. Esse leitor identifica os pontos, os conjuntos, as recompensas, as distâncias, o depósito e o limite T M A X.

Também foi criado um gerador de conjuntos obrigatórios. Esse gerador permite transformar uma instância comum de S O P em uma variante de S O P M V. A geração utiliza uma semente, o que permite repetir o experimento e obter os mesmos conjuntos obrigatórios.

Em seguida, foram implementados quatro métodos de solução.

O primeiro foi o C P L E X, usado para resolver um modelo matemático exato.

O segundo foi o algoritmo Guloso, usado para construir soluções de forma muito rápida.

O terceiro foi o Iterated Local Search, chamado de I L S. Ele utiliza a solução do Guloso como ponto de partida e tenta melhorá-la.

O quarto foi o Simulated Annealing com programação dinâmica, chamado neste projeto de S A P D.

Por fim, foi implementado um validador independente. Ele verifica se a rota começa e termina no depósito, se respeita o T M A X, se a recompensa foi calculada corretamente e se todos os conjuntos obrigatórios foram atendidos.

## 4. Funcionamento do algoritmo Guloso

O algoritmo Guloso constrói uma solução aos poucos. Ele começa com uma rota simples, que sai do depósito e retorna diretamente para o mesmo depósito.

No S O P M V, o algoritmo atende primeiro os conjuntos obrigatórios. Para isso, ele testa os pontos de cada conjunto e as diferentes posições em que esses pontos podem ser colocados na rota.

O algoritmo escolhe a inserção que provoca o menor aumento de distância. Antes de fazer a inserção, ele verifica se a nova rota continua dentro do T M A X.

Se algum conjunto obrigatório não puder ser incluído sem ultrapassar o T M A X, o Guloso encerra sem apresentar uma solução viável.

Depois de atender todos os conjuntos obrigatórios, o algoritmo analisa os conjuntos opcionais. Nesse momento, ele procura uma boa relação entre a recompensa recebida e o aumento de distância provocado pela visita.

Um conjunto com boa recompensa e baixo aumento de distância recebe prioridade. O processo continua enquanto for possível adicionar conjuntos sem ultrapassar o limite da rota.

Após cada inserção, o algoritmo tenta reduzir a distância da rota de duas maneiras.

A primeira maneira é testar outro ponto do mesmo conjunto. Como um conjunto pode possuir vários pontos, o algoritmo procura o representante que se encaixa melhor na rota.

A segunda maneira utiliza uma melhoria chamada dois opt. Essa melhoria reorganiza uma parte da rota quando a mudança reduz a distância percorrida.

O Guloso é determinístico. Isso significa que a mesma instância produz sempre o mesmo resultado. Sua principal vantagem é a velocidade.

Sua principal limitação é tomar decisões com base no melhor ganho daquele momento. Uma escolha que parece boa no início pode impedir uma combinação melhor no restante da rota.

## 5. Funcionamento do Iterated Local Search

O Iterated Local Search, ou I L S, foi implementado para melhorar as soluções produzidas pelo Guloso.

O processo começa com a rota construída pelo Guloso. Essa rota passa a ser a solução inicial, a solução atual e a melhor solução conhecida naquele momento.

Em seguida, o I L S aplica uma busca local. Essa busca tenta escolher representantes melhores para os conjuntos, reorganizar partes da rota com o movimento dois opt e inserir conjuntos que ainda não foram atendidos.

Depois da busca local, o algoritmo aplica uma perturbação. A perturbação remove alguns conjuntos opcionais e pode inverter uma parte da sequência de visitas.

Os conjuntos obrigatórios nunca são removidos durante essa etapa.

A função da perturbação é permitir que o algoritmo abandone uma organização que parece boa localmente, mas que pode não ser a melhor solução disponível.

Depois da perturbação, a busca local é executada novamente. Se a nova solução possuir recompensa maior, ela substitui a solução anterior. Se as recompensas forem iguais, o algoritmo prefere a rota de menor distância.

Esse ciclo de perturbação e melhoria continua até que o limite de tempo ou de iterações seja alcançado.

O I L S consegue revisar escolhas feitas durante a construção gulosa. Por isso, normalmente encontra soluções melhores, mas utiliza mais tempo de processamento.

## 6. Funcionamento do S A P D

O S A P D combina o Simulated Annealing com programação dinâmica. Esse método foi adaptado a partir da proposta apresentada no artigo de referência.

O Simulated Annealing modifica a ordem dos conjuntos na rota. Essas modificações podem trocar dois conjuntos de posição, mover um conjunto para outra posição ou inverter uma parte da sequência.

A programação dinâmica avalia cada sequência criada. Ela escolhe os melhores pontos representantes dos conjuntos e identifica quantos conjuntos podem ser visitados antes que o limite T M A X seja ultrapassado.

O algoritmo normalmente aceita alterações que melhoram a solução. No entanto, ele também pode aceitar temporariamente uma solução pior.

No início da execução, a chance de aceitar uma piora é maior. Essa chance diminui conforme a temperatura do algoritmo é reduzida. Esse comportamento ajuda a escapar de soluções que são boas apenas em uma pequena região da busca.

No S O P M V, o algoritmo aplica uma penalização quando algum conjunto obrigatório não aparece na parte viável da rota. Quanto maior o número de conjuntos obrigatórios ausentes, pior será a avaliação da solução.

A melhor solução apresentada ao final deve respeitar o T M A X e atender todos os conjuntos obrigatórios.

## 7. Papel do C P L E X

O C P L E X resolve uma formulação matemática do problema. O modelo possui variáveis que indicam os deslocamentos realizados, os pontos visitados e os conjuntos atendidos.

O objetivo do modelo é maximizar a soma das recompensas. Ao mesmo tempo, ele garante que a rota comece e termine no depósito, permaneça conectada, respeite o T M A X e visite todos os conjuntos obrigatórios.

Por ser um método exato, o C P L E X pode comprovar que uma solução é ótima. Entretanto, essa comprovação pode exigir muito tempo.

Quando o C P L E X termina com o estado ótimo e diferença de otimalidade igual a zero, existe uma prova de que nenhuma solução melhor está disponível.

Quando a execução termina por limite de tempo, a melhor rota encontrada continua sendo válida, mas não existe garantia de que seja a melhor rota possível.

Por isso, os resultados do C P L E X devem ser interpretados com cuidado. O fato de o modelo ser exato não significa que toda execução limitada por tempo encontrou o valor ótimo.

## 8. Significado das principais medidas

Uma solução viável é uma rota que respeita todas as regras do problema. Ela começa e termina no depósito, não ultrapassa o T M A X e atende todos os conjuntos obrigatórios.

Uma solução viável não precisa ser a melhor solução encontrada.

O melhor valor observado em uma instância é a maior recompensa obtida entre os algoritmos executados naquela mesma instância. Neste projeto, essa comparação pode envolver C P L E X, S A P D, Guloso e I L S.

Por exemplo, imagine que o C P L E X obtenha recompensa noventa, o Guloso obtenha noventa e cinco, e o S A P D e o I L S obtenham cem.

Nesse caso, os quatro algoritmos podem ter encontrado soluções viáveis. No entanto, apenas o S A P D e o I L S empataram com o melhor valor observado, que foi cem.

O melhor valor observado não deve ser chamado automaticamente de valor ótimo. Para utilizar a palavra ótimo, é necessário que um método exato comprove que nenhuma solução melhor existe.

A qualidade relativa compara a recompensa de um algoritmo com o melhor valor observado naquela instância. Uma qualidade de cem por cento significa que o algoritmo alcançou o melhor valor observado. Uma qualidade de noventa e cinco por cento significa que sua recompensa corresponde a noventa e cinco por cento do melhor valor observado.

## 9. Resultados da família Berlin cinquenta e dois

A primeira bateria consolidada analisada possui trinta e dois casos derivados da família Berlin cinquenta e dois.

Oito casos são do tipo S O P. Os outros vinte e quatro são do tipo S O P M V, com diferentes percentuais de conjuntos obrigatórios.

Cada caso foi executado com os quatro métodos. Isso produziu cento e vinte e oito execuções no total.

O C P L E X recebeu um limite de dez segundos por execução. O S A P D e o I L S utilizaram aproximadamente três segundos. O Guloso terminou em uma pequena fração de segundo.

Dos trinta e dois casos, todos os algoritmos encontraram soluções viáveis em vinte e sete.

Nos cinco casos restantes, nenhum dos quatro métodos apresentou uma rota viável. O C P L E X comprovou que quatro desses casos eram inviáveis. No quinto caso, o C P L E X terminou sem encontrar uma solução, mas também sem comprovar a inviabilidade.

O Guloso encontrou vinte e sete soluções viáveis entre os trinta e dois casos. Entre essas vinte e sete soluções, nove alcançaram o melhor valor observado entre os quatro métodos.

Isso não significa que o Guloso encontrou apenas nove soluções. Ele encontrou vinte e sete soluções viáveis. Em nove delas, a recompensa foi igual à maior recompensa encontrada naquela instância.

O desvio médio do Guloso em relação ao melhor valor observado foi de três vírgula sessenta e sete por cento. Seu tempo médio nos casos viáveis foi de aproximadamente cinquenta e três milionésimos de segundo.

O I L S encontrou vinte e sete soluções viáveis e alcançou o melhor valor observado em todos esses casos. Seu tempo médio foi de aproximadamente três segundos.

O S A P D também encontrou vinte e sete soluções viáveis. Ele alcançou o melhor valor observado em vinte e seis casos. Seu desvio médio foi de apenas zero vírgula quinze por cento, com tempo médio próximo de três segundos.

O C P L E X encontrou vinte e sete soluções viáveis, mas alcançou o melhor valor observado em apenas dois casos. Seu desvio médio foi de dezenove vírgula cinquenta por cento.

Todas as vinte e sete execuções viáveis do C P L E X terminaram pelo limite de dez segundos. Portanto, essas soluções não foram comprovadas como ótimas.

Esses resultados mostram que o Guloso é muito rápido e produz boas soluções iniciais. O I L S conseguiu melhorar essas soluções e obteve a melhor qualidade empírica da bateria. O S A P D apresentou resultados muito próximos aos do I L S.

## 10. Resultados da bateria de testes ampliada

Existe também uma bateria ampliada com duzentas e oitenta e oito execuções. Nela, cada algoritmo foi executado em setenta e dois casos.

Nessa bateria, o Guloso encontrou sessenta e sete soluções viáveis em setenta e dois casos. Isso representa uma taxa de solução viável de aproximadamente noventa e três vírgula zero seis por cento.

A qualidade média do Guloso foi de aproximadamente noventa e oito vírgula setenta e nove por cento em relação ao melhor valor observado em cada instância.

Essas duas porcentagens representam medidas diferentes.

Os noventa e três vírgula zero seis por cento informam em quantos casos o Guloso conseguiu construir uma rota viável.

Os noventa e oito vírgula setenta e nove por cento informam a qualidade média das soluções viáveis do Guloso quando comparadas com as melhores recompensas observadas.

Nessa bateria ampliada, o Guloso empatou com o melhor valor observado em quarenta e sete dos sessenta e sete casos viáveis.

## 11. Resultados da família V M mil e oitenta e quatro

A bateria consolidada da família V M mil e oitenta e quatro possui vinte casos.

Cinco casos são do tipo S O P. Os outros quinze são do tipo S O P M V, com diferentes percentuais de conjuntos obrigatórios.

Nessa bateria foram registrados resultados do Guloso, do I L S e do C P L E X. Ainda não existem resultados consolidados do S A P D para essa família.

O Guloso e o I L S encontraram soluções viáveis nos mesmos dezesseis casos.

Nos cinco casos de S O P, os dois métodos encontraram soluções em todas as instâncias.

Nos cinco casos com aproximadamente dez por cento de conjuntos obrigatórios, os dois métodos também encontraram soluções em todas as instâncias.

Nos cinco casos com aproximadamente vinte por cento de conjuntos obrigatórios, foram encontradas soluções em quatro instâncias.

Nos cinco casos com aproximadamente trinta por cento de conjuntos obrigatórios, foram encontradas soluções em duas instâncias.

O I L S obteve recompensa maior que o Guloso em todos os dezesseis casos nos quais os dois produziram soluções. O ganho relativo médio foi de quatro vírgula cinquenta e quatro por cento.

O tempo médio do Guloso nos casos viáveis foi de aproximadamente zero vírgula vinte e quatro segundo. O tempo médio do I L S foi de aproximadamente dois segundos.

Assim, o I L S utilizou mais tempo, mas produziu soluções de maior recompensa.

O C P L E X não encontrou uma solução inicial viável em nenhum dos vinte casos dentro do limite utilizado. Esse resultado não prova que as instâncias sejam inviáveis. Ele mostra apenas que o C P L E X não encontrou uma rota no tempo disponível.

A redução no número de soluções encontradas quando aumenta a quantidade de visitas obrigatórias indica que o problema se torna mais restritivo. Mesmo assim, quando uma heurística não encontra uma solução, não é possível concluir automaticamente que a instância seja inviável.

## 12. Limitações dos experimentos atuais

Os experimentos realizados permitem comparar o tempo e a qualidade dos algoritmos, mas ainda existem algumas limitações.

O limite de dez segundos do C P L E X na família Berlin cinquenta e dois não foi suficiente para comprovar a solução ótima nos casos viáveis.

Na família V M mil e oitenta e quatro, o tempo do C P L E X também foi curto e não produziu soluções iniciais viáveis.

O S A P D ainda precisa ser executado nos mesmos casos da família V M mil e oitenta e quatro.

Além disso, o S A P D e o I L S utilizam decisões aleatórias. Para uma análise mais completa, esses algoritmos devem ser executados várias vezes com sementes diferentes.

Também é importante separar duas medidas. A primeira é a diferença para um valor ótimo comprovado. A segunda é a diferença para o melhor valor apenas observado nos experimentos.

## 13. Conclusões parciais

O projeto já possui os principais componentes necessários para estudar o S O P M V.

Foram implementados o leitor das instâncias, o gerador de conjuntos obrigatórios, o modelo matemático no C P L E X, o algoritmo Guloso, o I L S, o S A P D e um validador independente.

O Guloso demonstrou ser uma boa alternativa para produzir soluções rapidamente. Ele também fornece um ponto de partida importante para o I L S.

O I L S apresentou a melhor qualidade empírica na família Berlin cinquenta e dois e melhorou todas as soluções comparáveis do Guloso na família V M mil e oitenta e quatro.

O S A P D apresentou desempenho muito próximo ao do I L S na família Berlin cinquenta e dois, confirmando a utilidade da combinação entre Simulated Annealing e programação dinâmica.

O C P L E X continua sendo importante para obter provas de otimalidade e de inviabilidade. Entretanto, os limites de tempo utilizados até agora foram insuficientes para uma comparação completa com os métodos heurísticos.

Os resultados indicam que as heurísticas são especialmente úteis quando as instâncias crescem e o modelo exato passa a exigir muito tempo.

## 14. Próximas etapas

A primeira próxima etapa é executar o S A P D nos vinte casos da família V M mil e oitenta e quatro.

A segunda etapa é aumentar o tempo disponível para o C P L E X. Também pode ser usada uma solução do I L S como ponto de partida para o modelo exato.

A terceira etapa é repetir o I L S e o S A P D com diferentes sementes. Com isso, será possível calcular a média, a variação, o melhor resultado e o pior resultado de cada algoritmo.

A quarta etapa é melhorar o comportamento do I L S quando o Guloso não encontra uma solução inicial viável. Uma possibilidade é implementar uma fase de reparo ou diferentes formas de reiniciar a construção.

A quinta etapa é registrar de forma uniforme as informações do ambiente de testes. Entre essas informações estão o processador utilizado, a memória, o compilador, a versão do C P L E X, o número de núcleos de processamento e os limites de tempo.

Essas etapas permitirão uma comparação mais completa, justa e reproduzível entre os algoritmos.

