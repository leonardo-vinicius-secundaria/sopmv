#!/usr/bin/env bash
# Bateria SOPMV grande comparavel aos apendices do artigo de 2024.
# Uso: ./scripts/run_article_appendix_sopmv_large.sh {a1|a2|a3} [pilot|batch1..batch6|hard] [ils,sa,vns]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
APPENDIX=${1:-}
SCOPE=${2:-hard}
ALGORITHMS=${3:-ils,sa,vns}
case "$APPENDIX" in a1) T=40; OMEGA=0.4 ;; a2) T=60; OMEGA=0.6 ;; a3) T=80; OMEGA=0.8 ;;
  *) echo "Uso: $0 {a1|a2|a3} [pilot|batch1..batch6|hard] [ils,sa,vns]" >&2; exit 2 ;; esac
case "$SCOPE" in
  pilot) FAMILIES=(80rd400 217vm1084) ;;
  batch1) FAMILIES=(84fl417 201pr1002) ;;
  batch2) FAMILIES=(88pr439 212u1060) ;;
  batch3) FAMILIES=(89pcb442 157rat783) ;;
  batch4) FAMILIES=(99d493 145u724) ;;
  batch5) FAMILIES=(115rat575 132d657) ;;
  batch6) FAMILIES=(115u574 131p654) ;;
  hard) FAMILIES=() ;;
  *) echo "Escopo invalido: $SCOPE" >&2; exit 2 ;;
esac
[[ "$ALGORITHMS" =~ ^(ils|sa|vns)(,(ils|sa|vns))*$ ]] || { echo "Lista invalida: $ALGORITHMS" >&2; exit 2; }

ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
SA_BIN=${SA_BIN:-"$ROOT/build/bin/sopmv_sa"}
VNS_BIN=${VNS_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
SEEDS=(202601 202602 202603 202604 202605 202606 202607 202608 202609 202610)
has_algorithm() { [[ ",$ALGORITHMS," == *",$1,"* ]]; }
has_algorithm ils && [[ -x "$ILS_BIN" ]] || ! has_algorithm ils || { echo "ILS ausente: $ILS_BIN" >&2; exit 2; }
has_algorithm sa && [[ -x "$SA_BIN" ]] || ! has_algorithm sa || { echo "SA-PD ausente: $SA_BIN" >&2; exit 2; }
has_algorithm vns && [[ -x "$VNS_BIN" ]] || ! has_algorithm vns || { echo "VNS ausente: $VNS_BIN" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/article_${APPENDIX}_sopmv_large_${SCOPE}_${STAMP}"
mkdir -p "$OUT"/{raw_ils,raw_sa,raw_vns,logs/ils,logs/sa,logs/vns}
printf 'article_appendix=%s\nomega=%s\nfile_pattern=T%s\nproblem=SOP_and_SOPMV\nsubset=%s\nmandatory_ratios=0,10,20,30\nruns=%s\nalgorithms=%s\ntime_limit_seconds=1.5*Nsets_without_depot\n' \
  "$APPENDIX" "$OMEGA" "$T" "$SCOPE" "${#SEEDS[@]}" "$ALGORITHMS" > "$OUT/protocol.txt"
printf 'instance,instance_path,variant,mandatory_ratio,sets_without_depot,time_limit_seconds\n' > "$OUT/selection.csv"
for solver in ils sa vns; do printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,elapsed_seconds,distance,solution_valid,raw_result\n' > "$OUT/${solver}_runs.csv"; done
csv_value() { awk -F',' -v f="$2" 'NR == 2 {gsub(/"/, "", $f); print $f; exit}' "$1"; }
append_solver_row() { local solver=$1 instance=$2 seed=$3 sets=$4 limit=$5 raw=$6; printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$instance" "$seed" "$sets" "$limit" "$(csv_value "$raw" 5)" "$(csv_value "$raw" 7)" "$(csv_value "$raw" 10)" "$(csv_value "$raw" 12)" "$(csv_value "$raw" 18)" "$raw" >> "$OUT/${solver}_runs.csv"; }

INSTANCES=()
selected_family() {
  local family=$1
  [[ "$SCOPE" == hard ]] && return 0
  local candidate
  for candidate in "${FAMILIES[@]}"; do [[ "$candidate" == "$family" ]] && return 0; done
  return 1
}
for ratio in 0 10 20 30; do
  directory="$ROOT/data/intancias_grandes/sop"
  (( ratio > 0 )) && directory="$ROOT/data/intancias_grandes/sopmv${ratio}"
  while IFS= read -r instance; do INSTANCES+=("$instance"); done < <(
    find "$directory" -maxdepth 1 -type f -name "*_T${T}_p[12].sop" ! -name '*_RND_*' | sort | while IFS= read -r candidate; do
      total=$(sed -n 's/^SETS:[[:space:]]*//p' "$candidate" | head -n 1)
      family=$(basename "$candidate"); family=${family%%_T*}
      (( total - 1 >= 80 )) && selected_family "$family" && printf '%s\n' "$candidate"
    done)
done
expected=112
[[ "$SCOPE" != hard ]] && expected=16
[[ ${#INSTANCES[@]} -eq "$expected" ]] || { echo "Esperava $expected instancias no escopo $SCOPE; encontrei ${#INSTANCES[@]}" >&2; exit 2; }

for instance in "${INSTANCES[@]}"; do
  name=$(sed -n 's/^NAME:[[:space:]]*//p' "$instance" | head -n 1)
  variant=$(basename "$(dirname "$instance")")
  mandatory_ratio=0
  [[ "$variant" =~ ^sopmv([0-9]+)$ ]] && mandatory_ratio=${BASH_REMATCH[1]}
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1); sets=$((total_sets - 1))
  limit=$(python3 -c "print(1.5 * $sets)")
  printf '%s,%s,%s,%s,%s,%s\n' "$name" "$instance" "$variant" "$mandatory_ratio" "$sets" "$limit" >> "$OUT/selection.csv"
  for seed in "${SEEDS[@]}"; do
    run_id="${name}_seed${seed}"
    if has_algorithm ils; then raw="$OUT/raw_ils/${run_id}.csv"; "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 --ils-no-improvement-limit 0 --ils-time-limit "$limit" --ils-reset-interval 40 --seed "$seed" --csv "$raw" > "$OUT/logs/ils/${run_id}.log" 2>&1; append_solver_row ils "$name" "$seed" "$sets" "$limit" "$raw"; fi
    if has_algorithm sa; then raw="$OUT/raw_sa/${run_id}.csv"; "$SA_BIN" --instance "$instance" --sa-temperature 16 --sa-alpha 0.93 --sa-iterations 80000 --sa-time-limit "$limit" --seed "$seed" --csv "$raw" > "$OUT/logs/sa/${run_id}.log" 2>&1; append_solver_row sa "$name" "$seed" "$sets" "$limit" "$raw"; fi
    if has_algorithm vns; then
      work="$OUT/raw_vns/${run_id}"; mkdir -p "$work"; set +e
      "$VNS_BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 --output="$work" --results=results.log --save-results=1 --save-info=0 --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 --use-rvns=0 --seed="$seed" --time-only-stop=1 --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 --num-iterations-unimproved=2147483647 > "$OUT/logs/vns/${run_id}.log" 2>&1
      code=$?; set -e; result="$work/results.log"
      if [[ -s "$result" ]]; then validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$result" 2>&1 || true); record=$(tail -n 1 "$result"); reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record"); distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record"); valid=$([[ "$validation" == VALIDO* ]] && echo true || echo false); printf '%s,%s,%s,%s,RESULT,%s,,%s,%s,%s\n' "$name" "$seed" "$sets" "$limit" "$reward" "$distance" "$valid" "$result" >> "$OUT/vns_runs.csv"; else printf '%s,%s,%s,%s,NO_RESULT_exit_%s,,,,false,%s\n' "$name" "$seed" "$sets" "$limit" "$code" "$result" >> "$OUT/vns_runs.csv"; fi
    fi
  done
done
echo "Concluido: $OUT"
