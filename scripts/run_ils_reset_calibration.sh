#!/usr/bin/env bash
# Calibracao de um fator do ILS: intervalo N de retorno ao melhor incumbente.
# Quatro niveis, quatro instancias representativas e cinco sementes: 80 execucoes.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
[[ -x "$ILS_BIN" ]] || { echo "ILS nao compilado: $ILS_BIN" >&2; exit 2; }

INTERVALS="10 20 30 40"
SEEDS="202601 202602 202603 202604 202605"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/ils_reset_calibration_${STAMP}"
mkdir -p "$OUT/raw" "$OUT/logs"
printf 'reset_interval,instance,seed,sets,time_limit_seconds,csv_path\n' > "$OUT/manifest.csv"
printf '%s\n' \
  'Calibracao unifatorial do ILS.' \
  'Fator: reset_interval N = 10, 20, 30, 40.' \
  'Sementes: 202601--202605.' \
  'Orcamento por execucao: ceil(1.5 * Nsets) segundos.' \
  'Selecao: menor RPD medio por instancia-semente; desempate por mediana, vitorias e distancia.' \
  > "$OUT/protocol.txt"

INSTANCES=(
  "$ROOT/data/intancias_grandes/sop/40d198_T80_p1.sop"
  "$ROOT/data/intancias_grandes/sop/60pr299_T80_p2.sop"
  "$ROOT/data/intancias_grandes/sop/80rd400_T80_p1.sop"
  "$ROOT/data/intancias_grandes/sop/145u724_T80_p2.sop"
)

for instance in "${INSTANCES[@]}"; do
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
done

for interval in $INTERVALS; do
  for instance in "${INSTANCES[@]}"; do
    name=$(basename "$instance" .sop)
    sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
    limit=$(( (3 * sets + 1) / 2 ))
    for seed in $SEEDS; do
      csv="$OUT/raw/N${interval}/${name}_seed${seed}.csv"
      mkdir -p "$(dirname "$csv")"
      echo "N=$interval | $name | seed=$seed | ${limit}s"
      "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 \
        --ils-time-limit "$limit" --ils-reset-interval "$interval" \
        --seed "$seed" --csv "$csv" \
        >"$OUT/logs/N${interval}_${name}_seed${seed}.log" 2>&1
      printf '%s,%s,%s,%s,%s,%s\n' "$interval" "$name" "$seed" "$sets" "$limit" "$csv" >> "$OUT/manifest.csv"
    done
  done
done

python3 "$ROOT/scripts/analyze_ils_reset_calibration.py" "$OUT"
echo "Concluido: $OUT"
