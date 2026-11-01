#!/usr/bin/env python3
"""Consolida a calibracao unifatorial do intervalo de reset do ILS."""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def number(value: str) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} DIRETORIO_DA_CALIBRACAO", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    manifest = root / "manifest.csv"
    if not manifest.is_file():
        print(f"Manifesto inexistente: {manifest}", file=sys.stderr)
        return 2

    rows: list[dict[str, object]] = []
    with manifest.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            csv_path = Path(str(item["csv_path"]))
            with csv_path.open(newline="", encoding="utf-8") as result_file:
                result = next(csv.DictReader(result_file), None)
            if result is None:
                raise RuntimeError(f"CSV sem resultado: {csv_path}")
            objective = number(result["objective"])
            distance = number(result["total_distance"])
            valid = result["solution_valid"].lower() == "true"
            rows.append({
                "reset_interval": int(item["reset_interval"]),
                "instance": item["instance"], "seed": int(item["seed"]),
                "objective": objective, "distance": distance,
                "elapsed_seconds": number(result["elapsed_seconds"]),
                "valid": valid,
            })

    by_case: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_case[(str(row["instance"]), int(row["seed"]))].append(row)
    for case_rows in by_case.values():
        feasible = [r for r in case_rows if r["valid"] and r["objective"] is not None]
        if not feasible:
            raise RuntimeError("nenhum resultado viavel em um caso de calibracao")
        best_reward = max(float(r["objective"]) for r in feasible)
        best_distance = min(float(r["distance"]) for r in feasible if float(r["objective"]) == best_reward)
        for row in case_rows:
            reward = row["objective"]
            distance = row["distance"]
            row["rpd"] = None if reward is None else 100.0 * (best_reward - float(reward)) / best_reward
            row["win"] = bool(reward == best_reward and distance == best_distance)

    detail_path = root / "calibration_results.csv"
    with detail_path.open("w", newline="", encoding="utf-8") as handle:
        fields = ["reset_interval", "instance", "seed", "objective", "distance", "elapsed_seconds", "valid", "rpd", "win"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["reset_interval"])].append(row)
    summary = []
    for interval, values in grouped.items():
        rpds = [float(v["rpd"]) for v in values if v["rpd"] is not None]
        summary.append({
            "reset_interval": interval,
            "runs": len(values),
            "valid_runs": sum(bool(v["valid"]) for v in values),
            "mean_rpd_percent": statistics.mean(rpds),
            "median_rpd_percent": statistics.median(rpds),
            "wins": sum(bool(v["win"]) for v in values),
            "mean_elapsed_seconds": statistics.mean(float(v["elapsed_seconds"]) for v in values if v["elapsed_seconds"] is not None),
        })
    summary.sort(key=lambda x: (x["mean_rpd_percent"], x["median_rpd_percent"], -x["wins"], x["reset_interval"]))
    summary_path = root / "calibration_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    print("Ranking por RPD medio (menor e melhor):")
    for item in summary:
        print(
            f"N={item['reset_interval']}: RPD medio={item['mean_rpd_percent']:.4f}% | "
            f"mediana={item['median_rpd_percent']:.4f}% | vitorias={item['wins']} | "
            f"validas={item['valid_runs']}/{item['runs']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
