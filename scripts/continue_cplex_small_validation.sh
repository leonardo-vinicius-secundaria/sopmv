#!/usr/bin/env bash
# Continua a validacao CPLEX interrompida em 2026-10-30, sem repetir casos ja concluidos.
# Executa: 19 instancias SOPMV20 restantes e as 20 SOPMV30.
# Uso: ./scripts/continue_cplex_small_validation.sh [limite_em_segundos]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN=${CPLEX_BIN:-"$ROOT/build/bin/sopmv_cplex_branch_cut"}
LIMIT=${1:-600}
[[ "$LIMIT" =~ ^[1-9][0-9]*([.][0-9]+)?$ ]] || { echo "Limite deve ser positivo" >&2; exit 2; }
[[ -x "$BIN" ]] || { echo "CPLEX branch-and-cut ausente: $BIN" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/cplex_small_validation_continuation_${STAMP}"
mkdir -p "$OUT/logs"
CSV="$OUT/cplex_results.csv"

printf 'time_limit_seconds=%s\nthreads=1\nmip_gap=0\nseed=202601\nsolver=branch_and_cut\n' "$LIMIT" > "$OUT/run_config.txt"
printf 'source_experiment=%s\n' \
  "$ROOT/new_experiments/cplex_small_validation_20261030_081715" >> "$OUT/run_config.txt"

INSTANCES=()
# O primeiro SOPMV20 ja foi concluido antes do desligamento.
while IFS= read -r instance; do INSTANCES+=("sopmv_20:small:$instance"); done < <(
  find "$ROOT/data/instancias_pequenas/sopmv_20" -maxdepth 1 -type f -name '*.sop' | sort | tail -n +2
)
while IFS= read -r instance; do INSTANCES+=("sopmv_30:small:$instance"); done < <(
  find "$ROOT/data/instancias_pequenas/sopmv_30" -maxdepth 1 -type f -name '*.sop' | sort
)

[[ ${#INSTANCES[@]} -eq 39 ]] || {
  echo "Esperava 39 instancias pendentes; encontrei ${#INSTANCES[@]}. Abortando por seguranca." >&2
  exit 2
}

printf 'family,size,instance,exit_code\n' > "$OUT/manifest.csv"
for item in "${INSTANCES[@]}"; do
  IFS=: read -r family size instance <<< "$item"
  name=$(basename "$instance" .sop)
  echo "Executando: $family/$name (limite ${LIMIT}s)"
  set +e
  "$BIN" --instance "$instance" --time-limit "$LIMIT" --threads 1 --mip-gap 0 \
    --seed 202601 --log-level 0 --csv "$CSV" \
    >"$OUT/logs/${family}_${name}.log" 2>&1
  code=$?
  set -e
  # 0: incumbente/otimo/limite; 4: inviabilidade formal provada pelo CPLEX.
  if [[ "$code" != 0 && "$code" != 4 ]]; then
    echo "Falha CPLEX (codigo $code): $family/$name. Veja o log correspondente." >&2
    exit "$code"
  fi
  printf '%s,%s,%s,%s\n' "$family" "$size" "$name" "$code" >> "$OUT/manifest.csv"
done

echo "Concluido: $OUT"
awk -F, 'NR > 1 {status[$5]++} END {for(s in status) printf "%s: %d\\n", s, status[s]}' "$CSV" | sort
