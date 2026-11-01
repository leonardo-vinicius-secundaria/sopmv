#!/usr/bin/env bash
# Reavalia somente as tres instancias SOPMV sem incumbente no teste de 600 s.
# Uso: ./scripts/run_cplex_unresolved_sopmv.sh [limite_em_segundos]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN=${CPLEX_BIN:-"$ROOT/build/bin/sopmv_cplex_branch_cut"}
LIMIT=${1:-3600}
[[ "$LIMIT" =~ ^[1-9][0-9]*([.][0-9]+)?$ ]] || { echo "Limite deve ser positivo" >&2; exit 2; }
[[ -x "$BIN" ]] || { echo "CPLEX branch-and-cut ausente: $BIN" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/cplex_sopmv_unresolved_${STAMP}"
mkdir -p "$OUT/logs"
CSV="$OUT/cplex_results.csv"
printf 'time_limit_seconds=%s\nthreads=1\nmip_gap=0\nseed=202601\nsolver=branch_and_cut\npurpose=resolve_sopmv_instances_without_incumbent_at_600s\n' \
  "$LIMIT" > "$OUT/run_config.txt"

INSTANCES=(
  "sopmv_20:11berlin52_T40_p2"
  "sopmv_30:14st70_T80_p2"
  "sopmv_10:16eil76_T40_p2"
)

printf 'family,instance,exit_code\n' > "$OUT/manifest.csv"
for item in "${INSTANCES[@]}"; do
  IFS=: read -r family name <<< "$item"
  instance="$ROOT/data/instancias_pequenas/$family/$name.sop"
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
  echo "Executando: $family/$name (limite ${LIMIT}s)"
  set +e
  "$BIN" --instance "$instance" --time-limit "$LIMIT" --threads 1 --mip-gap 0 \
    --seed 202601 --log-level 0 --csv "$CSV" \
    >"$OUT/logs/${family}_${name}.log" 2>&1
  code=$?
  set -e
  if [[ "$code" != 0 && "$code" != 4 ]]; then
    echo "Falha CPLEX (codigo $code): $family/$name. Veja o log." >&2
    exit "$code"
  fi
  printf '%s,%s,%s\n' "$family" "$name" "$code" >> "$OUT/manifest.csv"
done

echo "Concluido: $OUT"
awk -F, 'NR > 1 {status[$5]++} END {for(s in status) printf "%s: %d\\n", s, status[s]}' "$CSV" | sort
