#!/usr/bin/env bash
# Compila e compara CPLEX, guloso e SA-PD em SOP e SOPMV.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTANCE="data/berlin52/sop/11berlin52_T40_p1.sop"
OUTPUT_DIR="experiments/smoke_tests"
CPLEX_ROOT_DIR="${CPLEX_ROOT_DIR:-}"
RATIO="0.20"
SEED="202601"
TIME_LIMIT="600"
THREADS="1"
MIP_GAP="0"
LOG_LEVEL="0"
SA_TIME_LIMIT=""
MANUAL_SETS=""
SKIP_SOP=0

usage() {
    cat <<'EOF'
Uso:
  ./scripts/run_comparison.sh --cplex-root /caminho/CPLEX_Studio129 [opcoes]

Opcoes:
  --instance ARQUIVO          Instancia SOP (padrao: data/berlin52/sop/11berlin52_T40_p1.sop)
  --ratio R                   Proporcao para o gerador (padrao: 0.20)
  --seed S                    Semente do gerador e CPLEX (padrao: 202601)
  --mandatory-sets "3 8"      Usa exatamente estes conjuntos, em vez do gerador
  --time-limit SEGUNDOS       Limite por resolucao (padrao: 600)
  --threads N                 Threads do CPLEX (padrao: 1)
  --mip-gap G                 Gap MIP (padrao: 0)
  --log-level N               Log CPLEX, de 0 a 5 (padrao: 0)
  --sa-time-limit SEGUNDOS    Limite do SA-PD (padrao: 1.5 * conjuntos)
  --output-dir DIRETORIO      Arquivos .mv e CSV (padrao: experiments/smoke_tests)
  --skip-sop                  Executa somente SOPMV
  --help

Exemplos:
  ./scripts/run_comparison.sh --cplex-root /opt/ibm/ILOG/CPLEX_Studio129
  ./scripts/run_comparison.sh --cplex-root /opt/ibm/ILOG/CPLEX_Studio129 --seed 202602
  ./scripts/run_comparison.sh --cplex-root /opt/ibm/ILOG/CPLEX_Studio129 --mandatory-sets "4 7"
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cplex-root) CPLEX_ROOT_DIR="$2"; shift 2 ;;
        --instance) INSTANCE="$2"; shift 2 ;;
        --ratio) RATIO="$2"; shift 2 ;;
        --seed) SEED="$2"; shift 2 ;;
        --mandatory-sets) MANUAL_SETS="$2"; shift 2 ;;
        --time-limit) TIME_LIMIT="$2"; shift 2 ;;
        --threads) THREADS="$2"; shift 2 ;;
        --mip-gap) MIP_GAP="$2"; shift 2 ;;
        --log-level) LOG_LEVEL="$2"; shift 2 ;;
        --sa-time-limit) SA_TIME_LIMIT="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --skip-sop) SKIP_SOP=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Opcao desconhecida: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$CPLEX_ROOT_DIR" ]]; then
    echo "Erro: informe --cplex-root ou defina CPLEX_ROOT_DIR." >&2
    exit 2
fi

cd "$ROOT_DIR"
if [[ ! -f "$INSTANCE" ]]; then
    echo "Erro: instancia nao encontrada: $INSTANCE" >&2
    exit 2
fi
mkdir -p "$OUTPUT_DIR"

make CPLEX_ROOT_DIR="$CPLEX_ROOT_DIR"

CSV_PATH="$OUTPUT_DIR/comparacao.csv"
run_cplex() {
    local label="$1"
    shift
    echo
    echo "===== $label ====="
    set +e
    build/bin/sopmv_cplex \
        --instance "$INSTANCE" \
        --time-limit "$TIME_LIMIT" \
        --threads "$THREADS" \
        --mip-gap "$MIP_GAP" \
        --seed "$SEED" \
        --log-level "$LOG_LEVEL" \
        --csv "$CSV_PATH" \
        "$@"
    local status=$?
    set -e
    # 4 e o codigo normal para uma instancia comprovadamente inviavel.
    if [[ $status -ne 0 && $status -ne 4 ]]; then
        echo "Erro: execucao '$label' terminou com codigo $status." >&2
        exit "$status"
    fi
}

run_greedy() {
    local label="$1"
    shift
    echo
    echo "===== $label ====="
    build/bin/sopmv_greedy \
        --instance "$INSTANCE" \
        --csv "$CSV_PATH" \
        "$@"
}

run_sa() {
    local label="$1"
    shift
    local sa_time_args=()
    if [[ -n "$SA_TIME_LIMIT" ]]; then
        sa_time_args=(--sa-time-limit "$SA_TIME_LIMIT")
    fi
    echo
    echo "===== $label ====="
    build/bin/sopmv_sa \
        --instance "$INSTANCE" \
        --seed "$SEED" \
        --csv "$CSV_PATH" \
        "${sa_time_args[@]}" \
        "$@"
}

if [[ $SKIP_SOP -eq 0 ]]; then
    run_cplex "CPLEX - SOP (sem obrigatorios)"
    run_greedy "Guloso - SOP (sem obrigatorios)"
    run_sa "SA-PD - SOP (sem obrigatorios)"
fi

if [[ -n "$MANUAL_SETS" ]]; then
    read -r -a set_array <<< "$MANUAL_SETS"
    if [[ ${#set_array[@]} -eq 0 ]]; then
        echo "Erro: --mandatory-sets nao pode ser vazio." >&2
        exit 2
    fi
    set_label="$(IFS=_; echo "${set_array[*]}")"
    MANDATORY_FILE="$OUTPUT_DIR/manual_M_${set_label}.mv"
    if [[ ! -e "$MANDATORY_FILE" ]]; then
        {
            printf 'NAME: manual_M_%s\n' "$set_label"
            printf 'MANDATORY_SETS:'
            for set_id in "${set_array[@]}"; do printf ' %s' "$set_id"; done
            printf '\n'
        } > "$MANDATORY_FILE"
        echo "Arquivo manual criado: $MANDATORY_FILE"
    else
        echo "Arquivo manual reutilizado: $MANDATORY_FILE"
    fi
else
    instance_stem="$(basename "$INSTANCE" .sop)"
    MANDATORY_FILE="$OUTPUT_DIR/${instance_stem}_ratio${RATIO}_seed${SEED}.mv"
    if [[ ! -e "$MANDATORY_FILE" ]]; then
        build/bin/generate_sopmv \
            --instance "$INSTANCE" \
            --ratio "$RATIO" \
            --seed "$SEED" \
            --output "$MANDATORY_FILE"
    else
        echo "Arquivo gerado reutilizado: $MANDATORY_FILE"
    fi
fi

run_cplex "CPLEX - SOPMV (obrigatorios em $MANDATORY_FILE)" --mandatory-file "$MANDATORY_FILE"
run_greedy "Guloso - SOPMV (obrigatorios em $MANDATORY_FILE)" --mandatory-file "$MANDATORY_FILE"
run_sa "SA-PD - SOPMV (obrigatorios em $MANDATORY_FILE)" --mandatory-file "$MANDATORY_FILE"
echo
echo "Comparacao salva em: $CSV_PATH"
