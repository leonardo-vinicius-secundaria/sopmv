#!/usr/bin/env python3
"""Gera gráfico interativo de tempo x qualidade para os quatro resolvedores."""

import argparse
import csv
import html
import math
from collections import defaultdict
from pathlib import Path


SOLVERS = ("CPLEX", "SA_PD", "GREEDY", "ILS")
COLORS = {"CPLEX": "#2563eb", "SA_PD": "#f97316", "GREEDY": "#16a34a", "ILS": "#9333ea"}
LABELS = {"0": "SOP", "10": "SOPMV 10%", "20": "SOPMV 20%", "30": "SOPMV 30%"}


def numeric(value):
    try:
        return float(value) if value != "" else None
    except ValueError:
        return None


def fmt_time(seconds):
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.1f} µs"
    if seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    return f"{seconds:.3f} s"


def panel(category, rows, x_min, x_max):
    width, height = 670, 390
    left, right, top, bottom = 70, 24, 44, 60
    plot_w, plot_h = width - left - right, height - top - bottom

    def x_pos(seconds):
        value = math.log10(max(seconds, 1e-7))
        return left + (value - x_min) / (x_max - x_min) * plot_w

    def y_pos(quality):
        return top + (105 - quality) / 105 * plot_h

    output = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{LABELS[category]}">',
              f'<text x="{width/2}" y="24" text-anchor="middle" class="chart-title">{LABELS[category]}</text>']
    for quality in (0, 20, 40, 60, 80, 100):
        y = y_pos(quality)
        output.append(f'<line x1="{left}" y1="{y}" x2="{width-right}" y2="{y}" class="grid"/>')
        output.append(f'<text x="{left-8}" y="{y+4}" text-anchor="end" class="tick">{quality}%</text>')
    time_ticks = (1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10)
    for seconds in time_ticks:
        log_value = math.log10(seconds)
        if x_min <= log_value <= x_max:
            x = x_pos(seconds)
            output.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{height-bottom}" class="grid vertical"/>')
            output.append(f'<text x="{x}" y="{height-34}" text-anchor="middle" class="tick">{fmt_time(seconds)}</text>')
    offsets = {"CPLEX": (-5, -3), "SA_PD": (-4, 4), "GREEDY": (4, -3), "ILS": (5, 4)}
    for row in rows:
        objective = numeric(row["objective"])
        quality = numeric(row["quality_percent"])
        seconds = numeric(row["elapsed_seconds"])
        if objective is None or quality is None or seconds is None:
            continue
        dx, dy = offsets[row["solver"]]
        x, y = x_pos(seconds) + dx, y_pos(quality) + dy
        tooltip = (f'{row["instance"]} | {row["solver"]} | objetivo={objective:g} | '
                   f'qualidade={quality:.2f}% | tempo={fmt_time(seconds)}')
        output.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{COLORS[row["solver"]]}" '
                      f'class="point"><title>{html.escape(tooltip)}</title></circle>')
    output.append(f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" '
                  'text-anchor="middle" class="axis">Qualidade relativa</text>')
    output.append(f'<text x="{left+plot_w/2}" y="{height-7}" text-anchor="middle" class="axis">Tempo por execução (escala logarítmica)</text>')
    return "".join(output) + "</svg>"


def detail_table(rows):
    grouped = defaultdict(dict)
    metadata = {}
    for row in rows:
        grouped[row["instance"]][row["solver"]] = row
        metadata[row["instance"]] = row["requested_mandatory_percent"]
    body = []
    for instance in sorted(grouped, key=lambda name: (int(metadata[name]), name)):
        cells = []
        for solver in SOLVERS:
            row = grouped[instance][solver]
            objective = numeric(row["objective"])
            seconds = numeric(row["elapsed_seconds"])
            if objective is None:
                cells.append(f'<td><span class="missing">sem solução</span><small>{html.escape(row["status"])}</small></td>')
            else:
                cells.append(f'<td><strong>{objective:g}</strong><small>{fmt_time(seconds)}</small></td>')
        body.append(f'<tr><td>{html.escape(LABELS[metadata[instance]])}</td><th>{html.escape(instance)}</th>{"".join(cells)}</tr>')
    solver_headers = "".join(f'<th style="color:{COLORS[s]}">{s}</th>' for s in SOLVERS)
    return f'<table><thead><tr><th>Categoria</th><th>Instância</th>{solver_headers}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / "experiments" / "berlin52_comparacao_4_solvers"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=directory / "results_4_solvers.csv")
    parser.add_argument("-o", "--output", default=directory / "tempo_qualidade.html")
    args = parser.parse_args()
    csv_path, output_path = Path(args.csv), Path(args.output)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    by_instance = defaultdict(list)
    for row in rows:
        by_instance[row["instance"]].append(row)
    for instance_rows in by_instance.values():
        objectives = [numeric(row["objective"]) for row in instance_rows]
        best = max((value for value in objectives if value is not None), default=None)
        for row in instance_rows:
            objective = numeric(row["objective"])
            row["quality_percent"] = "" if objective is None or not best else str(100 * objective / best)

    times = [numeric(row["elapsed_seconds"]) for row in rows if numeric(row["elapsed_seconds"]) is not None]
    x_min = math.floor(math.log10(max(min(times), 1e-7))) - 0.15
    x_max = math.ceil(math.log10(max(times))) + 0.15
    panels = "".join(f'<section class="panel">{panel(category, [r for r in rows if r["requested_mandatory_percent"] == category], x_min, x_max)}</section>'
                     for category in ("0", "10", "20", "30"))
    legend = "".join(f'<span><i style="background:{COLORS[s]}"></i>{s}</span>' for s in SOLVERS)
    document = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Tempo × qualidade — SOPMV</title>
<style>
body{{font:14px system-ui,sans-serif;margin:0;background:#f3f5f8;color:#172033}}main{{max-width:1450px;margin:auto;padding:26px}}
h1{{margin:0 0 6px}}.intro{{max-width:1000px;color:#505a68;line-height:1.5}}.legend{{display:flex;gap:22px;margin:18px 0;flex-wrap:wrap}}
.legend span{{display:flex;align-items:center;gap:7px;font-weight:600}}.legend i{{width:12px;height:12px;border-radius:50%}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.panel,.table-panel{{background:white;border-radius:12px;padding:12px;box-shadow:0 2px 9px #0001;overflow:auto}}
svg{{width:100%;min-width:570px}}.grid{{stroke:#dfe3e8;stroke-width:1}}.vertical{{stroke-dasharray:3 4}}.tick{{font-size:10px;fill:#596273}}
.axis{{font-size:12px;fill:#374151}}.chart-title{{font-size:16px;font-weight:700;fill:#172033}}.point{{stroke:white;stroke-width:1.5;opacity:.86}}.point:hover{{r:9;opacity:1}}
.table-panel{{margin-top:18px}}table{{border-collapse:collapse;width:100%;min-width:950px}}th,td{{padding:9px;border-bottom:1px solid #e5e7eb;text-align:center}}th:nth-child(2){{text-align:left}}
td small{{display:block;color:#657080;margin-top:3px}}.missing{{color:#a11;display:block}}@media(max-width:950px){{.charts{{grid-template-columns:1fr}}}}
</style></head><body><main><h1>Tempo × qualidade da solução</h1>
<p class="intro">Cada ponto representa uma execução individual. Quanto mais à esquerda, mais rápido; quanto mais acima, melhor a solução. A qualidade é o objetivo dividido pelo maior objetivo encontrado pelos quatro métodos na mesma instância. Passe o mouse sobre um ponto para ver os valores exatos.</p>
<div class="legend">{legend}</div><div class="charts">{panels}</div>
<section class="table-panel"><h2>Objetivo e tempo de cada execução</h2>{detail_table(rows)}</section>
</main></body></html>'''
    output_path.write_text(document, encoding="utf-8")
    print(f"Gráfico gerado: {output_path.resolve()}")


if __name__ == "__main__":
    main()
