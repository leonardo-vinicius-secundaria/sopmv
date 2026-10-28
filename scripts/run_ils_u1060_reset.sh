#!/usr/bin/env bash
# Bateria ILS para tres instancias representativas de data/u1060:
# N = 20, 30 e 40; 10 repeticoes por instancia e por N.
#
# Uso:
#   ./scripts/run_ils_u1060_reset.sh
#   ./scripts/run_ils_u1060_reset.sh experiments/meu_resultado
#
# Opcoes por variavel de ambiente:
#   RUNS=10 TIME_LIMIT=70 BASE_SEED=202601 ILS_ITERATIONS=1000000000 \
#     ./scripts/run_ils_u1060_reset.sh

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BINARY=${BINARY:-"$ROOT_DIR/build/bin/sopmv_ils_new_version"}
INSTANCE_DIR="$ROOT_DIR/data/u1060"
RUNS=${RUNS:-10}
TIME_LIMIT=${TIME_LIMIT:-70}
BASE_SEED=${BASE_SEED:-202601}
ILS_ITERATIONS=${ILS_ITERATIONS:-1000000000}
STAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR=${1:-"$ROOT_DIR/experiments/u1060_ils_reset_${STAMP}"}
CSV_PATH="$OUTPUT_DIR/resultados.csv"
MANIFEST_PATH="$OUTPUT_DIR/manifest.csv"
LOG_DIR="$OUTPUT_DIR/logs"
RESET_INTERVALS=(20 30 40)

if [[ ! -x "$BINARY" ]]; then
    echo "Executavel nao encontrado: $BINARY" >&2
    echo "Compile antes com: make build/bin/sopmv_ils_new_version" >&2
    exit 2
fi

if [[ ! "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
    echo "RUNS deve ser um inteiro positivo." >&2
    exit 2
fi

if [[ -e "$OUTPUT_DIR" ]]; then
    echo "Diretorio de saida ja existe: $OUTPUT_DIR" >&2
    echo "Escolha outro caminho para preservar os resultados anteriores." >&2
    exit 2
fi

INSTANCES=(
    "$INSTANCE_DIR/212u1060_T60_p1.sop"
    "$INSTANCE_DIR/212u1060_T80_p1.sop"
    "$INSTANCE_DIR/212u1060_T100_p1.sop"
)
for instance in "${INSTANCES[@]}"; do
    if [[ ! -f "$instance" ]]; then
        echo "Instancia nao encontrada: $instance" >&2
        exit 2
    fi
done

mkdir -p "$LOG_DIR"
printf 'run,seed,instance,reset_interval,time_limit_seconds\n' > "$MANIFEST_PATH"

for reset_interval in "${RESET_INTERVALS[@]}"; do
    for instance in "${INSTANCES[@]}"; do
        instance_name=$(basename "$instance" .sop)
        for ((run = 1; run <= RUNS; ++run)); do
            seed=$((BASE_SEED + run - 1))
            printf '%s,%s,%s,%s,%s\n' \
                "$run" "$seed" "$instance_name" "$reset_interval" "$TIME_LIMIT" \
                >> "$MANIFEST_PATH"

            echo "[$instance_name | N=$reset_interval | repeticao $run/$RUNS | seed=$seed]"
            "$BINARY" \
                --instance "$instance" \
                --ils-iterations "$ILS_ITERATIONS" \
                --ils-time-limit "$TIME_LIMIT" \
                --ils-reset-interval "$reset_interval" \
                --seed "$seed" \
                --csv "$CSV_PATH" \
                >"$LOG_DIR/${instance_name}_N${reset_interval}_run${run}_seed${seed}.log" 2>&1
        done
    done
done

echo "Concluido."
echo "Resultados: $CSV_PATH"
echo "Manifesto:  $MANIFEST_PATH"
echo "Logs:       $LOG_DIR"
