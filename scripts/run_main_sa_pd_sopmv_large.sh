#!/usr/bin/env bash
# Executa SA-PD no mesmo corpus SOPMV grande T100 ja usado pelo ILS/VNS.
# Uso:
#   ./scripts/run_main_sa_pd_sopmv_large.sh --smoke [saida]
#   ./scripts/run_main_sa_pd_sopmv_large.sh --all [saida]
#
# O modo --smoke roda apenas a primeira instancia/semente para validar o
# ambiente. O modo --all executa os 84 perfis e 10 sementes, em serie, para
# preservar a comparabilidade do limite de tempo por relogio.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SA_BIN=${SA_BIN:-"$ROOT/build/bin/sopmv_sa"}
MODE=${1:-}
OUT=${2:-}
SEEDS=(202601 202602 202603 202604 202605 202606 202607 202608 202609 202610)
# Exclusivo para teste; a campanha final deve deixar esta variavel vazia.
SA_TIME_LIMIT_OVERRIDE=${SA_TIME_LIMIT_OVERRIDE:-}

[[ "$MODE" =~ ^(--smoke|--all)$ ]] || {
  echo "Uso: $0 {--smoke|--all} [diretorio_saida]" >&2
  exit 2
}
[[ -x "$SA_BIN" ]] || { echo "SA-PD ausente: $SA_BIN" >&2; exit 2; }

if [[ -z "$OUT" ]]; then
  stamp=$(date +%Y%m%d_%H%M%S)
  OUT="$ROOT/new_experiments/main_sa_pd_sopmv-large_${stamp}"
fi
mkdir -p "$OUT/raw_sa" "$OUT/logs/sa"

# Estas sao exatamente as sete fontes canônicas usadas na consolidação final.
SOURCES=(
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-pilot_20261102_185511"
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-batch1_20261103_101952"
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-batch2_20261104_091900"
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-batch3_20261105_080555"
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-batch4_20261105_203932"
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-batch5_20261106_090032"
  "$ROOT/new_experiments/main_ils_vns_sopmv-large-batch6_20261106_213903"
)

for source in "${SOURCES[@]}"; do
  [[ -f "$source/selection.csv" ]] || { echo "Selecao ausente: $source" >&2; exit 2; }
done

NEW_OUTPUT=0
if [[ ! -f "$OUT/protocol.txt" ]]; then
  NEW_OUTPUT=1
  {
    echo "stage=sopmv-large-T100"
    echo "algorithm=SA_PD"
    echo "counterpart=ILS_N40"
    echo "sources=$(IFS=' '; echo "${SOURCES[*]}")"
    echo "seeds=${SEEDS[*]}"
    echo "time_budget=exactly_the_ILS_selection_time_limit_seconds"
    echo "T0=16"
    echo "alpha=0.93"
    echo "iterations_per_temperature=80000"
    echo "execution_mode=${MODE#--}"
    echo "time_limit_override=${SA_TIME_LIMIT_OVERRIDE:-none}"
  } > "$OUT/protocol.txt"
  printf 'instance,instance_path,variant,sets_without_depot,time_limit_seconds,source_campaign\n' > "$OUT/selection.csv"
  printf 'instance,seed,sets_without_depot,time_limit_seconds,status,objective,elapsed_seconds,distance,solution_valid,validation_message,raw_csv\n' > "$OUT/sa_runs.csv"
fi

declare -A seen
entries=()
for source in "${SOURCES[@]}"; do
  while IFS=, read -r instance instance_path variant sets limit; do
    [[ "$instance" == "instance" ]] && continue
    [[ -n "$instance" && -n "$instance_path" && -n "$limit" ]] || {
      echo "Linha de selecao invalida em $source" >&2; exit 2; }
    [[ -z ${seen[$instance]+x} ]] || { echo "Instancia duplicada: $instance" >&2; exit 2; }
    seen[$instance]=1
    entries+=("$instance|$instance_path|$variant|$sets|$limit|$source")
    if [[ "$NEW_OUTPUT" -eq 1 ]]; then
      printf '%s,%s,%s,%s,%s,%s\n' "$instance" "$instance_path" "$variant" "$sets" "$limit" "$source" >> "$OUT/selection.csv"
    fi
  done < "$source/selection.csv"
done
[[ ${#entries[@]} -eq 84 ]] || { echo "Esperava 84 perfis; encontrei ${#entries[@]}" >&2; exit 2; }

run_one() {
  local instance=$1 path=$2 sets=$3 limit=$4 seed=$5
  local raw="$OUT/raw_sa/${instance}_seed${seed}.csv"
  local log="$OUT/logs/sa/${instance}_seed${seed}.log"
  local effective_limit=${SA_TIME_LIMIT_OVERRIDE:-$limit}
  if [[ -s "$raw" ]] && [[ $(wc -l < "$raw") -ge 2 ]]; then
    return
  fi
  echo "SA-PD | $instance | seed=$seed | ${effective_limit}s"
  "$SA_BIN" --instance "$path" --sa-temperature 16 --sa-alpha 0.93 \
    --sa-iterations 80000 --sa-time-limit "$effective_limit" --seed "$seed" --csv "$raw" >"$log" 2>&1
  awk -F',' -v raw="$raw" 'NR == 2 {
    gsub(/"/, "", $5); gsub(/"/, "", $7); gsub(/"/, "", $10); gsub(/"/, "", $12);
    gsub(/"/, "", $18); gsub(/"/, "", $19);
    print $1 "," seed "," sets "," limit "," $5 "," $7 "," $10 "," $12 "," $18 ",\"" $19 "\"," raw;
    exit
  }' seed="$seed" sets="$sets" limit="$effective_limit" "$raw" >> "$OUT/sa_runs.csv"
}

if [[ "$MODE" == "--smoke" ]]; then
  IFS='|' read -r instance path variant sets limit source <<< "${entries[0]}"
  run_one "$instance" "$path" "$sets" "$limit" "${SEEDS[0]}"
else
  for entry in "${entries[@]}"; do
    IFS='|' read -r instance path variant sets limit source <<< "$entry"
    for seed in "${SEEDS[@]}"; do run_one "$instance" "$path" "$sets" "$limit" "$seed"; done
  done
fi

echo "Concluido: $OUT"
