#!/usr/bin/env bash
# Nao regressao: VNS original (inalterado) x copia VNS adaptada.
# Uso: ./scripts/run_vns_nonregression.sh [repeticoes]
# O original nao aceita seed; cada repeticao dele usa a semente do relogio.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ORIGINAL=${VNS_ORIGINAL_BIN:-/home/leo/vns-sop/sources/sop_vns}
ADAPTED=${VNS_ADAPTED_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
source "$ROOT/config/benchmark_ils_vns.env"
RUNS=${1:-5}
[[ "$RUNS" =~ ^[1-9][0-9]*$ ]] || { echo "Repeticoes deve ser inteiro positivo" >&2; exit 2; }
OUT="$ROOT/new_experiments/vns_nonregression_$(date +%Y%m%d_%H%M%S)"
[[ -x "$ORIGINAL" && -x "$ADAPTED" ]] || { echo "Binario VNS ausente" >&2; exit 2; }
mkdir -p "$OUT"

# Seis pequenas e tres grandes, cobrindo 12, 81, 145 e 218 conjuntos.
instances=(
  "$ROOT/data/instancias_pequenas/sop/11berlin52_T40_p1.sop"
  "$ROOT/data/instancias_pequenas/sop/11berlin52_T60_p1.sop"
  "$ROOT/data/instancias_pequenas/sop/11berlin52_T80_p1.sop"
  "$ROOT/data/instancias_pequenas/sop/11berlin52_T40_p2.sop"
  "$ROOT/data/instancias_pequenas/sop/11berlin52_T60_p2.sop"
  "$ROOT/data/instancias_pequenas/sop/11berlin52_T80_p2.sop"
  "$ROOT/data/intancias_grandes/sop/80rd400_T80_p1.sop"
  "$ROOT/data/intancias_grandes/sop/145u724_T80_p1.sop"
  "$ROOT/data/intancias_grandes/sop/217vm1084_T80_p1.sop"
)
for instance in "${instances[@]}"; do
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
done

printf 'solver,instance,run,seed,sets,time_limit_seconds,reward,distance,iterations,validation\n' > "$OUT/results.csv"
printf 'runs=%s\n' "$RUNS" > "$OUT/run_config.txt"
printf '%s\n' "${instances[@]}" > "$OUT/instances.txt"

run_one() {
  local solver=$1 bin=$2 instance=$3 run=$4 seed=$5 limit=$6 sets=$7
  local name work record reward distance iterations validation
  name=$(basename "$instance" .sop)
  work="$OUT/$solver/${name}/run_${run}"
  mkdir -p "$work"
  local args=(--problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 \
    --output="$work" --results=results.log --save-results=1 --save-info=0 \
    --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 \
    --initial-greedy-solution=1 --use-rvns=0 --maximal-calculation-time-sec="$limit" \
    --num-iterations=2147483647 --num-iterations-unimproved=2147483647)
  if [[ "$solver" == adapted ]]; then
    args+=(--seed="$seed" --time-only-stop=1)
  fi
  "$bin" "${args[@]}" >"$work/stdout.log" 2>&1
  validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log")
  record=$(tail -n 1 "$work/results.log")
  reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
  distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
  iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,"%s"\n' \
    "$solver" "$name" "$run" "$seed" "$sets" "$limit" "$reward" "$distance" "$iterations" "$validation" \
    >> "$OUT/results.csv"
}

for instance in "${instances[@]}"; do
  sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  limit=$(( (3 * sets + 1) / 2 )) # ceil(1.5 * SETS)
  for ((run=1; run<=RUNS; run++)); do
    run_one original "$ORIGINAL" "$instance" "$run" "clock" "$limit" "$sets"
    run_one adapted "$ADAPTED" "$instance" "$run" "$((202600 + run))" "$limit" "$sets"
  done
done

echo "Concluido: $OUT"
