#!/usr/bin/env python3
"""Consolida ILS x SA-PD no SOPMV grande T100 usando a última linha por seed."""
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SA_DIR = ROOT / "new_experiments" / "main_sa_pd_sopmv-large_20261112"
OUT = ROOT / "new_experiments" / "sa_pd_ils_sopmv_final_20261115"
ILS_DIRS = [
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-pilot_20261102_185511",
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-batch1_20261103_101952",
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-batch2_20261104_091900",
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-batch3_20261105_080555",
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-batch4_20261105_203932",
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-batch5_20261106_090032",
    ROOT / "new_experiments" / "main_ils_vns_sopmv-large-batch6_20261106_213903",
]
FAMILY_ORDER = [
    "80rd400", "84fl417", "88pr439", "89pcb442", "99d493", "115rat575",
    "115u574", "131p654", "132d657", "145u724", "157rat783", "201pr1002",
    "212u1060", "217vm1084",
]

def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def ident(name):
    family, suffix = name.split("_T100_")
    profile, ratio = suffix.split("_MV")
    return family, profile, int(ratio)

def avg(values): return st.fmean(values)
def std(values): return st.stdev(values) if len(values) > 1 else 0.0
def fmt(value, digits=1):
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", "{,}").replace("X", r"\,")
def integer(value): return f"{int(round(float(value))):,}".replace(",", r"\,")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ils = {}
    for directory in ILS_DIRS:
        with (directory / "ils_runs.csv").open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                key = row["instance"], int(row["seed"])
                if key in ils: raise RuntimeError(f"ILS duplicado: {key}")
                ils[key] = row

    sa, duplicated, discarded, divergent = {}, 0, 0, 0
    for path in sorted((SA_DIR / "raw_sa").glob("*.csv")):
        with path.open(encoding="utf-8", newline="") as f: rows = list(csv.DictReader(f))
        if not rows: raise RuntimeError(f"SA-PD vazio: {path}")
        selected = rows[-1]
        seed = int(path.stem.rsplit("_seed", 1)[1])
        key = selected["instance"], seed
        if key in sa: raise RuntimeError(f"SA-PD duplicado: {key}")
        sa[key] = {**selected, "seed": seed, "raw_csv": str(path), "raw_rows": len(rows)}
        if len(rows) > 1:
            duplicated += 1; discarded += len(rows) - 1
            divergent += any((r["objective"], r["total_distance"]) != (selected["objective"], selected["total_distance"]) for r in rows[:-1])
    if set(ils) != set(sa): raise RuntimeError(f"Chaves: ILS={len(ils)} SA={len(sa)}")

    paired, groups = [], defaultdict(list)
    for key in sorted(ils):
        i, s = ils[key], sa[key]; io, so = float(i["objective"]), float(s["objective"])
        best = max(io, so); family, profile, ratio = ident(key[0])
        winner = "ILS_WIN" if io > so else "SA_PD_WIN" if so > io else "TIE"
        row = {
            "instance": key[0], "family": family, "profit_profile": profile, "mandatory_percent": ratio,
            "seed": key[1], "sets_without_depot": int(i["sets_without_depot"]), "time_limit_seconds": int(i["time_limit_seconds"]),
            "ils_objective": io, "ils_distance": float(i["distance"]), "ils_elapsed_seconds": float(i["elapsed_seconds"]), "ils_valid": i["solution_valid"].lower() == "true",
            "sa_pd_objective": so, "sa_pd_distance": float(s["total_distance"]), "sa_pd_elapsed_seconds": float(s["elapsed_seconds"]), "sa_pd_valid": s["solution_valid"].lower() == "true",
            "winner": winner, "best_pair_objective": best,
            "ils_rpd_percent": 100 * (best - io) / best if best else 0.0, "sa_pd_rpd_percent": 100 * (best - so) / best if best else 0.0,
            "sa_pd_raw_csv": s["raw_csv"], "sa_pd_raw_rows": s["raw_rows"],
        }
        paired.append(row); groups[key[0]].append(row)
    write_csv(OUT / "sa_pd_ils_sopmv_paired_seed_results.csv", paired)

    by_instance = []
    for instance, rows in sorted(groups.items()):
        family, profile, ratio = ident(instance); ilsv = [r["ils_objective"] for r in rows]; sav = [r["sa_pd_objective"] for r in rows]
        ib, sb = max(ilsv), max(sav)
        by_instance.append({
            "instance": instance, "family": family, "profit_profile": profile, "mandatory_percent": ratio,
            "sets_without_depot": rows[0]["sets_without_depot"], "time_limit_seconds": rows[0]["time_limit_seconds"], "runs": len(rows),
            "ils_mean": avg(ilsv), "ils_std": std(ilsv), "ils_best": ib,
            "sa_pd_mean": avg(sav), "sa_pd_std": std(sav), "sa_pd_best": sb,
            "best_gap_sa_pd_to_ils_percent": 100 * (ib - sb) / ib,
            "ils_seed_wins": sum(r["winner"] == "ILS_WIN" for r in rows), "seed_ties": sum(r["winner"] == "TIE" for r in rows), "sa_pd_seed_wins": sum(r["winner"] == "SA_PD_WIN" for r in rows),
            "ils_mean_rpd_percent": avg([r["ils_rpd_percent"] for r in rows]), "sa_pd_mean_rpd_percent": avg([r["sa_pd_rpd_percent"] for r in rows]),
            "ils_valid_runs": sum(r["ils_valid"] for r in rows), "sa_pd_valid_runs": sum(r["sa_pd_valid"] for r in rows),
        })
    write_csv(OUT / "sa_pd_ils_sopmv_by_instance.csv", by_instance)

    by_ratio = []
    for ratio in (10, 20, 30):
        rows = [r for r in paired if r["mandatory_percent"] == ratio]
        by_ratio.append({
            "mandatory_percent": ratio, "profiles": len({r["instance"] for r in rows}), "pairs": len(rows),
            "ils_seed_wins": sum(r["winner"] == "ILS_WIN" for r in rows), "seed_ties": sum(r["winner"] == "TIE" for r in rows), "sa_pd_seed_wins": sum(r["winner"] == "SA_PD_WIN" for r in rows),
            "ils_mean_rpd_percent": avg([r["ils_rpd_percent"] for r in rows]), "sa_pd_mean_rpd_percent": avg([r["sa_pd_rpd_percent"] for r in rows]),
            "ils_valid_runs": sum(r["ils_valid"] for r in rows), "sa_pd_valid_runs": sum(r["sa_pd_valid"] for r in rows),
        })
    write_csv(OUT / "sa_pd_ils_sopmv_by_mandatory_percent.csv", by_ratio)

    overall = [{
        "experiment": "ILS versus SA-PD / SOPMV grande T100", "profiles": len(by_instance), "runs_per_profile": 10, "pairs": len(paired),
        "ils_seed_wins": sum(r["winner"] == "ILS_WIN" for r in paired), "seed_ties": sum(r["winner"] == "TIE" for r in paired), "sa_pd_seed_wins": sum(r["winner"] == "SA_PD_WIN" for r in paired),
        "ils_mean_rpd_percent": avg([r["ils_rpd_percent"] for r in paired]), "sa_pd_mean_rpd_percent": avg([r["sa_pd_rpd_percent"] for r in paired]),
        "ils_valid_runs": sum(r["ils_valid"] for r in paired), "sa_pd_valid_runs": sum(r["sa_pd_valid"] for r in paired),
        "sa_pd_raw_files": len(sa), "sa_pd_duplicate_files": duplicated, "sa_pd_discarded_duplicate_rows": discarded, "sa_pd_divergent_duplicate_files": divergent,
        "deduplication_rule": "last physical data row of each raw SA-PD CSV",
    }]
    write_csv(OUT / "sa_pd_ils_sopmv_overall_summary.csv", overall)

    tex = [
        "% === CORPO PRINCIPAL: ILS versus SA-PD no SOPMV grande ===", r"\begin{longtable}{llrrr|rrr}",
        r"\caption{Comparação de qualidade entre ILS e SA-PD nas instâncias SOPMV grandes com $\omega=1{,}0$ ($T100$).} \label{tab:ils-sapd-sopmv-large}\\", r"\toprule",
        r"& & \multicolumn{3}{c}{Perfil g1 (p1)} & \multicolumn{3}{c}{Perfil g2 (p2)} \\", r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}",
        r"Obrigatórios & Instância & ILS $f_{best}$ & SA-PD $f_{best}$ & Dev. (\%) & ILS $f_{best}$ & SA-PD $f_{best}$ & Dev. (\%) \\", r"\midrule", r"\endfirsthead",
        r"\toprule", r"Obrigatórios & Instância & ILS $f_{best}$ & SA-PD $f_{best}$ & Dev. (\%) & ILS $f_{best}$ & SA-PD $f_{best}$ & Dev. (\%) \\", r"\midrule", r"\endhead",
    ]
    families = FAMILY_ORDER
    for ratio in (10, 20, 30):
        for family in families:
            p1 = next(r for r in by_instance if r["family"] == family and r["profit_profile"] == "p1" and r["mandatory_percent"] == ratio)
            p2 = next(r for r in by_instance if r["family"] == family and r["profit_profile"] == "p2" and r["mandatory_percent"] == ratio)
            tex.append(f"{ratio}\\% & {family} & {integer(p1['ils_best'])} & {integer(p1['sa_pd_best'])} & {fmt(p1['best_gap_sa_pd_to_ils_percent'], 3)} & {integer(p2['ils_best'])} & {integer(p2['sa_pd_best'])} & {fmt(p2['best_gap_sa_pd_to_ils_percent'], 3)} " + r"\\")
        tex.append(r"\midrule")
    tex += [r"\multicolumn{8}{l}{\footnotesize Dev.(\%) = $100(f_{best}^{ILS}-f_{best}^{SA-PD})/f_{best}^{ILS}$; valores positivos favorecem o ILS.} \\", r"\bottomrule", r"\end{longtable}", ""]
    (OUT / "sa_pd_ils_sopmv_table.tex").write_text("\n".join(tex), encoding="utf-8")
    print(f"Gerado em: {OUT}")

if __name__ == "__main__": main()
