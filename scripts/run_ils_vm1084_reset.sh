#!/usr/bin/env bash
# Executa o piloto de reinicio periodico do ILS em duas instancias vm1084.
#
# Uso:
#   ./scripts/run_ils_vm1084_reset.sh [diretorio_de_saida]
#
# Variaveis opcionais:
#   RUNS=10 TIME_LIMIT=70 BASE_SEED=202601 ILS_ITERATIONS=1000000000 \
#     ./scripts/run_ils_vm1084_reset.sh

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BINARY=${BINARY:-"$ROOT_DIR/build/bin/sopmv_ils_new_version"}
RUNS=${RUNS:-10}
TIME_LIMIT=${TIME_LIMIT:-70}
BASE_SEED=${BASE_SEED:-202601}
# Valor alto para que a parada seja efetivamente dada pelo limite de tempo.
ILS_ITERATIONS=${ILS_ITERATIONS:-1000000000}
STAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR=${1:-"$ROOT_DIR/experiments/vm1084_ils_reset_${STAMP}"}
CSV_PATH="$OUTPUT_DIR/resultados.csv"
MANIFEST_PATH="$OUTPUT_DIR/manifest.csv"
LOG_DIR="$OUTPUT_DIR/logs"

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

mkdir -p "$LOG_DIR"
printf 'run,seed,instance,reset_interval,time_limit_seconds\n' > "$MANIFEST_PATH"

instances=(
    "data/vm1084/sop/217vm1084_T40_p2.sop"
    "data/vm1084/sop/217vm1084_T80_p1.sop"
)
reset_intervals=(10 20 30)

for reset_interval in "${reset_intervals[@]}"; do
    for instance_rel in "${instances[@]}"; do
        instance="$ROOT_DIR/$instance_rel"
        if [[ ! -f "$instance" ]]; then
            echo "Instancia nao encontrada: $instance" >&2
            exit 2
        fi

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
