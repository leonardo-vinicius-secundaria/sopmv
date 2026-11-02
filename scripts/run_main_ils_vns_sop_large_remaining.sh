#!/usr/bin/env bash
# Conclui os 12 perfis SOP grandes T100 ainda pendentes (10 sementes por algoritmo).
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec "$ROOT/scripts/run_main_ils_vns.sh" sop-large-remaining
