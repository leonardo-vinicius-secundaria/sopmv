#!/usr/bin/env bash
# Continua uma bateria SA-PD large-hard interrompida sem repetir CSVs validos.
# Uso: ./scripts/continue_sa_pd_large_hard.sh
# Considera automaticamente a execucao original e todas as continuacoes anteriores.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SA_BIN=${SA_BIN:-"$ROOT/build/bin/sopmv_sa"}
[[ -x "$SA_BIN" ]] || { echo "SA-PD nao compilado: $SA_BIN" >&2; exit 2; }

SOURCES=("$ROOT/new_experiments/sa_pd_reproduction_large-hard_20261031_000511")
while IFS= read -r directory; do SOURCES+=("$directory"); done < <(
  find "$ROOT/new_experiments" -maxdepth 1 -type d \
    -name 'sa_pd_reproduction_large-hard_continuation_*' | sort
)
for source in "${SOURCES[@]}"; do
  [[ -d "$source/raw" ]] || { echo "Diretorio de resultados ausente: $source/raw" >&2; exit 2; }
done

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/sa_pd_reproduction_large-hard_continuation_${STAMP}"
mkdir -p "$OUT/raw" "$OUT/logs"
printf 'instance,seed,sets_without_depot,time_limit_seconds,mode,csv_path\n' > "$OUT/manifest.csv"
printf 'mode=large-hard-continuation\nruns=10\nT0=16\nalpha=0.93\niterations_per_temperature=80000\ntime_multiplier=1.5\n' \
  > "$OUT/protocol.txt"
printf 'source_experiment=%s\n' "${SOURCES[@]}" >> "$OUT/protocol.txt"

mapfile -t INSTANCES < <(
  for instance in "$ROOT"/data/intancias_grandes/sop/*_T80_p[12].sop; do
    [[ "$(basename "$instance")" == *_RND_* ]] && continue
    total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
    (( total_sets - 1 >= 80 )) && printf '%s\n' "$instance"
  done | sort
)

(( ${#INSTANCES[@]} == 28 )) || {
  echo "Esperava 28 instancias large-hard; encontrei ${#INSTANCES[@]}. Abortando." >&2
  exit 2
}

# Um CSV ja concluido tem cabecalho e ao menos uma linha de resultado valida.
declare -A DONE
for source in "${SOURCES[@]}"; do
  for csv in "$source"/raw/*_seed*.csv; do
    [[ -f "$csv" && $(wc -l < "$csv") -ge 2 ]] || continue
    base=$(basename "$csv" .csv)
    DONE["$base"]=1
  done
done

pending=0
for instance in "${INSTANCES[@]}"; do
  name=$(basename "$instance" .sop)
  for seed in {202601..202610}; do
    [[ -n ${DONE["${name}_seed${seed}"]+x} ]] || pending=$((pending + 1))
  done
done
(( pending > 0 )) || { echo "Nenhuma execucao pendente."; exit 0; }

echo "Executando $pending combinacoes pendentes; resultados em: $OUT"
for instance in "${INSTANCES[@]}"; do
  name=$(basename "$instance" .sop)
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  sets=$((total_sets - 1))
  limit=$(python3 -c "print(1.5 * $sets)")
  for seed in {202601..202610}; do
    key="${name}_seed${seed}"
    [[ -n ${DONE["$key"]+x} ]] && continue
    csv="$OUT/raw/${key}.csv"
    echo "large-hard | $name | seed=$seed | ${limit}s"
    "$SA_BIN" --instance "$instance" --sa-temperature 16 --sa-alpha 0.93 \
      --sa-iterations 80000 --sa-time-limit "$limit" --seed "$seed" --csv "$csv" \
      >"$OUT/logs/${key}.log" 2>&1
    printf '%s,%s,%s,%s,%s,%s\n' "$name" "$seed" "$sets" "$limit" \
      'large-hard-continuation' "$csv" >> "$OUT/manifest.csv"
  done
done

echo "Concluido: $OUT"
