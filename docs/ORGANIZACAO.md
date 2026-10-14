# Organização do projeto

Cada diretório de primeiro nível possui uma única responsabilidade:

- `data/`: instâncias que servem como entrada dos resolvedores;
- `src/`: implementação C++, com código comum em `core/` e um diretório por método;
- `tests/`: testes automatizados e dados pequenos exclusivos dos testes;
- `scripts/`: geração, execução, consolidação e visualização;
- `experiments/`: saídas produzidas por execuções e insumos históricos associados;
- `visualization/`: dashboard geral para consultar resultados;
- `docs/`: documentação do trabalho e referências;
- `build/`: arquivos regeneráveis de compilação;
- `archive/`: backups antigos mantidos apenas para consulta.

## Convenção para experimentos

Use nomes que descrevam família, comparação e, quando necessário, data ou
parâmetros. Evite sequências como `teste`, `teste_2` e `final_novo`.

Exemplo:

```text
experiments/berlin52_cplex-ils-sa_seed-202601_2026-10-07/
├── config.json
├── raw/
├── resultados.csv
└── resumo.csv
```

O arquivo `config.json` deve registrar pelo menos a semente, os resolvedores,
limites de tempo e as famílias de instâncias. Resultados incompletos ou apenas
exploratórios devem ficar em `experiments/archive/`, com um nome que diferencie
cada execução.

Experimentos históricos podem manter uma cópia de seus insumos em `inputs/`
quando isso for necessário para reproduzir exatamente a execução. Fora desse
caso, os scripts devem ler as instâncias canônicas diretamente de `data/`.

## Migração dos nomes antigos

| Nome antigo | Local atual |
|---|---|
| `instancias  11_berlin/` | `data/berlin52/` |
| `instancia_vm1084/` | `data/vm1084/` |
| `benchmark_11berlin52/` | `experiments/berlin52_comparacao_4_solvers/` |
| `bateria_completa/` | `experiments/berlin52_bateria_completa/` |
| `bateria_teste/` | `experiments/archive/berlin52_teste_execucao_01/` |
| `bateria_teste_2/` | `experiments/archive/berlin52_teste_execucao_02/` |
| `resultados_vm1084/` | `experiments/vm1084_comparacao/` |
| `resultados_vm1084_ils/` | `experiments/vm1084_ils_10s/` |
| `results/` | `experiments/smoke_tests/` |
| `visualizacao_resultados/` | `visualization/` |
| `bin/` | `build/bin/` |
| `CPLEX/` | `data/berlin52/sop/` e `data/berlin52/mandatory_sets/` |
