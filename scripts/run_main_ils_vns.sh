#!/usr/bin/env bash
# Benchmark principal ILS (N=40) x VNS adaptado, com orcamento igual por relogio.
# Uso: ./scripts/run_main_ils_vns.sh {sop-small|sop-large-pilot|sop-large-batch2|sop-large-remaining|sop-large-hard|sopmv-small|sopmv-large-pilot|sopmv-large-batch1..6}
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
VNS_BIN=${VNS_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
STAGE=${1:-}
SEEDS=(202601 202602 202603 202604 202605 202606 202607 202608 202609 202610)

[[ "$STAGE" =~ ^(sop-small|sop-large-pilot|sop-large-batch2|sop-large-remaining|sop-large-hard|sopmv-small|sopmv-large-pilot|sopmv-large-batch[1-6])$ ]] || {
  echo "Uso: $0 {sop-small|sop-large-pilot|sop-large-batch2|sop-large-remaining|sop-large-hard|sopmv-small|sopmv-large-pilot|sopmv-large-batch1..6}" >&2; exit 2; }
[[ -x "$ILS_BIN" && -x "$VNS_BIN" ]] || { echo "ILS ou VNS adaptado nao compilado" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/main_ils_vns_${STAGE}_${STAMP}"
mkdir -p "$OUT/raw_ils" "$OUT/raw_vns" "$OUT/logs/ils" "$OUT/logs/vns"
printf 'stage=%s\nalgorithms=ILS_N40,VNS_adapted\nseeds=%s\ntime_budget=ceil(1.5*Nset_without_depot)\nils_reset_interval=40\nils_no_improvement_limit=0\nvns_time_only_stop=1\n' \
  "$STAGE" "${SEEDS[*]}" > "$OUT/protocol.txt"
printf 'instance,instance_path,variant,sets_without_depot,time_limit_seconds\n' > "$OUT/selection.csv"
printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,elapsed_seconds,distance,solution_valid,raw_csv\n' > "$OUT/ils_runs.csv"
printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,distance,iterations,validation,raw_results_log\n' > "$OUT/vns_runs.csv"

INSTANCES=()
case "$STAGE" in
  sop-small)
    mapfile -t INSTANCES < <(find "$ROOT/data/instancias_pequenas/sop" -maxdepth 1 -type f -name '*.sop' | sort)
    [[ ${#INSTANCES[@]} -eq 20 ]] || { echo "Esperava 20 SOP pequenas; encontrei ${#INSTANCES[@]}" >&2; exit 2; }
    ;;
  sop-large-pilot)
    # Quatro familias de tamanhos crescentes para decidir se vale escalar ao bloco hard.
    for family in 80rd400 115u574 145u724 217vm1084; do
      INSTANCES+=(
        "$ROOT/data/intancias_grandes/sop/${family}_T100_p1.sop"
        "$ROOT/data/intancias_grandes/sop/${family}_T100_p2.sop"
      )
    done
    [[ ${#INSTANCES[@]} -eq 8 ]] || { echo "Esperava 8 perfis SOP do piloto" >&2; exit 2; }
    for instance in "${INSTANCES[@]}"; do
      [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
    done
    ;;
  sop-large-batch2)
    # Segundo lote, disjunto do piloto: quatro familias adicionais e tamanhos variados.
    for family in 88pr439 115rat575 157rat783 212u1060; do
      INSTANCES+=(
        "$ROOT/data/intancias_grandes/sop/${family}_T100_p1.sop"
        "$ROOT/data/intancias_grandes/sop/${family}_T100_p2.sop"
      )
    done
    [[ ${#INSTANCES[@]} -eq 8 ]] || { echo "Esperava 8 perfis SOP do segundo lote" >&2; exit 2; }
    for instance in "${INSTANCES[@]}"; do
      [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
    done
    ;;
  sop-large-remaining)
    # Perfis T100 ainda nao executados entre as 14 familias grandes hard.
    # E disjunto de sop-large-pilot e sop-large-batch2.
    for family in 84fl417 89pcb442 99d493 131p654 132d657 201pr1002; do
      INSTANCES+=(
        "$ROOT/data/intancias_grandes/sop/${family}_T100_p1.sop"
        "$ROOT/data/intancias_grandes/sop/${family}_T100_p2.sop"
      )
    done
    [[ ${#INSTANCES[@]} -eq 12 ]] || { echo "Esperava 12 perfis SOP restantes" >&2; exit 2; }
    for instance in "${INSTANCES[@]}"; do
      [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
    done
    ;;
  sop-large-hard)
    mapfile -t INSTANCES < <(
      for instance in "$ROOT"/data/intancias_grandes/sop/*_T100_p[12].sop; do
        [[ "$(basename "$instance")" == *_RND_* ]] && continue
        total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
        (( total_sets - 1 >= 80 )) && printf '%s\n' "$instance"
      done | sort
    )
    [[ ${#INSTANCES[@]} -eq 28 ]] || { echo "Esperava 28 SOP grandes T100; encontrei ${#INSTANCES[@]}" >&2; exit 2; }
    ;;
  sopmv-small)
    # Seleciona apenas as 38 SOPMV pequenas que o CPLEX ja certificou com rota viavel.
    CPLEX_A="$ROOT/new_experiments/cplex_small_validation_20261030_081715/cplex_results.csv"
    CPLEX_B="$ROOT/new_experiments/cplex_small_validation_continuation_20261030_142058/cplex_results.csv"
    [[ -f "$CPLEX_A" && -f "$CPLEX_B" ]] || { echo "CSVs CPLEX de referencia ausentes" >&2; exit 2; }
    declare -A CPLEX_FEASIBLE
    while IFS= read -r name; do CPLEX_FEASIBLE["$name"]=1; done < <(
      awk -F',' 'NR > 1 && $2 == "SOPMV" && ($5 == "Optimal" || $5 == "FeasibleTimeLimit") && $18 == "true" {gsub(/"/, "", $1); print $1}' "$CPLEX_A" "$CPLEX_B" | sort -u
    )
    while IFS= read -r instance; do
      name=$(sed -n 's/^NAME:[[:space:]]*//p' "$instance" | head -n 1)
      [[ -n ${CPLEX_FEASIBLE["$name"]+x} ]] && INSTANCES+=("$instance")
    done < <(find "$ROOT/data/instancias_pequenas" -mindepth 2 -maxdepth 2 -type f -path '*/sopmv_*/*.sop' | sort)
    [[ ${#INSTANCES[@]} -eq 38 ]] || { echo "Esperava 38 SOPMV pequenas viaveis; encontrei ${#INSTANCES[@]}" >&2; exit 2; }
    ;;
  sopmv-large-pilot)
    # Duas familias de extremos de porte, p1/p2 e tres percentuais obrigatorios.
    # As mesmas familias ja apareceram no piloto SOP, permitindo leitura direta
    # do impacto dos conjuntos obrigatorios. Resultados sem rota sao registrados.
    for mandatory_ratio in 10 20 30; do
      for family in 80rd400 217vm1084; do
        INSTANCES+=(
          "$ROOT/data/intancias_grandes/sopmv${mandatory_ratio}/${family}_T100_p1.sop"
          "$ROOT/data/intancias_grandes/sopmv${mandatory_ratio}/${family}_T100_p2.sop"
        )
      done
    done
    [[ ${#INSTANCES[@]} -eq 12 ]] || { echo "Esperava 12 perfis SOPMV grandes do piloto" >&2; exit 2; }
    for instance in "${INSTANCES[@]}"; do
      [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
    done
    ;;
  sopmv-large-batch1|sopmv-large-batch2|sopmv-large-batch3|sopmv-large-batch4|sopmv-large-batch5|sopmv-large-batch6)
    # Blocos disjuntos de duas familias. Juntos, com o piloto, cobrem as
    # 14 familias grandes hard em p1/p2 e SOPMV10/20/30.
    case "$STAGE" in
      sopmv-large-batch1) FAMILIES=(84fl417 201pr1002) ;;
      sopmv-large-batch2) FAMILIES=(88pr439 212u1060) ;;
      sopmv-large-batch3) FAMILIES=(89pcb442 157rat783) ;;
      sopmv-large-batch4) FAMILIES=(99d493 145u724) ;;
      sopmv-large-batch5) FAMILIES=(115rat575 132d657) ;;
      sopmv-large-batch6) FAMILIES=(115u574 131p654) ;;
    esac
    for mandatory_ratio in 10 20 30; do
      for family in "${FAMILIES[@]}"; do
        INSTANCES+=(
          "$ROOT/data/intancias_grandes/sopmv${mandatory_ratio}/${family}_T100_p1.sop"
          "$ROOT/data/intancias_grandes/sopmv${mandatory_ratio}/${family}_T100_p2.sop"
        )
      done
    done
    [[ ${#INSTANCES[@]} -eq 12 ]] || { echo "Esperava 12 perfis SOPMV no lote" >&2; exit 2; }
    for instance in "${INSTANCES[@]}"; do
      [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
    done
    ;;
esac

csv_value() {
  local csv=$1 field=$2
  awk -F',' -v f="$field" 'NR == 2 {gsub(/"/, "", $f); print $f; exit}' "$csv"
}

for instance in "${INSTANCES[@]}"; do
  display_name=$(sed -n 's/^NAME:[[:space:]]*//p' "$instance" | head -n 1)
  variant=$(basename "$(dirname "$instance")")
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  sets=$((total_sets - 1))
  limit=$(python3 -c "import math; print(max(1, math.ceil(1.5 * $sets)))")
  printf '%s,%s,%s,%s,%s\n' "$display_name" "$instance" "$variant" "$sets" "$limit" >> "$OUT/selection.csv"

  for seed in "${SEEDS[@]}"; do
    run_id="${display_name}_seed${seed}"
    ils_csv="$OUT/raw_ils/${run_id}.csv"
    echo "ILS | $display_name | seed=$seed | ${limit}s"
    "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 \
      --ils-no-improvement-limit 0 --ils-time-limit "$limit" --ils-reset-interval 40 \
      --seed "$seed" --csv "$ils_csv" >"$OUT/logs/ils/${run_id}.log" 2>&1
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$display_name" "$seed" "$sets" "$limit" \
      "$(csv_value "$ils_csv" 5)" "$(csv_value "$ils_csv" 7)" "$(csv_value "$ils_csv" 10)" \
      "$(csv_value "$ils_csv" 12)" "$(csv_value "$ils_csv" 18)" "$ils_csv" >> "$OUT/ils_runs.csv"

    work="$OUT/raw_vns/${run_id}"
    mkdir -p "$work"
    echo "VNS | $display_name | seed=$seed | ${limit}s"
    set +e
    "$VNS_BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 \
      --output="$work" --results=results.log --save-results=1 --save-info=0 --save-settings=0 \
      --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 \
      --use-rvns=0 --seed="$seed" --time-only-stop=1 --maximal-calculation-time-sec="$limit" \
      --num-iterations=2147483647 --num-iterations-unimproved=2147483647 \
      >"$OUT/logs/vns/${run_id}.log" 2>&1
    vns_code=$?
    set -e
    results_log="$work/results.log"
    if [[ -s "$results_log" ]]; then
      validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$results_log" 2>&1 || true)
      record=$(tail -n 1 "$results_log")
      reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
      distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
      iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
      status="RESULT"
    else
      reward=""; distance=""; iterations=""
      status="NO_RESULT_exit_${vns_code}"
      validation="sem results.log"
    fi
    validation=${validation//$'\n'/ }
    printf '%s,%s,%s,%s,%s,%s,%s,%s,"%s",%s\n' \
      "$display_name" "$seed" "$sets" "$limit" "$status" "$reward" "$distance" "$iterations" \
      "$validation" "$results_log" >> "$OUT/vns_runs.csv"
  done
done

echo "Concluido: $OUT"
