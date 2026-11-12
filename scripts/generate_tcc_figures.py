#!/usr/bin/env python3
"""Gera figuras de resultados para o TCC a partir dos CSVs consolidados."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "new_experiments/final_tables_20261108/paired_seed_results.csv"
SA_PD_SOURCE = ROOT / "new_experiments/final_tables_20261108/sa_pd_table6_paired_seed_results.csv"
OUT = ROOT / "new_experiments/final_tables_20261108/figures"

COLORS = {"ILS_WIN": "#287D3C", "TIE": "#B0B7C3", "VNS_WIN": "#BE3F3F"}


def label(row: dict[str, str]) -> str | None:
    block = row["block"]
    if block == "sop_small":
        return "SOP\npequeno"
    if block == "sop_large":
        return "SOP\ngrande"
    if block == "sopmv_small":
        return "SOPMV\npequeno"
    if block == "sopmv_large":
        return f"SOPMV\ngrande MV{row['instance'].split('_MV')[-1]}"
    return None


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with SOURCE.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    order = ["SOP\npequeno", "SOP\ngrande", "SOPMV\npequeno",
             "SOPMV\ngrande MV10", "SOPMV\ngrande MV20", "SOPMV\ngrande MV30"]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        group = label(row)
        if group:
            grouped[group].append(row)

    # Figura 1: proporção de vitórias, empates e derrotas por bloco.
    fig, ax = plt.subplots(figsize=(10.2, 5.5))
    bottoms = [0.0] * len(order)
    for outcome, title in (("ILS_WIN", "Vitória ILS"), ("TIE", "Empate"), ("VNS_WIN", "Vitória VNS")):
        values = []
        for group in order:
            group_rows = grouped[group]
            values.append(100 * sum(row["winner"] == outcome for row in group_rows) / len(group_rows))
        ax.bar(range(len(order)), values, bottom=bottoms, color=COLORS[outcome], edgecolor="white", linewidth=0.8, label=title)
        for index, (value, bottom) in enumerate(zip(values, bottoms)):
            if value >= 8:
                ax.text(index, bottom + value / 2, f"{value:.1f}%", ha="center", va="center", fontsize=8,
                        color="white" if outcome != "TIE" else "black", fontweight="bold")
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    ax.set_ylim(0, 100)
    ax.set_ylabel("Proporção de pares de execuções (\%)")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13), frameon=False)
    fig.tight_layout()
    save(fig, "win_tie_loss_by_block")

    # Figura 2: qualidade relativa por par, sem misturar escalas de recompensa.
    rpd_groups = ["SOP grande", "SOPMV MV10", "SOPMV MV20", "SOPMV MV30"]
    selectors = {
        "SOP grande": lambda r: r["block"] == "sop_large",
        "SOPMV MV10": lambda r: r["block"] == "sopmv_large" and r["instance"].endswith("_MV10"),
        "SOPMV MV20": lambda r: r["block"] == "sopmv_large" and r["instance"].endswith("_MV20"),
        "SOPMV MV30": lambda r: r["block"] == "sopmv_large" and r["instance"].endswith("_MV30"),
    }
    data, positions, colors, labels = [], [], [], []
    for index, group in enumerate(rpd_groups):
        selected = [r for r in rows if selectors[group](r)]
        data.extend([
            [float(r["ils_rpd_percent"]) for r in selected],
            [float(r["vns_rpd_percent"]) for r in selected],
        ])
        positions.extend([index * 3 + 1, index * 3 + 2])
        colors.extend(["#287D3C", "#BE3F3F"])
        labels.extend(["ILS", "VNS"])
    fig, ax = plt.subplots(figsize=(11, 5.7))
    box = ax.boxplot(data, positions=positions, widths=0.68, patch_artist=True, showfliers=True,
                     medianprops={"color": "black", "linewidth": 1.3},
                     whiskerprops={"color": "#555555"}, capprops={"color": "#555555"},
                     flierprops={"marker": "o", "markersize": 2.5, "markerfacecolor": "#555555", "alpha": 0.45})
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    for x in (3.5, 6.5, 9.5):
        ax.axvline(x, color="#D5D9E0", linewidth=0.9)
    for index, group in enumerate(rpd_groups):
        ax.text(index * 3 + 1.5, 1.02, group, transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("RPD em relação ao melhor valor do par (\%)")
    ax.set_ylim(bottom=-0.03)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(handles=[Patch(facecolor="#287D3C", alpha=0.75, label="ILS"), Patch(facecolor="#BE3F3F", alpha=0.75, label="VNS adaptado")],
              loc="upper right", frameon=False)
    fig.tight_layout()
    save(fig, "rpd_boxplots_large_instances")

    # Figura 3: comparacao direta e pareada dos tres metodos no mesmo lote
    # SOP grande T100.  O RPD usa o melhor objetivo entre ILS, VNS e SA-PD
    # para cada instancia/semente; valores menores sao melhores.
    with SA_PD_SOURCE.open(newline="", encoding="utf-8") as handle:
        three_way_rows = list(csv.DictReader(handle))
    methods = [
        ("ILS", "ils_rpd_percent", "#287D3C"),
        ("VNS adaptado", "vns_rpd_percent", "#BE3F3F"),
        ("SA-PD", "sa_pd_rpd_percent", "#396EAA"),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 5.3))
    box = ax.boxplot(
        [[float(row[column]) for row in three_way_rows] for _, column, _ in methods],
        widths=0.58, patch_artist=True, showfliers=True,
        medianprops={"color": "black", "linewidth": 1.3},
        whiskerprops={"color": "#555555"}, capprops={"color": "#555555"},
        flierprops={"marker": "o", "markersize": 2.5, "markerfacecolor": "#555555", "alpha": 0.45},
    )
    for patch, (_, _, color) in zip(box["boxes"], methods):
        patch.set_facecolor(color)
        patch.set_alpha(0.78)
    ax.set_xticklabels([name for name, _, _ in methods])
    ax.set_ylabel("RPD em rela\u00e7\u00e3o ao melhor valor entre os tr\u00eas (\%)")
    ax.set_title("SOP grande ($T100$): distribui\u00e7\u00e3o por 280 execu\u00e7\u00f5es pareadas")
    ax.set_ylim(bottom=-0.03)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "rpd_boxplot_ils_vns_sa_pd_sop_grande_t100")

    print(f"Figuras geradas em: {OUT}")


if __name__ == "__main__":
    main()
