#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BINARY=${BINARY:-"$ROOT_DIR/build/bin/sopmv_ils_new_version"}
INSTANCE_DIR=${INSTANCE_DIR:-"/home/leo/vns-sop/datasets/sop"}
OUTPUT_DIR=${1:-"$ROOT_DIR/experiments/berlin52_ils_acceptance_2000"}
CSV_PATH="$OUTPUT_DIR/11berlin52_ils_results.csv"
LOG_DIR="$OUTPUT_DIR/logs"

if [[ ! -x "$BINARY" ]]; then
    echo "Executavel nao encontrado: $BINARY" >&2
    echo "Compile com: make build/bin/sopmv_ils_new_version" >&2
    exit 2
fi

if [[ ! -d "$INSTANCE_DIR" ]]; then
    echo "Diretorio de instancias nao encontrado: $INSTANCE_DIR" >&2
    exit 2
fi

if [[ -e "$OUTPUT_DIR" ]]; then
    echo "Diretorio de saida ja existe: $OUTPUT_DIR" >&2
    echo "Escolha outro caminho para nao sobrescrever resultados." >&2
    exit 2
fi

mkdir -p "$LOG_DIR"

shopt -s nullglob
instances=("$INSTANCE_DIR"/11berlin52_*.sop)
if [[ ${#instances[@]} -ne 18 ]]; then
    echo "Esperadas 18 instancias 11berlin52_*.sop; encontradas ${#instances[@]} em $INSTANCE_DIR" >&2
    exit 2
fi

for policy in better random-walk metropolis; do
    for instance in "${instances[@]}"; do
        instance_name=$(basename "$instance" .sop)
        "$BINARY" \
            --instance "$instance" \
            --ils-iterations 2000 \
            --ils-no-improvement-limit 1000 \
            --ils-time-limit 0 \
            --ils-perturbation 2 \
            --ils-acceptance "$policy" \
            --seed 202601 \
            --csv "$CSV_PATH" \
            >"$LOG_DIR/${instance_name}_${policy}.log" 2>&1
    done
done

echo "CSV gerado em: $CSV_PATH"
echo "Logs gerados em: $LOG_DIR"
