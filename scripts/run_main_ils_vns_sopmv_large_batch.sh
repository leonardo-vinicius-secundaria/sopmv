#!/usr/bin/env bash
# Executa um dos seis lotes independentes restantes do SOPMV grande.
# Uso: ./scripts/run_main_ils_vns_sopmv_large_batch.sh {1|2|3|4|5|6}
set -euo pipefail

BATCH=${1:-}
[[ "$BATCH" =~ ^[1-6]$ ]] || {
  echo "Uso: $0 {1|2|3|4|5|6}" >&2
  exit 2
}

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec "$ROOT/scripts/run_main_ils_vns.sh" "sopmv-large-batch${BATCH}"
