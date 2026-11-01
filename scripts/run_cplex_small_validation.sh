#!/usr/bin/env bash
# Valida a implementacao propria MILP/CPLEX (branch-and-cut) nas instancias pequenas.
# Uso: ./scripts/run_cplex_small_validation.sh [limite_em_segundos]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN=${CPLEX_BIN:-"$ROOT/build/bin/sopmv_cplex_branch_cut"}
LIMIT=${1:-600}
[[ "$LIMIT" =~ ^[1-9][0-9]*([.][0-9]+)?$ ]] || { echo "Limite deve ser positivo" >&2; exit 2; }
[[ -x "$BIN" ]] || { echo "CPLEX branch-and-cut ausente: $BIN" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/cplex_small_validation_${STAMP}"
mkdir -p "$OUT/logs"
CSV="$OUT/cplex_results.csv"
printf 'time_limit_seconds=%s\nthreads=1\nmip_gap=0\nseed=202601\nsolver=branch_and_cut\n' "$LIMIT" > "$OUT/run_config.txt"

INSTANCES=()
while IFS= read -r instance; do INSTANCES+=("SOP:small:$instance"); done < <(
  find "$ROOT/data/instancias_pequenas/sop" -maxdepth 1 -type f -name '*.sop' | sort
)
for group in sopmv_10 sopmv_20 sopmv_30; do
  while IFS= read -r instance; do INSTANCES+=("$group:small:$instance"); done < <(
    find "$ROOT/data/instancias_pequenas/$group" -maxdepth 1 -type f -name '*.sop' | sort
  )
done

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
awk -F, 'NR > 1 {status[$5]++} END {for(s in status) printf "%s: %d\n", s, status[s]}' "$CSV" | sort
