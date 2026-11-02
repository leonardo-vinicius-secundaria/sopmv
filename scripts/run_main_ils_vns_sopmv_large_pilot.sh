#!/usr/bin/env bash
# Piloto SOPMV grande: 80rd400 e 217vm1084, p1/p2, MV10/MV20/MV30,
# 10 sementes, ILS N=40 versus VNS adaptado com o mesmo tempo por par.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec "$ROOT/scripts/run_main_ils_vns.sh" sopmv-large-pilot
