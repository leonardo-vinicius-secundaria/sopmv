#!/usr/bin/env python3
"""Gera um dashboard HTML simples a partir do CSV da bateria SOPMV."""

import argparse
import csv
import html
import statistics
from collections import Counter, defaultdict
from pathlib import Path


COLORS = {"CPLEX": "#2563eb", "SA_PD": "#ea580c", "GREEDY": "#16a34a"}
SOLVERS = tuple(COLORS)


def number(value):
    try:
        return float(value) if value != "" else None
    except (TypeError, ValueError):
        return None


def mean(values):
    clean = [value for value in values if value is not None]
    return statistics.fmean(clean) if clean else None


def grouped_bar(title, ylabel, data, formatter=lambda value: f"{value:.2f}"):
    """data: {categoria: {solver: valor}}."""
    categories = sorted(data, key=lambda value: float(value))
    width, height = 920, 400
    left, right, top, bottom = 72, 24, 48, 65
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [value for group in data.values() for value in group.values() if value is not None]
    ymax = max(values, default=1) or 1
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
             f'<text x="{width / 2}" y="24" text-anchor="middle" class="chart-title">{html.escape(title)}</text>']
    for tick in range(6):
        value = ymax * tick / 5
        y = top + plot_h - plot_h * tick / 5
        parts += [f'<line x1="{left}" y1="{y}" x2="{width-right}" y2="{y}" class="grid"/>',
                  f'<text x="{left-8}" y="{y+4}" text-anchor="end" class="tick">{formatter(value)}</text>']
    group_w = plot_w / max(len(categories), 1)
    bar_w = min(34, group_w / (len(SOLVERS) + 1))
    for category_index, category in enumerate(categories):
        center = left + group_w * (category_index + 0.5)
        for solver_index, solver in enumerate(SOLVERS):
            value = data[category].get(solver)
            if value is None:
                continue
            x = center + (solver_index - 1) * bar_w - bar_w * 0.42
            bar_h = plot_h * value / ymax
            y = top + plot_h - bar_h
            parts.append(f'<rect x="{x}" y="{y}" width="{bar_w*0.84}" height="{bar_h}" fill="{COLORS[solver]}"><title>{solver}: {formatter(value)}</title></rect>')
        parts.append(f'<text x="{center}" y="{height-38}" text-anchor="middle" class="tick">{html.escape(str(category))}%</text>')
    parts.append(f'<text x="18" y="{top + plot_h/2}" transform="rotate(-90 18 {top + plot_h/2})" text-anchor="middle" class="axis">{html.escape(ylabel)}</text>')
    for index, solver in enumerate(SOLVERS):
        x = width - 320 + index * 105
        parts += [f'<rect x="{x}" y="34" width="12" height="12" fill="{COLORS[solver]}"/>',
                  f'<text x="{x+17}" y="44" class="tick">{solver}</text>']
    return "".join(parts) + "</svg>"


def status_chart(rows):
    counts = {solver: Counter(row["status"] for row in rows if row["solver"] == solver)
              for solver in SOLVERS}
    statuses = sorted({status for counter in counts.values() for status in counter})
    header = "".join(f"<th>{html.escape(status)}</th>" for status in statuses)
    body = []
    for solver in SOLVERS:
        cells = "".join(f"<td>{counts[solver][status]}</td>" for status in statuses)
        body.append(f'<tr><th><span class="dot" style="background:{COLORS[solver]}"></span>{solver}</th>{cells}</tr>')
    return f'<table><thead><tr><th>Método</th>{header}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def main():
    root = Path(__file__).resolve().parents[1]
    experiment = root / "experiments" / "berlin52_comparacao_4_solvers"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", default=experiment / "results.csv", help="CSV consolidado")
    parser.add_argument("-o", "--output", default=experiment / "dashboard.html", help="HTML de saída")
    args = parser.parse_args()
    csv_path, output_path = Path(args.csv), Path(args.output)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("CSV vazio")

    objective, elapsed, gap = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list)), defaultdict(list)
    for row in rows:
        percent, solver = row["requested_mandatory_percent"], row["solver"]
        objective[percent][solver].append(number(row["objective"]))
        elapsed[percent][solver].append(number(row["elapsed_seconds"]))
        if solver == "CPLEX":
            gap[percent].append(number(row["gap"]))
    objective_avg = {p: {s: mean(v) for s, v in groups.items()} for p, groups in objective.items()}
    elapsed_avg = {p: {s: mean(v) for s, v in groups.items()} for p, groups in elapsed.items()}
    gap_avg = {p: {"CPLEX": (mean(v) * 100 if mean(v) is not None else None)} for p, v in gap.items()}
    valid = sum(row["solution_valid"].lower() == "true" for row in rows)
    feasible = sum(number(row["objective"]) is not None for row in rows)

    document = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Resultados SOPMV</title>
<style>
body{{font:15px system-ui,sans-serif;margin:0;background:#f4f6f8;color:#172033}}main{{max-width:1100px;margin:auto;padding:28px}}
h1{{margin:0 0 6px}}.subtitle{{color:#5b6472;margin-bottom:22px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
.card,.panel{{background:white;border-radius:12px;padding:18px;box-shadow:0 2px 9px #0001}}.value{{font-size:28px;font-weight:700}}
.panel{{margin-top:16px;overflow-x:auto}}svg{{width:100%;min-width:650px}}.grid{{stroke:#dfe3e8;stroke-width:1}}.tick{{font-size:11px;fill:#566070}}
.axis{{font-size:12px;fill:#374151}}.chart-title{{font-size:16px;font-weight:650;fill:#172033}}table{{border-collapse:collapse;width:100%}}
th,td{{padding:10px;border-bottom:1px solid #e5e7eb;text-align:center}}th:first-child{{text-align:left}}.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px}}
@media(max-width:700px){{.cards{{grid-template-columns:1fr}}main{{padding:16px}}}}
</style></head><body><main><h1>Resultados SOPMV — 11berlin52</h1>
<div class="subtitle">Arquivo: {html.escape(csv_path.name)} · percentuais no eixo X são os níveis solicitados.</div>
<section class="cards"><div class="card"><div class="value">{len(rows)}</div>execuções</div>
<div class="card"><div class="value">{feasible}</div>soluções encontradas</div>
<div class="card"><div class="value">{valid}</div>soluções validadas</div></section>
<section class="panel">{grouped_bar("Objetivo médio por nível", "Objetivo médio", objective_avg)}</section>
<section class="panel">{grouped_bar("Tempo médio por nível", "Segundos", elapsed_avg)}</section>
<section class="panel">{grouped_bar("Gap médio do CPLEX", "Gap (%)", gap_avg)}</section>
<section class="panel"><h2>Status das execuções</h2>{status_chart(rows)}</section>
</main></body></html>'''
    output_path.write_text(document, encoding="utf-8")
    print(f"Dashboard gerado: {output_path.resolve()}")


if __name__ == "__main__":
    main()
