#!/usr/bin/env python3
"""Gera CSVs agregados e trechos LaTeX finais para o TCC.

Fonte primária: new_experiments/final_tables_20261108.
Os valores TMS foram transcritos da Tabela A.4 fornecida pelo autor do projeto
na conversa, e são mantidos separados dos resultados executados localmente.
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "new_experiments/final_tables_20261108"

TMS = {
    "80rd400": (398, 20140), "84fl417": (415, 21042),
    "88pr439": (437, 22127), "89pcb442": (440, 22300),
    "99d493": (491, 24854), "115rat575": (568, 28649),
    "115u574": (572, 28935), "131p654": (652, 32991),
    "132d657": (655, 33182), "145u724": (722, 36518),
    "157rat783": (775, 39277), "201pr1002": (1000, 50570),
    "212u1060": (1058, 53523), "217vm1084": (1082, 54708),
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def tex(s: str) -> str:
    return s.replace("_", r"\_").replace("%", r"\%")


def dec(value: float, digits: int = 1) -> str:
    """Número para LaTeX/PT-BR, com separador fino para milhares."""
    value = float(value)
    formatted = f"{value:,.{digits}f}"
    formatted = formatted.replace(",", "X").replace(".", "{,}").replace("X", r"\,")
    return formatted


def integer(value: float) -> str:
    return f"{int(round(float(value))):,}".replace(",", r"\,")


def pct(value: float, digits: int = 3) -> str:
    return dec(value, digits) + r"\%"


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    summary = read_csv("all_blocks_by_instance.csv")
    paired = read_csv("paired_seed_results.csv")
    block_summary = read_csv("block_summary.csv")
    calibration = read_csv("../ils_reset_calibration_20261029_193722/calibration_summary.csv")
    row_end = r"\\"

    # Agrupamento SOPMV grande por percentual obrigatório.
    mv_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in paired:
        if row["block"] == "sopmv_large":
            mv_groups[row["instance"].split("_MV")[-1]].append(row)
    mv_rows = []
    for mv in sorted(mv_groups, key=int):
        rows = mv_groups[mv]
        profiles = len({row["instance"] for row in rows})
        profile_means: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
        for row in rows:
            d = profile_means[row["instance"]]
            d[0] += float(row["ils_objective"])
            d[1] += float(row["vns_objective"])
            d[2] += 1
        pm_ils = pm_vns = pm_tie = 0
        for ils_sum, vns_sum, n in profile_means.values():
            if ils_sum / n > vns_sum / n:
                pm_ils += 1
            elif ils_sum / n < vns_sum / n:
                pm_vns += 1
            else:
                pm_tie += 1
        mv_rows.append({
            "mandatory_percent": mv,
            "profiles": profiles,
            "pairs": len(rows),
            "ils_seed_wins": sum(row["winner"] == "ILS_WIN" for row in rows),
            "seed_ties": sum(row["winner"] == "TIE" for row in rows),
            "vns_seed_wins": sum(row["winner"] == "VNS_WIN" for row in rows),
            "ils_profile_wins": pm_ils,
            "profile_ties": pm_tie,
            "vns_profile_wins": pm_vns,
            "ils_mean_rpd_percent": statistics.mean(float(row["ils_rpd_percent"]) for row in rows),
            "vns_mean_rpd_percent": statistics.mean(float(row["vns_rpd_percent"]) for row in rows),
            "ils_valid_runs": sum(row["ils_valid"].lower() == "true" for row in rows),
            "vns_valid_runs": sum("VALIDO reward=" in row["vns_validation"] for row in rows),
        })
    write_csv("sopmv_large_by_mandatory_percent.csv", mv_rows, list(mv_rows[0]))

    # Comparação externa ILS x TMS para SOP grande T100.
    sop_large = [r for r in summary if r["block"] == "sop_large"]
    lookup = {r["instance"]: r for r in sop_large}
    tms_rows = []
    for family, (tms_p1, tms_p2) in TMS.items():
        for profile, tms_best in (("p1", tms_p1), ("p2", tms_p2)):
            row = lookup[f"{family}_T100_{profile}"]
            ils_best = float(row["ils_best"])
            ils_mean = float(row["ils_mean"])
            tms_rows.append({
                "instance": row["instance"], "family": family, "profit_profile": profile,
                "ils_best": ils_best, "ils_mean": ils_mean,
                "tms_fbest": tms_best,
                "ils_best_gap_percent": 100 * (tms_best - ils_best) / tms_best,
                "ils_mean_gap_percent": 100 * (tms_best - ils_mean) / tms_best,
            })
    write_csv("sop_large_ils_tms_2026_comparison.csv", tms_rows, list(tms_rows[0]))

    # Resumo da validação VNS original/adaptado.
    nonreg_path = ROOT / "new_experiments/vns_nonregression_20261028_204513/results.csv"
    with nonreg_path.open(newline="") as handle:
        nonreg = list(csv.DictReader(handle))
    nonreg_by_solver: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in nonreg:
        nonreg_by_solver[row["solver"]].append(row)
    nonreg_rows = []
    for solver, rows in sorted(nonreg_by_solver.items()):
        nonreg_rows.append({
            "solver": solver,
            "profiles": len({r["instance"] for r in rows}),
            "runs": len(rows),
            "externally_valid": sum("VALIDO reward=" in r["validation"] for r in rows),
        })
    write_csv("vns_nonregression_summary.csv", nonreg_rows, list(nonreg_rows[0]))

    # ----- LaTex -----
    lines: list[str] = [
        "% Gerado por scripts/generate_tcc_result_tables.py.",
        "% Pacotes necessarios: booktabs, longtable, threeparttable, adjustbox.",
        "% As tabelas marcadas como APENDICE nao sao recomendadas para o corpo principal.",
        "",
        "% === CORPO PRINCIPAL: calibração ===",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Calibração preliminar do intervalo de reinício do ILS.}",
        r"\label{tab:ils-calibration}", r"\begin{tabular}{rrrrrr}", r"\toprule",
        r"$N$ & Execuções & Válidas & RPD médio (\%) & Mediana RPD (\%) & Vitórias \\", r"\midrule",
    ]
    for row in calibration:
        lines.append(f"{row['reset_interval']} & {row['runs']} & {row['valid_runs']} & {dec(float(row['mean_rpd_percent']),3)} & {dec(float(row['median_rpd_percent']),3)} & {row['wins']} " + row_end)
    lines += [
        r"\bottomrule", r"\end{tabular}",
        r"\begin{minipage}{0.93\linewidth}\footnotesize",
        r"Foram avaliados $N\in\{10,20,30,40\}$ em 20 execuções por configuração, com cinco sementes e orçamento $\lceil1{,}5N_{set}\rceil$. O menor RPD médio foi obtido por $N=40$, adotado nos experimentos finais.",
        r"\end{minipage}", r"\end{table}", "",
        "% === CORPO PRINCIPAL: validade do baseline ===",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Não regressão do VNS após a adaptação para semente explícita e parada por tempo.}",
        r"\label{tab:vns-nonregression}", r"\begin{tabular}{lrrr}", r"\toprule",
        r"Versão & Perfis & Execuções & Rotas externamente válidas \\", r"\midrule",
    ]
    for row in nonreg_rows:
        name = "VNS original" if row["solver"] == "original" else "VNS adaptado"
        lines.append(f"{name} & {row['profiles']} & {row['runs']} & {row['externally_valid']} " + row_end)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
        "% === CORPO PRINCIPAL: resumo SOP ===",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Resumo da comparação final ILS--VNS adaptado no SOP.}",
        r"\label{tab:ils-vns-sop-summary}", r"\begin{tabular}{lrrrrrrr}", r"\toprule",
        r"Bloco & Perfis & Pares & Vitórias ILS & Empates & Vitórias VNS & RPD ILS (\%) & RPD VNS (\%) \\", r"\midrule"]
    for row in block_summary:
        if row["block"] not in {"sop_small", "sop_large"}:
            continue
        name = "SOP pequeno" if row["block"] == "sop_small" else "SOP grande ($T100$)"
        lines.append(f"{name} & {row['profiles']} & {row['pairs']} & {row['ils_seed_wins']} & {row['seed_ties']} & {row['vns_seed_wins']} & {dec(float(row['ils_mean_rpd_percent']),3)} & {dec(float(row['vns_mean_rpd_percent']),3)} " + row_end)
    lines += [r"\bottomrule", r"\end{tabular}",
        r"\begin{minipage}{0.94\linewidth}\footnotesize",
        r"Cada perfil foi executado 10 vezes por algoritmo, com as mesmas sementes e orçamento $\lceil1{,}5N_{set}\rceil$. Todas as 480 soluções de cada algoritmo foram válidas. No SOP grande, o teste de Wilcoxon bilateral sobre as médias dos 28 perfis resultou em $p=0{,}000215$. ",
        r"\end{minipage}", r"\end{table}", "",
        "% === CORPO PRINCIPAL: ILS versus TMS ===",
        r"\begin{table}[htbp]", r"\centering", r"\scriptsize", r"\caption{Comparação de qualidade entre o ILS e o TMS publicado para as instâncias SOP grandes com $\omega=1{,}0$ ($T100$).}",
        r"\label{tab:ils-tms-sop-large}", r"\begin{adjustbox}{max width=\textwidth}", r"\begin{tabular}{lrrr|rrr}", r"\toprule",
        r"& \multicolumn{3}{c}{Perfil g1 (p1)} & \multicolumn{3}{c}{Perfil g2 (p2)} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
        r"Instância & ILS $f_{best}$ & TMS $f_{best}$ & Dev. (\%) & ILS $f_{best}$ & TMS $f_{best}$ & Dev. (\%) \\", r"\midrule"]
    equal = 0
    best_gaps = []
    for family in TMS:
        p1 = next(r for r in tms_rows if r["family"] == family and r["profit_profile"] == "p1")
        p2 = next(r for r in tms_rows if r["family"] == family and r["profit_profile"] == "p2")
        equal += int(p1["ils_best_gap_percent"] == 0) + int(p2["ils_best_gap_percent"] == 0)
        best_gaps += [p1["ils_best_gap_percent"], p2["ils_best_gap_percent"]]
        lines.append(f"{tex(family)} & {integer(p1['ils_best'])} & {integer(p1['tms_fbest'])} & {dec(p1['ils_best_gap_percent'],3)} & {integer(p2['ils_best'])} & {integer(p2['tms_fbest'])} & {dec(p2['ils_best_gap_percent'],3)} " + row_end)
    lines += [r"\midrule",
        f"\multicolumn{{3}}{{l}}{{Empates ILS--TMS: {equal}/28}} & \multicolumn{{1}}{{r}}{{}} & \multicolumn{{2}}{{l}}{{Desvio médio: {dec(statistics.mean(best_gaps),3)}\%}} & " + row_end,
        r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}",
        r"\begin{minipage}{0.96\linewidth}\footnotesize",
        r"A comparação é exclusivamente de qualidade: $f_{best}$ do ILS resulta de 10 sementes locais; os valores TMS são os publicados na Tabela A.4 do material suplementar. Tempos de CPU não são comparados, pois os ambientes computacionais e os critérios de parada diferem.",
        r"\end{minipage}", r"\end{table}", "",
        "% === CORPO PRINCIPAL: SOPMV ===",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Comparação ILS--VNS adaptado no SOPMV pequeno.}",
        r"\label{tab:ils-vns-sopmv-small-summary}", r"\begin{tabular}{lrrrrrr}", r"\toprule",
        r"Obrigatórios & Perfis viáveis & Pares & Vitórias ILS & Empates & Vitórias VNS & Soluções válidas \\", r"\midrule",
        r"10\% & 18 & 180 & 0 & 180 & 0 & 360 \\",
        r"20\% & 13 & 130 & 0 & 130 & 0 & 260 \\",
        r"30\% & 7 & 70 & 0 & 70 & 0 & 140 \\", r"\midrule",
        r"Total & 38 & 380 & 0 & 380 & 0 & 760 \\", r"\bottomrule", r"\end{tabular}",
        r"\begin{minipage}{0.93\linewidth}\footnotesize",
        r"As 38 instâncias foram selecionadas por possuírem solução viável certificada pelo CPLEX. Todos os empates em recompensa também empataram em distância.",
        r"\end{minipage}", r"\end{table}", "",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Comparação ILS--VNS adaptado no SOPMV grande por percentual de conjuntos obrigatórios.}",
        r"\label{tab:ils-vns-sopmv-large-summary}", r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r"Obrigatórios & Perfis & Pares & ILS/E/V por semente & ILS/E/V por média & RPD ILS (\%) & RPD VNS (\%) & Válidas ILS/VNS \\", r"\midrule"]
    for row in mv_rows:
        lines.append(f"{row['mandatory_percent']}\% & {row['profiles']} & {row['pairs']} & {row['ils_seed_wins']}/{row['seed_ties']}/{row['vns_seed_wins']} & {row['ils_profile_wins']}/{row['profile_ties']}/{row['vns_profile_wins']} & {dec(float(row['ils_mean_rpd_percent']),3)} & {dec(float(row['vns_mean_rpd_percent']),3)} & {row['ils_valid_runs']}/{row['vns_valid_runs']} " + row_end)
    total_ils_w = sum(int(r["ils_seed_wins"]) for r in mv_rows)
    total_tie = sum(int(r["seed_ties"]) for r in mv_rows)
    total_vns_w = sum(int(r["vns_seed_wins"]) for r in mv_rows)
    lines += [r"\midrule", f"Total & 84 & 840 & {total_ils_w}/{total_tie}/{total_vns_w} & 73/6/5 & {dec(statistics.mean(float(r['ils_mean_rpd_percent']) for r in mv_rows),3)} & {dec(statistics.mean(float(r['vns_mean_rpd_percent']) for r in mv_rows),3)} & 840/840 " + row_end,
        r"\bottomrule", r"\end{tabular}",
        r"\begin{minipage}{0.96\linewidth}\footnotesize",
        r"I/E/V denota vitórias do ILS, empates e vitórias do VNS. Todas as soluções do VNS foram aprovadas pelo validador externo; o orçamento foi idêntico por par e definido por $\lceil1{,}5N_{set}\rceil$ segundos.",
        r"\end{minipage}", r"\end{table}", "",
        "% === APENDICE: comparação SOP grande por perfil ===",
        r"\begin{longtable}{llrrrrrrr}", r"\caption{Resultados detalhados de ILS e VNS adaptado no SOP grande ($T100$).}\label{tab:appendix-ils-vns-sop-large}\\",
        r"\toprule", r"Instância & Perfil & $N_{set}$ & $t_{lim}$ & ILS $\bar P$ & ILS DP & ILS melhor & VNS $\bar P$ & I/E/V \\", r"\midrule", r"\endfirsthead",
        r"\toprule", r"Instância & Perfil & $N_{set}$ & $t_{lim}$ & ILS $\bar P$ & ILS DP & ILS melhor & VNS $\bar P$ & I/E/V \\", r"\midrule", r"\endhead",
        r"\bottomrule", r"\endlastfoot"]
    for row in sorted(sop_large, key=lambda x: (int(x["sets_without_depot"]), x["family"], x["profit_profile"])):
        lines.append(f"{tex(row['family'])} & {row['profit_profile'].replace('p','g')} & {row['sets_without_depot']} & {row['time_limit_seconds']} & {dec(float(row['ils_mean']))} & {dec(float(row['ils_std']))} & {integer(row['ils_best'])} & {dec(float(row['vns_mean']))} & {row['ils_seed_wins']}/{row['seed_ties']}/{row['vns_seed_wins']} " + row_end)
    lines += [r"\end{longtable}", ""]

    (OUT / "tcc_results_tables.tex").write_text("\n".join(lines) + "\n")

    inventory = """# Inventário de tabelas para o TCC

## Manter no corpo principal

1. `tab:ils-calibration` — justifica N=40.
2. `tab:vns-nonregression` — valida a adaptação reprodutível do VNS.
3. `tab:ils-vns-sop-summary` — comparação justa ILS x VNS no SOP.
4. `tab:ils-tms-sop-large` — comparação externa de qualidade ILS x TMS.
5. `tab:ils-vns-sopmv-small-summary` — empate nas pequenas e viabilidade.
6. `tab:ils-vns-sopmv-large-summary` — principal resultado SOPMV.

## Mover para o apêndice

- `tab:appendix-ils-vns-sop-large`: detalhamento dos 28 perfis SOP grandes.
- Lista de casos CPLEX sem incumbente/inviáveis: útil para rastreabilidade, não para o texto central.

## Substituir/remover das versões anteriores

- Tabelas de **piloto** SOP grande e SOPMV grande: foram substituídas pelos resultados completos.
- Detalhe SOPMV pequeno: redundante, pois os 380 pares empataram; manter somente se a banca pedir a lista completa.
- Tabela DLX x CPLEX de SCP: não pertence ao escopo SOP/SOPMV deste TCC.

## Tabelas opcionais de validação

- Resumo CPLEX pequeno: manter se o capítulo de validação do MILP for incluído.
- Validação SA-PD pequena: manter apenas se o SA-PD entrar nos resultados finais; caso contrário, citar no texto metodológico.
"""
    (OUT / "tcc_table_inventory.md").write_text(inventory)
    print(f"Gerados: {OUT / 'tcc_results_tables.tex'}")


if __name__ == "__main__":
    main()
