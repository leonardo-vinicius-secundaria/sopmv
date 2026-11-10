#!/usr/bin/env python3
"""Consolida a reproducao final SA-PD (Tabela 6) e a compara a ILS e VNS.

Gera CSVs na pasta final_tables. Os dados sao mantidos por semente para que as
comparacoes sejam auditaveis; os resumos por instancia sao os apropriados para
as tabelas do TCC.
"""
from __future__ import annotations

import csv
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SA_DIR = ROOT / "new_experiments" / "sa_pd_table6_t100_hard_20261108_213252" / "raw"
TABLE_DIR = ROOT / "new_experiments" / "final_tables_20261108"
PAIRS = TABLE_DIR / "paired_seed_results.csv"


def mean(xs):
    return st.fmean(xs) if xs else float("nan")


def med(xs):
    return st.median(xs) if xs else float("nan")


def std(xs):
    return st.stdev(xs) if len(xs) > 1 else 0.0


def family_and_profile(instance: str) -> tuple[str, str]:
    m = re.match(r"(.+)_T100_(p[12])$", instance)
    if not m:
        raise ValueError(f"Nome inesperado: {instance}")
    return m.group(1), m.group(2)


def write_csv(path: Path, fields: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not SA_DIR.is_dir() or not PAIRS.is_file():
        raise SystemExit("Resultados SA-PD ou pares ILS/VNS ausentes.")
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    sa = {}
    for file in sorted(SA_DIR.glob("*.csv")):
        with file.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 1:
            raise SystemExit(f"CSV SA-PD invalido: {file}")
        row = rows[0]
        instance = row["instance"]
        seed_match = re.search(r"_seed(\d+)$", file.stem)
        if not seed_match:
            raise SystemExit(f"Semente ausente no nome: {file}")
        key = (instance, int(seed_match.group(1)))
        if key in sa:
            raise SystemExit(f"Execucao SA duplicada: {key}")
        sa[key] = {
            "objective": float(row["objective"]),
            "distance": float(row["total_distance"]),
            "elapsed_seconds": float(row["elapsed_seconds"]),
            "valid": row["solution_valid"].strip().lower() == "true",
            "status": row["status"],
        }

    ils_vns = {}
    with PAIRS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["block"] != "sop_large":
                continue
            ils_vns[(row["instance"], int(row["seed"]))] = row

    expected = set(ils_vns)
    if set(sa) != expected:
        missing, extra = expected - set(sa), set(sa) - expected
        raise SystemExit(f"Chaves divergentes; faltam={len(missing)}, extras={len(extra)}")

    paired, groups = [], defaultdict(list)
    for key in sorted(sa):
        instance, seed = key
        s = sa[key]
        baseline = ils_vns[key]
        ils = float(baseline["ils_objective"])
        vns = float(baseline["vns_objective"])
        best = max(ils, vns, s["objective"])
        family, profile = family_and_profile(instance)
        row = {
            "instance": instance, "family": family, "profit_profile": profile,
            "seed": seed, "sets_without_depot": int(baseline["sets_without_depot"]),
            "time_limit_seconds": float(baseline["time_limit_seconds"]),
            "ils_objective": ils, "vns_objective": vns,
            "sa_pd_objective": s["objective"], "sa_pd_distance": s["distance"],
            "sa_pd_elapsed_seconds": s["elapsed_seconds"], "sa_pd_valid": s["valid"],
            "best_objective_among_three": best,
            "ils_rpd_percent": 100 * (best - ils) / best,
            "vns_rpd_percent": 100 * (best - vns) / best,
            "sa_pd_rpd_percent": 100 * (best - s["objective"]) / best,
        }
        paired.append(row)
        groups[instance].append(row)

    detail_fields = list(paired[0])
    write_csv(TABLE_DIR / "sa_pd_table6_paired_seed_results.csv", detail_fields, paired)

    summary = []
    total_wins = {"ILS": 0, "VNS": 0, "SA_PD": 0, "TIE": 0}
    for instance, rows in sorted(groups.items()):
        family, profile = family_and_profile(instance)
        ils = [r["ils_objective"] for r in rows]
        vns = [r["vns_objective"] for r in rows]
        sapd = [r["sa_pd_objective"] for r in rows]
        winners = {"ILS": 0, "VNS": 0, "SA_PD": 0, "TIE": 0}
        for row in rows:
            vals = {"ILS": row["ils_objective"], "VNS": row["vns_objective"], "SA_PD": row["sa_pd_objective"]}
            top = max(vals.values())
            names = [name for name, value in vals.items() if value == top]
            if len(names) == 1:
                winners[names[0]] += 1
            else:
                winners["TIE"] += 1
        for name in winners:
            total_wins[name] += winners[name]
        summary.append({
            "instance": instance, "family": family, "profit_profile": profile,
            "sets_without_depot": rows[0]["sets_without_depot"],
            "time_limit_seconds": rows[0]["time_limit_seconds"], "runs": len(rows),
            "ils_mean": mean(ils), "ils_median": med(ils), "ils_std": std(ils), "ils_best": max(ils),
            "vns_mean": mean(vns), "vns_median": med(vns), "vns_std": std(vns), "vns_best": max(vns),
            "sa_pd_mean": mean(sapd), "sa_pd_median": med(sapd), "sa_pd_std": std(sapd), "sa_pd_best": max(sapd),
            "sa_pd_mean_elapsed_seconds": mean([r["sa_pd_elapsed_seconds"] for r in rows]),
            "sa_pd_valid_runs": sum(r["sa_pd_valid"] for r in rows),
            "ils_seed_wins_among_three": winners["ILS"], "vns_seed_wins_among_three": winners["VNS"],
            "sa_pd_seed_wins_among_three": winners["SA_PD"], "seed_ties_among_three": winners["TIE"],
            "ils_mean_rpd_percent": mean([r["ils_rpd_percent"] for r in rows]),
            "vns_mean_rpd_percent": mean([r["vns_rpd_percent"] for r in rows]),
            "sa_pd_mean_rpd_percent": mean([r["sa_pd_rpd_percent"] for r in rows]),
        })
    fields = list(summary[0])
    write_csv(TABLE_DIR / "sa_pd_table6_by_instance.csv", fields, summary)

    all_ils = [r["ils_objective"] for r in paired]
    all_vns = [r["vns_objective"] for r in paired]
    all_sa = [r["sa_pd_objective"] for r in paired]
    overall = [{
        "experiment": "SA-PD Tabela 6 / SOP grande T100",
        "profiles": len(summary), "runs_per_profile": 10, "total_runs_per_algorithm": len(paired),
        "time_rule": "1.5 x Nsets seconds", "sa_pd_valid_runs": sum(r["sa_pd_valid"] for r in paired),
        "ils_mean_rpd_percent": mean([r["ils_rpd_percent"] for r in paired]),
        "vns_mean_rpd_percent": mean([r["vns_rpd_percent"] for r in paired]),
        "sa_pd_mean_rpd_percent": mean([r["sa_pd_rpd_percent"] for r in paired]),
        "ils_best_hits_among_three": sum(x == max(a,b,c) for x,a,b,c in zip(all_ils,all_ils,all_vns,all_sa)),
        "vns_best_hits_among_three": sum(x == max(a,b,c) for x,a,b,c in zip(all_vns,all_ils,all_vns,all_sa)),
        "sa_pd_best_hits_among_three": sum(x == max(a,b,c) for x,a,b,c in zip(all_sa,all_ils,all_vns,all_sa)),
        "exclusive_ils_seed_wins": total_wins["ILS"], "exclusive_vns_seed_wins": total_wins["VNS"],
        "exclusive_sa_pd_seed_wins": total_wins["SA_PD"], "seed_ties_for_best": total_wins["TIE"],
    }]
    write_csv(TABLE_DIR / "sa_pd_table6_overall_summary.csv", list(overall[0]), overall)
    algorithm_summary = [
        {
            "algorithm": "ILS (N=40)", "profiles": len(summary), "runs": len(paired),
            "valid_runs": len(paired),
            "mean_rpd_percent_against_best_of_three": mean([r["ils_rpd_percent"] for r in paired]),
            "best_hits_including_ties": overall[0]["ils_best_hits_among_three"],
            "exclusive_seed_wins": total_wins["ILS"],
        },
        {
            "algorithm": "VNS adaptado", "profiles": len(summary), "runs": len(paired),
            "valid_runs": len(paired),
            "mean_rpd_percent_against_best_of_three": mean([r["vns_rpd_percent"] for r in paired]),
            "best_hits_including_ties": overall[0]["vns_best_hits_among_three"],
            "exclusive_seed_wins": total_wins["VNS"],
        },
        {
            "algorithm": "SA-PD (reimplementacao)", "profiles": len(summary), "runs": len(paired),
            "valid_runs": sum(r["sa_pd_valid"] for r in paired),
            "mean_rpd_percent_against_best_of_three": mean([r["sa_pd_rpd_percent"] for r in paired]),
            "best_hits_including_ties": overall[0]["sa_pd_best_hits_among_three"],
            "exclusive_seed_wins": total_wins["SA_PD"],
        },
    ]
    write_csv(TABLE_DIR / "sa_pd_final_summary.csv", list(algorithm_summary[0]), algorithm_summary)
    print(f"SA-PD: {len(paired)} execucoes, {sum(r['sa_pd_valid'] for r in paired)} validas.")
    print(f"Arquivos gerados em: {TABLE_DIR}")


if __name__ == "__main__":
    main()
