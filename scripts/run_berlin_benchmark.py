#!/usr/bin/env python3
"""Generate inline SOPMV variants and benchmark CPLEX, SA-PD and greedy."""

import argparse
import csv
import hashlib
import random
import shutil
import subprocess
from pathlib import Path


LEVELS = (0, 10, 20, 30)
TIME_LEVELS = (40, 60, 80)
PROFIT_TYPES = (1, 2)
SOLVERS = (
    ("CPLEX", "sopmv_cplex"),
    ("SA_PD", "sopmv_sa"),
    ("GREEDY", "sopmv_greedy"),
)


def stable_seed(seed: int, stem: str) -> int:
    digest = hashlib.sha256(f"{seed}:{stem}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def parse_set_lines(lines):
    start = next(i for i, line in enumerate(lines) if line.startswith("GTSP_SET_SECTION"))
    rows = []
    for i in range(start + 1, len(lines)):
        fields = lines[i].split()
        if fields and fields[0].lstrip("-").isdigit():
            rows.append((i, fields))
    return start, rows


def generate_family(source: Path, output_dir: Path, seed: int):
    lines = source.read_text().splitlines()
    section, rows = parse_set_lines(lines)
    eligible = [int(fields[0]) for _, fields in rows if float(fields[1]) > 0]
    rng = random.Random(stable_seed(seed, source.stem))
    rng.shuffle(eligible)
    generated = []
    for percent in LEVELS:
        if percent == 0:
            destination = output_dir / source.name
            shutil.copyfile(source, destination)
            generated.append((percent, destination, []))
            continue
        count = int(len(eligible) * percent / 100.0 + 0.5)
        mandatory = set(eligible[:count])
        variant = list(lines)
        variant[section] = "GTSP_SET_SECTION: set_id set_profit mandatory id-vertex-list"
        variant_name = f"{source.stem}_MV{percent}_seed{seed}"
        for i, line in enumerate(variant):
            if line.startswith("NAME:"):
                variant[i] = f"NAME: {variant_name}"
                break
        for i, fields in rows:
            variant[i] = " ".join(fields[:2] + ["1" if int(fields[0]) in mandatory else "0"] + fields[2:])
        destination = output_dir / f"{variant_name}.sop"
        destination.write_text("\n".join(variant) + "\n")
        generated.append((percent, destination, sorted(mandatory)))
    return generated


def run_solver(root: Path, solver: str, executable: str, instance: Path,
               raw_csv: Path, seed: int, cplex_limit: float, sa_limit: float):
    command = [
        str(root / "build" / "bin" / executable),
        "--instance", str(instance),
        "--csv", str(raw_csv),
    ]
    if solver == "CPLEX":
        command += ["--time-limit", str(cplex_limit), "--threads", "1", "--mip-gap", "0",
                    "--seed", str(seed), "--log-level", "0"]
    elif solver == "SA_PD":
        command += ["--seed", str(seed), "--sa-time-limit", str(sa_limit)]
    result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    # CPLEX returns 4 for a proven-infeasible model.
    if result.returncode not in ({0, 4} if solver == "CPLEX" else {0}):
        raise RuntimeError(f"{' '.join(command)} failed ({result.returncode}): {result.stderr}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260928)
    parser.add_argument("--cplex-time-limit", type=float, default=60.0)
    parser.add_argument("--sa-time-limit", type=float, default=10.0)
    parser.add_argument(
        "--output-dir", default="experiments/berlin52_comparacao_4_solvers"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source_dir = root / "data" / "berlin52" / "sop"
    output_dir = root / args.output_dir
    instance_dir = output_dir / "inputs"
    raw_dir = output_dir / "raw"
    instance_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        source_dir / f"11berlin52_T{time}_p{profit}.sop"
        for time in TIME_LEVELS
        for profit in PROFIT_TYPES
    ]
    variants = []
    manifest_rows = []
    for source in sources:
        for percent, path, mandatory in generate_family(source, instance_dir, args.seed):
            variants.append((percent, path))
            manifest_rows.append({"source": source.name, "instance": path.name,
                                  "requested_percent": percent,
                                  "selected_count": len(mandatory),
                                  "mandatory_sets": ";".join(map(str, mandatory)), "seed": args.seed})
    with (output_dir / "manifest.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_rows[0].keys())
        writer.writeheader()
        writer.writerows(manifest_rows)

    result_rows = []
    total_runs = len(variants) * len(SOLVERS)
    for percent, instance in variants:
        for solver, executable in SOLVERS:
            raw_csv = raw_dir / f"{instance.stem}__{solver}.csv"
            if raw_csv.exists():
                raw_csv.unlink()
            run_solver(root, solver, executable, instance, raw_csv, args.seed,
                       args.cplex_time_limit, args.sa_time_limit)
            with raw_csv.open(newline="") as handle:
                row = next(csv.DictReader(handle))
            result_rows.append({"solver": solver, "requested_mandatory_percent": percent,
                                "seed": args.seed, **row})
            print(
                f"[{len(result_rows):02d}/{total_runs}] {solver:6s} {instance.name}",
                flush=True,
            )
    with (output_dir / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_rows[0].keys())
        writer.writeheader()
        writer.writerows(result_rows)


if __name__ == "__main__":
    main()
