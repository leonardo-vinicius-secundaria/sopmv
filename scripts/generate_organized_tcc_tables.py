#!/usr/bin/env python3
"""Gera a versao organizada das tabelas finais do TCC.

O arquivo separa resultados de corpo principal de rastreabilidade de apendice
e usa somente os CSVs consolidados em new_experiments/final_tables_20261108.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "new_experiments" / "final_tables_20261108"
OUT = ROOT / "docs" / "tabelas_resultados_organizadas.tex"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def num(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", "{,}")


def tex(value: str) -> str:
    return value.replace("_", r"\_").replace("%", r"\%")


def detail_table(lines: list[str], title: str, label: str, rows: list[dict[str, str]]) -> None:
    lines += [
        r"\footnotesize",
        rf"\begin{{longtable}}{{llrrrrrr}}",
        rf"\caption{{{title}}}\label{{{label}}}\\",
        r"\toprule",
        r"Inst\^ancia & Perfil & MV & $N_{set}$ & $t_{lim}$ & ILS $\bar P$ & VNS $\bar P$ & I/E/V \\",
        r"\midrule", r"\endfirsthead",
        r"\toprule",
        r"Inst\^ancia & Perfil & MV & $N_{set}$ & $t_{lim}$ & ILS $\bar P$ & VNS $\bar P$ & I/E/V \\",
        r"\midrule", r"\endhead",
        r"\midrule", r"\multicolumn{8}{r}{\footnotesize Continua na pr\'oxima p\'agina.}\\",
        r"\endfoot", r"\bottomrule", r"\endlastfoot",
    ]
    for row in rows:
        lines.append(
            f"{tex(row['instance'])} & {row['profit_profile'].replace('p', 'g')} & "
            f"{row['mandatory_percent']}\\% & {row['sets_without_depot']} & {row['time_limit_seconds']} & "
            f"{num(float(row['ils_mean']), 1)} & {num(float(row['vns_mean']), 1)} & "
            f"{row['ils_seed_wins']}/{row['seed_ties']}/{row['vns_seed_wins']} " + r"\\")
    lines += [r"\end{longtable}", r"\normalsize", ""]


def main() -> None:
    blocks = {row["block"]: row for row in read("block_summary.csv")}
    mandatory = read("sopmv_large_by_mandatory_percent.csv")
    small = read("sopmv_small_by_instance.csv")
    large = read("sopmv_large_by_instance.csv")
    three_way = read("sa_pd_table6_paired_seed_results.csv")

    # SA-PD: agregacao por faixa de N_set, com RPD contra o melhor dos tres.
    ranges = [(80, 99, "80--99"), (100, 145, "115--145"), (146, 217, "157--217")]
    sa_rows = []
    for low, high, name in ranges:
        selected = [r for r in three_way if low <= int(r["sets_without_depot"]) <= high]
        profiles = len({r["instance"] for r in selected})
        wins = {"ILS": 0, "VNS": 0, "SA": 0, "TIE": 0}
        for row in selected:
            values = {"ILS": float(row["ils_objective"]), "VNS": float(row["vns_objective"]), "SA": float(row["sa_pd_objective"])}
            best = max(values.values())
            leaders = [key for key, value in values.items() if value == best]
            wins[leaders[0] if len(leaders) == 1 else "TIE"] += 1
        sa_rows.append((name, profiles, selected, wins))

    lines = [
        "% Gerado por scripts/generate_organized_tcc_tables.py; nao editar manualmente.",
        "% Pacotes: booktabs, longtable, threeparttable, siunitx e adjustbox.",
        "% Corpo principal: tabelas de sintese. Apendice: detalhamento SOPMV.", "",
        "% === CORPO PRINCIPAL: VALIDACAO ===",
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{Panorama da valida\c{c}\~ao do CPLEX branch-and-cut nas inst\^ancias pequenas.}",
        r"\label{tab:cplex-branch-cut-overview}", r"\begin{threeparttable}",
        r"\begin{tabular}{lrrrrr}", r"\toprule",
        r"Conjunto & Casos & \'Otimo & Vi\'avel no limite & Invi\'avel & Sem incumbente \\", r"\midrule",
        r"SOP & 20 & 9 & 11 & 0 & 0 \\",
        r"SOPMV10 & 20 & 10 & 8 & 1 & 1 \\",
        r"SOPMV20 & 20 & 6 & 7 & 6 & 1 \\",
        r"SOPMV30 & 20 & 2 & 5 & 12 & 1 \\", r"\midrule",
        r"Total & 80 & 27 & 31 & 19 & 3 \\", r"\bottomrule", r"\end{tabular}",
        r"\begin{tablenotes}[flushleft]\footnotesize",
        r"\item Limite de \SI{600}{\second}. ``Sem incumbente'' n\~ao prova inviabilidade. A lista dos 22 casos sem solu\c{c}\~ao retornada deve ficar apenas no ap\^endice metodol\'ogico, pois repete esta s\'intese.",
        r"\end{tablenotes}", r"\end{threeparttable}", r"\end{table}", "",
        "% === CORPO PRINCIPAL: SOP ===",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Resumo da compara\c{c}\~ao final ILS--VNS adaptado no SOP.}",
        r"\label{tab:ils-vns-sop-summary}", r"\begin{tabular}{lrrrrrrr}", r"\toprule",
        r"Bloco & Perfis & Pares & Vit. ILS & Empates & Vit. VNS & RPD ILS (\%) & RPD VNS (\%) \\", r"\midrule",
    ]
    for key, title in (("sop_small", "SOP pequeno"), ("sop_large", "SOP grande ($T100$)")):
        row = blocks[key]
        lines.append(f"{title} & {row['profiles']} & {row['pairs']} & {row['ils_seed_wins']} & {row['seed_ties']} & {row['vns_seed_wins']} & {num(float(row['ils_mean_rpd_percent']))} & {num(float(row['vns_mean_rpd_percent']))} " + r"\\")
    lines += [
        r"\bottomrule", r"\end{tabular}",
        r"\begin{minipage}{0.94\linewidth}\footnotesize Cada perfil foi executado 10 vezes por algoritmo, com mesmas sementes e or\c{c}amento $\lceil1{,}5N_{set}\rceil$ segundos. Todas as solu\c{c}\~oes foram aprovadas pelo validador externo.\end{minipage}",
        r"\end{table}", "",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Compara\c{c}\~ao ILS--VNS adaptado--SA--PD no SOP grande ($T100$).}",
        r"\label{tab:ils-vns-sapd-sop-large}", r"\begin{adjustbox}{max width=\textwidth}", r"\begin{tabular}{lrrrrrrr}", r"\toprule",
        r"$N_{set}$ & Perfis & Pares & RPD ILS (\%) & RPD VNS (\%) & RPD SA--PD (\%) & I/V/SA & Empates \\", r"\midrule",
    ]
    for name, profiles, selected, wins in sa_rows:
        lines.append(f"{name} & {profiles} & {len(selected)} & {num(sum(float(r['ils_rpd_percent']) for r in selected)/len(selected))} & {num(sum(float(r['vns_rpd_percent']) for r in selected)/len(selected))} & {num(sum(float(r['sa_pd_rpd_percent']) for r in selected)/len(selected))} & {wins['ILS']}/{wins['VNS']}/{wins['SA']} & {wins['TIE']} " + r"\\")
    total = three_way
    total_wins = defaultdict(int)
    for _, _, _, wins in sa_rows:
        for key, value in wins.items(): total_wins[key] += value
    lines += [
        r"\midrule",
        f"Total & 28 & {len(total)} & {num(sum(float(r['ils_rpd_percent']) for r in total)/len(total))} & {num(sum(float(r['vns_rpd_percent']) for r in total)/len(total))} & {num(sum(float(r['sa_pd_rpd_percent']) for r in total)/len(total))} & {total_wins['ILS']}/{total_wins['VNS']}/{total_wins['SA']} & {total_wins['TIE']} " + r"\\",
        r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}",
        r"\begin{minipage}{0.96\linewidth}\footnotesize RPD calculado por inst\^ancia/semente contra o melhor objetivo entre os tr\^es algoritmos; menor \`e melhor. I/V/SA indica vit\'orias exclusivas. Todas as 840 solu\c{c}\~oes foram v\'alidas.\end{minipage}",
        r"\end{table}", "",
        "% === CORPO PRINCIPAL: SOPMV ===",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Resumo da compara\c{c}\~ao ILS--VNS adaptado no SOPMV pequeno.}",
        r"\label{tab:ils-vns-sopmv-small-summary}", r"\begin{tabular}{lrrrrrr}", r"\toprule",
        r"Obrigat\'orios & Perfis vi\'aveis & Pares & Vit. ILS & Empates & Vit. VNS & Solu\c{c}\~oes v\'alidas \\", r"\midrule",
        r"10\% & 18 & 180 & 0 & 180 & 0 & 360 \\", r"20\% & 13 & 130 & 0 & 130 & 0 & 260 \\", r"30\% & 7 & 70 & 0 & 70 & 0 & 140 \\", r"\midrule",
        r"Total & 38 & 380 & 0 & 380 & 0 & 760 \\", r"\bottomrule", r"\end{tabular}",
        r"\begin{minipage}{0.94\linewidth}\footnotesize O detalhamento por perfil est\'a no Ap\^endice~\ref{tab:appendix-sopmv-small-detail}; os 380 pares tamb\'em empataram em dist\^ancia.\end{minipage}", r"\end{table}", "",
        r"\begin{table}[htbp]", r"\centering", r"\caption{Resumo da compara\c{c}\~ao ILS--VNS adaptado no SOPMV grande.}",
        r"\label{tab:ils-vns-sopmv-large-summary}", r"\begin{adjustbox}{max width=\textwidth}", r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r"Obrigat\'orios & Perfis & Pares & I/E/V por semente & I/E/V por m\'edia & RPD ILS (\%) & RPD VNS (\%) & V\'alidas ILS/VNS \\", r"\midrule",
    ]
    for row in mandatory:
        lines.append(f"{row['mandatory_percent']}\\% & {row['profiles']} & {row['pairs']} & {row['ils_seed_wins']}/{row['seed_ties']}/{row['vns_seed_wins']} & {row['ils_profile_wins']}/{row['profile_ties']}/{row['vns_profile_wins']} & {num(float(row['ils_mean_rpd_percent']))} & {num(float(row['vns_mean_rpd_percent']))} & {row['ils_valid_runs']}/{row['vns_valid_runs']} " + r"\\")
    lines += [
        r"\midrule", r"Total & 84 & 840 & 599/189/52 & 73/6/5 & 0{,}023 & 0{,}475 & 840/840 \\",
        r"\bottomrule", r"\end{tabular}", r"\end{adjustbox}",
        r"\begin{minipage}{0.96\linewidth}\footnotesize I/E/V denota vit\'orias do ILS, empates e vit\'orias do VNS. O detalhamento por perfil est\'a no Ap\^endice~\ref{tab:appendix-sopmv-large-detail}.\end{minipage}", r"\end{table}", "",
        "% === APENDICE: DETALHAMENTO SOPMV ===",
    ]
    sort_key = lambda r: (int(r["mandatory_percent"]), int(r["sets_without_depot"]), r["family"], r["profit_profile"])
    detail_table(lines, "Resultados detalhados de ILS e VNS adaptado no SOPMV pequeno.", "tab:appendix-sopmv-small-detail", sorted(small, key=sort_key))
    detail_table(lines, "Resultados detalhados de ILS e VNS adaptado no SOPMV grande.", "tab:appendix-sopmv-large-detail", sorted(large, key=sort_key))
    lines += [
        "% Tabelas deliberadamente omitidas desta versao:",
        "% - pilotos SOP grande e SOPMV grande: substituidos pelas baterias finais;",
        "% - detalhe SOPMV pequeno do arquivo antigo: agora esta no apendice acima;",
        "% - listagem CPLEX completa e lista de casos sem solucao: rastreabilidade, nao corpo principal.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Gerado: {OUT}")


if __name__ == "__main__":
    main()
