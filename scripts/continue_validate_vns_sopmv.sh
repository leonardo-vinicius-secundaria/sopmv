#!/usr/bin/env bash
# Continua uma validacao SOPMV existente, sem repetir registros ja presentes.
# Uso: ./scripts/continue_validate_vns_sopmv.sh /caminho/para/vns_sopmv_validation_...
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN=${VNS_ADAPTED_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
OUT=${1:?"Uso: $0 /caminho/para/vns_sopmv_validation"}
SEED=${SEED:-202601}
RESULTS="$OUT/results.csv"

[[ -x "$BIN" ]] || { echo "VNS adaptado nao compilado: $BIN" >&2; exit 2; }
[[ -f "$RESULTS" ]] || { echo "CSV inexistente: $RESULTS" >&2; exit 2; }
mkdir -p "$OUT/raw_vns_retry" "$OUT/logs_retry"

INSTANCES=()
for group in sopmv_10 sopmv_20 sopmv_30; do
  while IFS= read -r instance; do INSTANCES+=("$group:small:$instance"); done < <(
    find "$ROOT/data/instancias_pequenas/$group" -maxdepth 1 -type f -name '*.sop' | sort
  )
done
INSTANCES+=(
  "sopmv10:large:$ROOT/data/intancias_grandes/sopmv10/217vm1084_T80_p1.sop"
  "sopmv20:large:$ROOT/data/intancias_grandes/sopmv20/217vm1084_T80_p1.sop"
  "sopmv30:large:$ROOT/data/intancias_grandes/sopmv30/217vm1084_T80_p1.sop"
)

completed=0
for item in "${INSTANCES[@]}"; do
  IFS=: read -r group size instance <<< "$item"
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
  name=$(basename "$instance" .sop)
  key="$group,$size,$name"
  if awk -F, -v key="$key" 'NR > 1 && ($2 "," $3 "," $1) == key { found=1 } END { exit !found }' "$RESULTS"; then
    completed=$((completed + 1))
    continue
  fi

  sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  limit=$(( (3 * sets + 1) / 2 ))
  stamp=$(date +%Y%m%d_%H%M%S)
  work="$OUT/raw_vns_retry/${group}_${size}_${name}_${stamp}"
  mkdir -p "$work"
  echo "Executando: $group/$size/$name (${limit}s)"

  set +e
  "$BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 \
    --output="$work" --results=results.log --save-results=1 --save-info=0 \
    --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 \
    --initial-greedy-solution=1 --use-rvns=0 --seed="$SEED" --time-only-stop=1 \
    --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 \
    --num-iterations-unimproved=2147483647 \
    >"$OUT/logs_retry/${group}_${size}_${name}_${stamp}.log" 2>&1
  exit_code=$?
  set -e

  if [[ ! -s "$work/results.log" ]]; then
    log_file="$OUT/logs_retry/${group}_${size}_${name}_${stamp}.log"
    if rg -q 'mandatory visits require length .* but the budget is' "$log_file"; then
      reason=$(rg 'mandatory visits require length .* but the budget is' "$log_file" | tail -n 1 | sed 's/.*mandatory visits require length /INVIAVEL: obrigatorios requerem comprimento /; s/ but the budget is /, Tmax=/')
    else
      reason="NO_RESULT: VNS nao gerou results.log (exit_code=$exit_code)"
    fi
    printf '%s,%s,%s,%s,%s,%s,,,,"%s"\n' \
      "$name" "$group" "$size" "$SEED" "$sets" "$limit" "$reason" >> "$RESULTS"
    echo "$reason: $group/$size/$name"
    continue
  fi

  if ! validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log" 2>&1); then
    printf '%s,%s,%s,%s,%s,%s,,,,"INVALIDO: %s"\n' \
      "$name" "$group" "$size" "$SEED" "$sets" "$limit" "${validation//$'\n'/ }" >> "$RESULTS"
    echo "INVALIDO: $group/$size/$name"
    continue
  fi
  record=$(tail -n 1 "$work/results.log")
  reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
  distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
  iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,"%s"\n' \
    "$name" "$group" "$size" "$SEED" "$sets" "$limit" "$reward" "$distance" "$iterations" "$validation" \
    >> "$RESULTS"
done

printf 'Concluido. Registros existentes preservados: %s.\n' "$completed"
awk -F, 'NR > 1 { total[$2]++; if($10 ~ /VALIDO/) valid[$2]++; else bad[$2]++ } END { for(g in total) printf "%s: validas=%d, sem/invalidas=%d, total=%d\n", g, valid[g], bad[g], total[g] }' "$RESULTS" | sort
