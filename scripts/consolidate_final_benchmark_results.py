#!/usr/bin/env python3
"""Consolida os benchmarks finais ILS x VNS em CSVs prontos para analise.

Uso:
  ./scripts/consolidate_final_benchmark_results.py \
      --out new_experiments/final_tables_YYYYMMDD

Os CSVs de entrada sao explicitamente fixados abaixo para impedir que pilotos
antigos ou execucoes futuras sejam incorporados por engano ao resultado final.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BLOCKS = {
    "sop_small": [
        ROOT / "new_experiments/main_ils_vns_sop-small_20261108_102848",
    ],
    "sop_large": [
        ROOT / "new_experiments/main_ils_vns_sop-large-pilot_20261101_194713",
        ROOT / "new_experiments/main_ils_vns_sop-large-batch2_20261102_085249",
        ROOT / "new_experiments/main_ils_vns_sop-large-remaining_20261107_133845",
    ],
    "sopmv_small": [
        ROOT / "new_experiments/main_ils_vns_sopmv-small_20261101_152156",
    ],
    "sopmv_large": [
        ROOT / "new_experiments/main_ils_vns_sopmv-large-pilot_20261102_185511",
        ROOT / "new_experiments/main_ils_vns_sopmv-large-batch1_20261103_101952",
        ROOT / "new_experiments/main_ils_vns_sopmv-large-batch2_20261104_091900",
        ROOT / "new_experiments/main_ils_vns_sopmv-large-batch3_20261105_080555",
        ROOT / "new_experiments/main_ils_vns_sopmv-large-batch4_20261105_203932",
        ROOT / "new_experiments/main_ils_vns_sopmv-large-batch5_20261106_090032",
        ROOT / "new_experiments/main_ils_vns_sopmv-large-batch6_20261106_213903",
    ],
}


def number(value: str) -> float:
    return float(value) if value else float("nan")


def parse_name(instance: str) -> tuple[str, str, str]:
    """Retorna familia, perfil de lucro e percentual MV (vazio em SOP)."""
    parts = instance.split("_")
    family = parts[0]
    profit = next((part for part in parts if part in {"p1", "p2"}), "")
    mandatory = next((part[2:] for part in parts if part.startswith("MV")), "")
    return family, profit, mandatory


def read_runs(directory: Path, algorithm: str) -> dict[tuple[str, str], dict]:
    filename = "ils_runs.csv" if algorithm == "ils" else "vns_runs.csv"
    records: dict[tuple[str, str], dict] = {}
    with (directory / filename).open(newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["instance"], row["seed"])
            if key in records:
                raise ValueError(f"Execucao duplicada em {directory}: {key}")
            records[key] = row
    return records


def safe_mean(values: list[float]) -> float:
    return statistics.mean(values)


def safe_std(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Diretorio de saida")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    all_summary_rows: list[dict] = []
    all_pair_rows: list[dict] = []
    block_rows: list[dict] = []

    for block, directories in BLOCKS.items():
        ils: dict[tuple[str, str], dict] = {}
        vns: dict[tuple[str, str], dict] = {}
        for directory in directories:
            if not directory.is_dir():
                raise FileNotFoundError(f"Diretorio de entrada ausente: {directory}")
            for key, row in read_runs(directory, "ils").items():
                if key in ils:
                    raise ValueError(f"Execucao ILS repetida entre baterias: {key}")
                ils[key] = row
            for key, row in read_runs(directory, "vns").items():
                if key in vns:
                    raise ValueError(f"Execucao VNS repetida entre baterias: {key}")
                vns[key] = row

        if set(ils) != set(vns):
            raise ValueError(f"Pares ILS/VNS diferentes no bloco {block}")

        by_instance: dict[str, list[dict]] = defaultdict(list)
        for key in sorted(ils):
            irow, vrow = ils[key], vns[key]
            iobj, vobj = number(irow["objective"]), number(vrow["objective"])
            best = max(iobj, vobj)
            ils_rpd = 100.0 * (best - iobj) / best if best else 0.0
            vns_rpd = 100.0 * (best - vobj) / best if best else 0.0
            if iobj > vobj:
                outcome = "ILS_WIN"
            elif iobj < vobj:
                outcome = "VNS_WIN"
            else:
                outcome = "TIE"
            pair = {
                "block": block,
                "instance": key[0],
                "seed": key[1],
                "sets_without_depot": int(irow["sets_without_depot"]),
                "time_limit_seconds": int(irow["time_limit_seconds"]),
                "ils_objective": iobj,
                "ils_distance": number(irow["distance"]),
                "ils_elapsed_seconds": number(irow["elapsed_seconds"]),
                "ils_valid": irow["solution_valid"],
                "vns_objective": vobj,
                "vns_distance": number(vrow["distance"]),
                "vns_validation": vrow["validation"],
                "winner": outcome,
                "best_pair_objective": best,
                "ils_rpd_percent": ils_rpd,
                "vns_rpd_percent": vns_rpd,
            }
            all_pair_rows.append(pair)
            by_instance[key[0]].append(pair)

        summaries: list[dict] = []
        for instance, pairs in sorted(by_instance.items()):
            family, profit, mandatory = parse_name(instance)
            ils_objectives = [row["ils_objective"] for row in pairs]
            vns_objectives = [row["vns_objective"] for row in pairs]
            summary = {
                "block": block,
                "instance": instance,
                "family": family,
                "profit_profile": profit,
                "mandatory_percent": mandatory,
                "sets_without_depot": pairs[0]["sets_without_depot"],
                "time_limit_seconds": pairs[0]["time_limit_seconds"],
                "runs": len(pairs),
                "ils_mean": safe_mean(ils_objectives),
                "ils_median": statistics.median(ils_objectives),
                "ils_std": safe_std(ils_objectives),
                "ils_best": max(ils_objectives),
                "ils_worst": min(ils_objectives),
                "ils_valid_runs": sum(row["ils_valid"].lower() == "true" for row in pairs),
                "vns_mean": safe_mean(vns_objectives),
                "vns_median": statistics.median(vns_objectives),
                "vns_std": safe_std(vns_objectives),
                "vns_best": max(vns_objectives),
                "vns_worst": min(vns_objectives),
                "vns_valid_runs": sum("VALIDO reward=" in row["vns_validation"] for row in pairs),
                "ils_seed_wins": sum(row["winner"] == "ILS_WIN" for row in pairs),
                "seed_ties": sum(row["winner"] == "TIE" for row in pairs),
                "vns_seed_wins": sum(row["winner"] == "VNS_WIN" for row in pairs),
                "ils_mean_rpd_percent": safe_mean([row["ils_rpd_percent"] for row in pairs]),
                "vns_mean_rpd_percent": safe_mean([row["vns_rpd_percent"] for row in pairs]),
                "mean_difference_ils_minus_vns": safe_mean(ils_objectives) - safe_mean(vns_objectives),
            }
            summaries.append(summary)
            all_summary_rows.append(summary)

        write_csv(out / f"{block}_by_instance.csv", summaries, list(summaries[0]))
        block_rows.append({
            "block": block,
            "profiles": len(summaries),
            "pairs": len(all_pair_rows) - sum(row["pairs"] for row in block_rows),
            "ils_seed_wins": sum(row["ils_seed_wins"] for row in summaries),
            "seed_ties": sum(row["seed_ties"] for row in summaries),
            "vns_seed_wins": sum(row["vns_seed_wins"] for row in summaries),
            "ils_mean_rpd_percent": safe_mean([row["ils_rpd_percent"] for pair in by_instance.values() for row in pair]),
            "vns_mean_rpd_percent": safe_mean([row["vns_rpd_percent"] for pair in by_instance.values() for row in pair]),
            "ils_valid_runs": sum(row["ils_valid_runs"] for row in summaries),
            "vns_valid_runs": sum(row["vns_valid_runs"] for row in summaries),
        })

    write_csv(out / "all_blocks_by_instance.csv", all_summary_rows, list(all_summary_rows[0]))
    write_csv(out / "paired_seed_results.csv", all_pair_rows, list(all_pair_rows[0]))
    write_csv(out / "block_summary.csv", block_rows, list(block_rows[0]))

    # Exportacoes limpas do ILS no SOP, sem colunas de VNS ou de literatura.
    ils_sop_summary = []
    for row in all_summary_rows:
        if row["block"] not in {"sop_small", "sop_large"}:
            continue
        ils_sop_summary.append({
            "block": row["block"],
            "instance": row["instance"],
            "family": row["family"],
            "profit_profile": row["profit_profile"],
            "sets_without_depot": row["sets_without_depot"],
            "time_limit_seconds": row["time_limit_seconds"],
            "runs": row["runs"],
            "ils_mean_reward": row["ils_mean"],
            "ils_median_reward": row["ils_median"],
            "ils_std_reward": row["ils_std"],
            "ils_best_reward": row["ils_best"],
            "ils_worst_reward": row["ils_worst"],
            "ils_valid_runs": row["ils_valid_runs"],
        })
    write_csv(out / "ils_sop_by_instance.csv", ils_sop_summary, list(ils_sop_summary[0]))

    ils_sop_runs = []
    for row in all_pair_rows:
        if row["block"] not in {"sop_small", "sop_large"}:
            continue
        family, profit, _ = parse_name(row["instance"])
        ils_sop_runs.append({
            "block": row["block"],
            "instance": row["instance"],
            "family": family,
            "profit_profile": profit,
            "seed": row["seed"],
            "sets_without_depot": row["sets_without_depot"],
            "time_limit_seconds": row["time_limit_seconds"],
            "reward": row["ils_objective"],
            "distance": row["ils_distance"],
            "elapsed_seconds": row["ils_elapsed_seconds"],
            "solution_valid": row["ils_valid"],
        })
    write_csv(out / "ils_sop_all_runs.csv", ils_sop_runs, list(ils_sop_runs[0]))

    # O TMS e uma referencia externa: os campos TMS devem ser preenchidos apenas
    # apos confirmar a correspondencia exata de instancia, lucro e Tmax no artigo.
    tms_rows = []
    for row in all_summary_rows:
        if row["block"] != "sop_large":
            continue
        tms_rows.append({
            "instance": row["instance"],
            "family": row["family"],
            "profit_profile": row["profit_profile"],
            "sets_without_depot": row["sets_without_depot"],
            "time_limit_seconds_ils": row["time_limit_seconds"],
            "ils_best": row["ils_best"],
            "ils_mean": row["ils_mean"],
            "ils_median": row["ils_median"],
            "ils_std": row["ils_std"],
            "tms_instance_confirmed": "PENDING",
            "tms_table": "",
            "reference_fb": "",
            "tms_fbest": "",
            "tms_dev_percent": "",
            "tms_favg": "",
            "tms_t_seconds": "",
            "tms_hardware": "",
            "ils_dev_to_reference_fb_percent": "",
            "gap_ils_best_to_tms_fbest_percent": "",
            "gap_ils_mean_to_tms_fbest_percent": "",
            "notes": "Campos TMS seguem a tabela do artigo: fb, fbest, Dev.(%), favg e t(s). Preencher somente apos conferir instancia, lucro e Tmax.",
        })
    write_csv(out / "sop_large_tms_2026_comparison_template.csv", tms_rows, list(tms_rows[0]))

    guide_rows = [
        {"file": "block_summary.csv", "purpose": "Resumo por bloco: pares, vitorias/empates/derrotas, RPD e validade."},
        {"file": "*_by_instance.csv", "purpose": "Tabela por instancia/perfil: media, mediana, desvio, melhor, pior, RPD e validade."},
        {"file": "paired_seed_results.csv", "purpose": "Dados pareados por semente; base para Wilcoxon e graficos."},
        {"file": "ils_sop_by_instance.csv", "purpose": "Resultados somente do ILS em SOP, agregados por instancia/perfil."},
        {"file": "ils_sop_all_runs.csv", "purpose": "Resultados somente do ILS em SOP, uma linha por semente."},
        {"file": "sop_large_tms_2026_comparison_template.csv", "purpose": "Modelo alinhado ao TMS 2026: fb, fbest, Dev.(%), favg e t(s)."},
    ]
    write_csv(out / "files_guide.csv", guide_rows, ["file", "purpose"])
    print(f"CSVs gerados em: {out}")


if __name__ == "__main__":
    main()
