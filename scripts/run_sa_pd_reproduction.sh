#!/usr/bin/env bash
# Reproducao do protocolo SA-PD do artigo de 2024 em SOP (sem obrigatorios).
# Uso: ./scripts/run_sa_pd_reproduction.sh {small|large-hard|large-full} [repeticoes]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SA_BIN=${SA_BIN:-"$ROOT/build/bin/sopmv_sa"}
MODE=${1:-}
RUNS=${2:-10}
[[ "$MODE" =~ ^(small|large-hard|large-full)$ ]] || {
  echo "Uso: $0 {small|large-hard|large-full} [repeticoes]" >&2; exit 2; }
[[ "$RUNS" =~ ^[1-9][0-9]*$ ]] || { echo "Repeticoes deve ser inteiro positivo" >&2; exit 2; }
[[ -x "$SA_BIN" ]] || { echo "SA-PD nao compilado: $SA_BIN" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/sa_pd_reproduction_${MODE}_${STAMP}"
mkdir -p "$OUT/raw" "$OUT/logs"
printf 'instance,seed,sets_without_depot,time_limit_seconds,mode,csv_path\n' > "$OUT/manifest.csv"

case "$MODE" in
  small)
    # Tabela 5: tempos observados de 0,2 x Nset (sem o conjunto deposito).
    mapfile -t INSTANCES < <(find "$ROOT/data/instancias_pequenas/sop" -maxdepth 1 -type f -name '*.sop' | sort)
    MULTIPLIER=0.2
    ;;
  large-hard)
    # Subconjunto discriminativo da Tabela 6: 80rd400 ate 217vm1084, g1 e g2.
    mapfile -t INSTANCES < <(
      for instance in "$ROOT"/data/intancias_grandes/sop/*_T80_p[12].sop; do
        [[ "$(basename "$instance")" == *_RND_* ]] && continue
        sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
        (( sets - 1 >= 80 )) && printf '%s\n' "$instance"
      done | sort
    )
    MULTIPLIER=1.5
    ;;
  large-full)
    # Segundo conjunto completo do artigo: perfis g1/g2, sem variantes RND.
    mapfile -t INSTANCES < <(
      find "$ROOT/data/intancias_grandes/sop" -maxdepth 1 -type f -name '*_T80_p[12].sop' ! -name '*_RND_*' | sort
    )
    MULTIPLIER=1.5
    ;;
esac

(( ${#INSTANCES[@]} > 0 )) || { echo "Nenhuma instancia encontrada" >&2; exit 2; }
printf 'mode=%s\nruns=%s\nT0=16\nalpha=0.93\niterations_per_temperature=80000\ntime_multiplier=%s\n' \
  "$MODE" "$RUNS" "$MULTIPLIER" > "$OUT/protocol.txt"

for instance in "${INSTANCES[@]}"; do
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
  name=$(basename "$instance" .sop)
  total_sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  sets=$((total_sets - 1))
  limit=$(python3 -c "print($MULTIPLIER * $sets)")
  for ((run=1; run<=RUNS; run++)); do
    seed=$((202600 + run))
    csv="$OUT/raw/${name}_seed${seed}.csv"
    echo "$MODE | $name | seed=$seed | ${limit}s"
    "$SA_BIN" --instance "$instance" --sa-temperature 16 --sa-alpha 0.93 \
      --sa-iterations 80000 --sa-time-limit "$limit" --seed "$seed" --csv "$csv" \
      >"$OUT/logs/${name}_seed${seed}.log" 2>&1
    printf '%s,%s,%s,%s,%s,%s\n' "$name" "$seed" "$sets" "$limit" "$MODE" "$csv" >> "$OUT/manifest.csv"
  done
done

echo "Concluido: $OUT"
