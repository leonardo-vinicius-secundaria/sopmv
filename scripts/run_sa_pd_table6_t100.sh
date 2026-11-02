#!/usr/bin/env bash
# Reproduz o protocolo SA-SOP da Tabela 6 (omega=1 => arquivos T100).
# Uso: ./scripts/run_sa_pd_table6_t100.sh {hard|full} [repeticoes]
# hard: 28 perfis grandes (Nset >= 80); full: todos os 94 perfis da Tabela 6.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SA_BIN=${SA_BIN:-"$ROOT/build/bin/sopmv_sa"}
MODE=${1:-hard}
RUNS=${2:-10}
[[ "$MODE" =~ ^(hard|full)$ ]] || { echo "Uso: $0 {hard|full} [repeticoes]" >&2; exit 2; }
[[ "$RUNS" =~ ^[1-9][0-9]*$ ]] || { echo "Repeticoes deve ser inteiro positivo" >&2; exit 2; }
[[ -x "$SA_BIN" ]] || { echo "SA-PD nao compilado: $SA_BIN" >&2; exit 2; }

mapfile -t ALL_INSTANCES < <(
  find "$ROOT/data/intancias_grandes/sop" -maxdepth 1 -type f \
    -name '*_T100_p[12].sop' ! -name '*_RND_*' | sort
)
[[ ${#ALL_INSTANCES[@]} -eq 94 ]] || {
  echo "Esperava 94 arquivos T100 locais; encontrei ${#ALL_INSTANCES[@]}. Abortando." >&2
  exit 2
}

INSTANCES=()
for instance in "${ALL_INSTANCES[@]}"; do
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  if [[ "$MODE" == full ]] || (( total_sets - 1 >= 80 )); then
    INSTANCES+=("$instance")
  fi
done
expected=28
[[ "$MODE" == full ]] && expected=94
[[ ${#INSTANCES[@]} -eq "$expected" ]] || {
  echo "Esperava $expected arquivos no modo $MODE; encontrei ${#INSTANCES[@]}. Abortando." >&2
  exit 2
}

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/sa_pd_table6_t100_${MODE}_${STAMP}"
mkdir -p "$OUT/raw" "$OUT/logs"
printf 'instance,seed,sets_without_depot,time_limit_seconds,mode,csv_path\n' > "$OUT/manifest.csv"
printf 'article_table=6\nproblem=SOP\nomega=1.0\nfile_pattern=T100\nmode=%s\nruns=%s\nT0=16\nalpha=0.93\niterations_per_temperature=80000\ntime_multiplier=1.5\nlocal_profiles=%s\n' \
  "$MODE" "$RUNS" "${#INSTANCES[@]}" > "$OUT/protocol.txt"

for instance in "${INSTANCES[@]}"; do
  name=$(basename "$instance" .sop)
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  sets=$((total_sets - 1))
  limit=$(python3 -c "print(1.5 * $sets)")
  for ((run=1; run<=RUNS; run++)); do
    seed=$((202600 + run))
    csv="$OUT/raw/${name}_seed${seed}.csv"
    echo "table6-$MODE | $name | seed=$seed | ${limit}s"
    "$SA_BIN" --instance "$instance" --sa-temperature 16 --sa-alpha 0.93 \
      --sa-iterations 80000 --sa-time-limit "$limit" --seed "$seed" --csv "$csv" \
      >"$OUT/logs/${name}_seed${seed}.log" 2>&1
    printf '%s,%s,%s,%s,%s,%s\n' "$name" "$seed" "$sets" "$limit" \
      "table6-t100-$MODE" "$csv" >> "$OUT/manifest.csv"
  done
done

echo "Concluido: $OUT"
