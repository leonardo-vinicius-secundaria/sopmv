#!/usr/bin/env python3
"""Executa o ILS nas instancias e junta com o benchmark de tres metodos."""

import argparse
import csv
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark-dir", default="experiments/berlin52_comparacao_4_solvers"
    )
    parser.add_argument("--time-limit", type=float, default=3.0)
    parser.add_argument("--iterations", type=int, default=1000000)
    parser.add_argument("--perturbation", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260928)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    bench = root / args.benchmark_dir
    with (bench / "results.csv").open(newline="") as handle:
        existing = list(csv.DictReader(handle))
    expected_instances = 3 * 2 * 4  # T40/T60/T80, p1/p2 e quatro percentuais.
    expected_rows = expected_instances * 3  # CPLEX, SA-PD e Greedy.
    if len(existing) != expected_rows:
        raise SystemExit(
            f"esperadas {expected_rows} linhas no benchmark original; "
            f"encontradas {len(existing)}"
        )

    combinations = []
    seen = set()
    for row in existing:
        key = (row["instance"], row["requested_mandatory_percent"])
        if key not in seen:
            combinations.append(key)
            seen.add(key)

    if len(combinations) != expected_instances:
        raise SystemExit(
            f"esperadas {expected_instances} instancias distintas; "
            f"encontradas {len(combinations)}"
        )

    ils_rows = []
    raw_dir = bench / "raw_ils"
    raw_dir.mkdir(exist_ok=True)
    for index, (instance_name, percent) in enumerate(combinations, 1):
        instance = bench / "inputs" / f"{instance_name}.sop"
        raw_csv = raw_dir / f"{instance_name}__ILS.csv"
        if raw_csv.exists():
            raw_csv.unlink()
        command = [
            str(root / "build" / "bin" / "sopmv_ils"), "--instance", str(instance),
            "--ils-time-limit", str(args.time_limit),
            "--ils-iterations", str(args.iterations),
            "--ils-perturbation", str(args.perturbation),
            "--seed", str(args.seed), "--csv", str(raw_csv),
        ]
        result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"ILS falhou em {instance.name}: {result.stderr}")
        with raw_csv.open(newline="") as handle:
            row = next(csv.DictReader(handle))
        ils_rows.append({"solver": "ILS", "requested_mandatory_percent": percent,
                         "seed": str(args.seed), **row})
        print(f"[{index:02d}/{len(combinations)}] ILS {instance.name}", flush=True)

    combined = existing + ils_rows
    output = bench / "results_4_solvers.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=combined[0].keys())
        writer.writeheader()
        writer.writerows(combined)
    print(f"CSV consolidado: {output}")


if __name__ == "__main__":
    main()
