#!/usr/bin/env bash
# Executa CPLEX branch-and-cut, ILS e VNS somente nos substitutos isolados.
# Uso: ./scripts/run_feasible_sopmv_replacements.sh [diretorio_das_instancias] [limite_cplex_s]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INPUT=${1:-"$ROOT/new_experiments/sopmv_feasible_replacements_20261110"}
CPLEX_LIMIT=${2:-600}
CPLEX_BIN=${CPLEX_BIN:-"$ROOT/build/bin/sopmv_cplex_branch_cut"}
ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
VNS_BIN=${VNS_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
SEEDS=(202601 202602 202603 202604 202605 202606 202607 202608 202609 202610)

[[ -f "$INPUT/manifest.csv" ]] || { echo "manifest ausente: $INPUT/manifest.csv" >&2; exit 2; }
[[ "$CPLEX_LIMIT" =~ ^[1-9][0-9]*([.][0-9]+)?$ ]] || { echo "limite CPLEX invalido" >&2; exit 2; }
[[ -x "$CPLEX_BIN" ]] || { echo "CPLEX branch-and-cut ausente: $CPLEX_BIN" >&2; exit 2; }
[[ -x "$ILS_BIN" ]] || { echo "ILS ausente: $ILS_BIN" >&2; exit 2; }
[[ -x "$VNS_BIN" ]] || { echo "VNS adaptado ausente: $VNS_BIN" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$INPUT/benchmark_${STAMP}"
mkdir -p "$OUT"/{raw_cplex,raw_ils,raw_vns,logs/cplex,logs/ils,logs/vns}
cp "$INPUT/manifest.csv" "$OUT/input_manifest.csv"
printf 'instances=22\nruns_ils_vns=10\ncplex_limit_seconds=%s\nils_vns_limit=ceil(1.5*Nsets)\n' "$CPLEX_LIMIT" > "$OUT/protocol.txt"
printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,distance,solution_valid,raw_result\n' > "$OUT/cplex_runs.csv"
printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,distance,solution_valid,raw_result\n' > "$OUT/ils_runs.csv"
printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,distance,solution_valid,validation,raw_result\n' > "$OUT/vns_runs.csv"

csv_value() { awk -F',' -v f="$2" 'NR == 2 {gsub(/"/, "", $f); print $f; exit}' "$1"; }

tail -n +2 "$INPUT/manifest.csv" | while IFS=, read -r name source ratio mandatory tmax witness attempt seed relative; do
  instance="$INPUT/${relative//\//\/}"
  [[ -f "$instance" ]] || { echo "arquivo ausente: $instance" >&2; exit 2; }
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  sets=$((total_sets - 1))
  limit=$(python3 -c "import math; print(max(1, math.ceil(1.5 * $sets)))")

  cplex_csv="$OUT/raw_cplex/${name}.csv"
  set +e
  "$CPLEX_BIN" --instance "$instance" --time-limit "$CPLEX_LIMIT" --threads 1 --mip-gap 0 --seed 20261110 --log-level 0 --csv "$cplex_csv" >"$OUT/logs/cplex/${name}.log" 2>&1
  code=$?
  set -e
  [[ "$code" == 0 || "$code" == 4 ]] || { echo "falha CPLEX: $name (codigo $code)" >&2; exit "$code"; }
  printf '%s,20261110,%s,%s,%s,%s,%s,%s,%s\n' "$name" "$sets" "$CPLEX_LIMIT" "$(csv_value "$cplex_csv" 5)" "$(csv_value "$cplex_csv" 7)" "$(csv_value "$cplex_csv" 12)" "$(csv_value "$cplex_csv" 18)" "$cplex_csv" >> "$OUT/cplex_runs.csv"

  for run_seed in "${SEEDS[@]}"; do
    run_id="${name}_seed${run_seed}"
    ils_csv="$OUT/raw_ils/${run_id}.csv"
    "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 --ils-no-improvement-limit 0 --ils-time-limit "$limit" --ils-reset-interval 40 --seed "$run_seed" --csv "$ils_csv" >"$OUT/logs/ils/${run_id}.log" 2>&1
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$name" "$run_seed" "$sets" "$limit" "$(csv_value "$ils_csv" 5)" "$(csv_value "$ils_csv" 7)" "$(csv_value "$ils_csv" 12)" "$(csv_value "$ils_csv" 18)" "$ils_csv" >> "$OUT/ils_runs.csv"

    work="$OUT/raw_vns/${run_id}"; mkdir -p "$work"
    set +e
    "$VNS_BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 --output="$work" --results=results.log --save-results=1 --save-info=0 --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 --use-rvns=0 --seed="$run_seed" --time-only-stop=1 --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 --num-iterations-unimproved=2147483647 >"$OUT/logs/vns/${run_id}.log" 2>&1
    vns_code=$?
    set -e
    result="$work/results.log"
    if [[ -s "$result" ]]; then
      validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$result" 2>&1 || true)
      record=$(tail -n 1 "$result")
      reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
      distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
      valid=$([[ "$validation" == VALIDO* ]] && echo true || echo false)
      printf '%s,%s,%s,%s,RESULT,%s,%s,%s,"%s",%s\n' "$name" "$run_seed" "$sets" "$limit" "$reward" "$distance" "$valid" "$validation" "$result" >> "$OUT/vns_runs.csv"
    else
      printf '%s,%s,%s,%s,NO_RESULT_exit_%s,,,false,"sem results.log",%s\n' "$name" "$run_seed" "$sets" "$limit" "$vns_code" "$result" >> "$OUT/vns_runs.csv"
    fi
  done
done
echo "Concluido: $OUT"
