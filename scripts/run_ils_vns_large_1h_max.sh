#!/usr/bin/env bash
# Piloto ILS x VNS em SOP: maximo de instancias grandes que cabe em ~1 hora.
# Usa somente T80_p1, sem as variantes RND (uma instancia por familia), e uma
# semente. Os 5 minutos restantes sao reserva para E/S e validacao.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/config/benchmark_ils_vns.env"
ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
VNS_BIN=${VNS_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
SEED=202601
MAX_SOLVER_SECONDS=3300 # 55 min: 5 min reservados para overhead.
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/ils_vns_large_1h_max_${STAMP}"
DATA_DIR="$ROOT/data/intancias_grandes/sop"

[[ -x "$ILS_BIN" && -x "$VNS_BIN" ]] || {
  echo "ILS ou VNS adaptado nao compilado" >&2
  exit 2
}
mkdir -p "$OUT/raw_vns" "$OUT/logs/ils" "$OUT/logs/vns"
printf 'solver,instance,seed,sets,time_limit_seconds,variant\n' > "$OUT/manifest.csv"
printf 'instance,seed,sets,time_limit_seconds,reward,distance,iterations,validation\n' > "$OUT/vns_results.csv"

# Cada instancia consome 2 * ceil(1.5 * SETS): uma execucao ILS e uma VNS.
# Ordenar por SETS maximiza a quantidade de instancias sob o mesmo orcamento.
mapfile -t CANDIDATES < <(
  for instance in "$DATA_DIR"/*_T80_p1.sop; do
    [[ "$(basename "$instance")" == *_RND_* ]] && continue
    sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
    printf '%08d\t%s\n' "$sets" "$instance"
  done | sort -n
)

INSTANCES=()
used=0
for row in "${CANDIDATES[@]}"; do
  sets=${row%%$'\t'*}
  instance=${row#*$'\t'}
  limit=$(( (3 * 10#$sets + 1) / 2 )) # ceil(1.5 * SETS)
  cost=$((2 * limit))
  (( used + cost <= MAX_SOLVER_SECONDS )) || continue
  INSTANCES+=("$instance")
  used=$((used + cost))
done

(( ${#INSTANCES[@]} > 0 )) || { echo "Nenhuma instancia selecionada" >&2; exit 2; }
printf '%s\n' "${INSTANCES[@]}" > "$OUT/selected_instances.txt"
printf 'seed=%s\nsolver_budget_seconds=%s\nselected_instances=%s\n' \
  "$SEED" "$used" "${#INSTANCES[@]}" > "$OUT/run_config.txt"
echo "Selecionadas ${#INSTANCES[@]} instancias; orcamento dos solvers: ${used}s (mais overhead)."

for instance in "${INSTANCES[@]}"; do
  name=$(basename "$instance" .sop)
  sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  limit=$(( (3 * 10#$sets + 1) / 2 ))

  printf 'ILS,%s,%s,%s,%s,large-sop-1h-max\n' "$name" "$SEED" "$sets" "$limit" >> "$OUT/manifest.csv"
  "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 \
    --ils-time-limit "$limit" --ils-reset-interval "$ILS_RESET_INTERVAL" \
    --seed "$SEED" --csv "$OUT/ils_results.csv" \
    >"$OUT/logs/ils/${name}_seed${SEED}.log" 2>&1

  work="$OUT/raw_vns/${name}_seed${SEED}"
  mkdir -p "$work"
  printf 'VNS,%s,%s,%s,%s,large-sop-1h-max\n' "$name" "$SEED" "$sets" "$limit" >> "$OUT/manifest.csv"
  "$VNS_BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 \
    --output="$work" --results=results.log --save-results=1 --save-info=0 \
    --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 \
    --initial-greedy-solution=1 --use-rvns=0 --seed="$SEED" --time-only-stop=1 \
    --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 \
    --num-iterations-unimproved=2147483647 \
    >"$OUT/logs/vns/${name}_seed${SEED}.log" 2>&1

  validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log")
  record=$(tail -n 1 "$work/results.log")
  reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
  distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
  iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
  printf '%s,%s,%s,%s,%s,%s,%s,"%s"\n' \
    "$name" "$SEED" "$sets" "$limit" "$reward" "$distance" "$iterations" "$validation" \
    >> "$OUT/vns_results.csv"
done

echo "Concluido: $OUT"
