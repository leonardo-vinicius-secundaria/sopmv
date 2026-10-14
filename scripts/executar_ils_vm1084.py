#!/usr/bin/env python3
"""Gera variantes SOPMV da vm1084 e executa ILS, Greedy e CPLEX."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from gerar_instancias_sopmv import converter_arquivo


PERCENTUAIS = (10, 20, 30)


def argumentos() -> argparse.Namespace:
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Gera SOPMV10, SOPMV20 e SOPMV30 para as instancias vm1084 "
            "e executa ILS, Greedy e CPLEX nas originais e nas variantes."
        )
    )
    parser.add_argument(
        "--instancias",
        type=Path,
        default=raiz / "data" / "vm1084",
        help="pasta da família vm1084, com as cinco originais em sop/",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=raiz / "experiments" / "vm1084_comparacao",
        help="pasta do CSV consolidado",
    )
    parser.add_argument("--seed", type=int, default=202601)
    parser.add_argument("--ils-time-limit", type=float, default=10.0)
    parser.add_argument("--ils-iterations", type=int, default=10000)
    parser.add_argument("--ils-perturbation", type=int, default=2)
    parser.add_argument("--cplex-time-limit", type=float, default=60.0)
    parser.add_argument("--cplex-threads", type=int, default=1)
    parser.add_argument("--cplex-mip-gap", type=float, default=0.0)
    parser.add_argument(
        "--cplex-root",
        type=Path,
        help="diretorio CPLEX_Studio; necessario somente para compilar o CPLEX",
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        help="substitui variantes e CSV gerados anteriormente",
    )
    parser.set_defaults(raiz=raiz)
    args = parser.parse_args()

    if args.ils_time_limit < 0:
        parser.error("--ils-time-limit nao pode ser negativo")
    if args.ils_iterations < 0:
        parser.error("--ils-iterations nao pode ser negativo")
    if args.ils_perturbation <= 0:
        parser.error("--ils-perturbation deve ser positivo")
    if args.cplex_time_limit < 0:
        parser.error("--cplex-time-limit nao pode ser negativo")
    if args.cplex_threads <= 0:
        parser.error("--cplex-threads deve ser positivo")
    if args.cplex_mip_gap < 0:
        parser.error("--cplex-mip-gap nao pode ser negativo")
    return args


def gerar_variantes(
    originais: list[Path], pasta: Path, seed: int, sobrescrever: bool
) -> dict[int, list[Path]]:
    destinos = {percentual: pasta / f"sopmv_{percentual}" for percentual in PERCENTUAIS}
    for destino in destinos.values():
        destino.mkdir(parents=True, exist_ok=True)

    variantes = {percentual: [] for percentual in PERCENTUAIS}
    for original in originais:
        geradas = converter_arquivo(original, destinos, seed, sobrescrever)
        for percentual, caminho, obrigatorios in geradas:
            variantes[percentual].append(caminho)
            print(
                f"[GERADA] SOPMV{percentual:02d} {caminho.name}: "
                f"{len(obrigatorios)} conjunto(s) obrigatorio(s)",
                flush=True,
            )
    return variantes


def main() -> int:
    args = argumentos()
    pasta = args.instancias.expanduser().resolve()
    pasta_sop = pasta / "sop"
    saida = args.saida.expanduser().resolve()
    resultado = saida / "resultados.csv"

    if not pasta_sop.is_dir():
        raise RuntimeError(f"pasta de instancias SOP nao encontrada: {pasta_sop}")

    # Os arquivos das subpastas SOPMV nao entram nesta lista.
    originais = sorted(caminho for caminho in pasta_sop.glob("*.sop") if caminho.is_file())
    if len(originais) != 5:
        raise RuntimeError(
            f"esperava 5 instancias .sop em {pasta_sop}, mas encontrei {len(originais)}"
        )

    if resultado.exists() and not args.sobrescrever:
        raise RuntimeError(
            f"o resultado ja existe: {resultado}; use --sobrescrever para refazer a bateria"
        )

    print("Compilando os executaveis do ILS e do Greedy...", flush=True)
    subprocess.run(
        ["make", "build/bin/sopmv_ils", "build/bin/sopmv_greedy"],
        cwd=args.raiz,
        check=True,
    )

    executavel_cplex = args.raiz / "build" / "bin" / "sopmv_cplex"
    if args.cplex_root is not None:
        ambiente = os.environ.copy()
        ambiente["CPLEX_ROOT_DIR"] = str(args.cplex_root.expanduser().resolve())
        print("Compilando o executavel do CPLEX...", flush=True)
        subprocess.run(
            ["make", "build/bin/sopmv_cplex"], cwd=args.raiz, env=ambiente, check=True
        )
    elif not executavel_cplex.is_file():
        raise RuntimeError(
            "build/bin/sopmv_cplex nao foi encontrado; informe --cplex-root /caminho/CPLEX_Studio"
        )

    variantes = gerar_variantes(originais, pasta, args.seed, args.sobrescrever)
    tarefas: list[tuple[str, Path]] = [("SOP", caminho) for caminho in originais]
    for percentual in PERCENTUAIS:
        tarefas.extend(
            (f"SOPMV{percentual}", caminho)
            for caminho in sorted(variantes[percentual])
        )

    saida.mkdir(parents=True, exist_ok=True)
    if resultado.exists():
        resultado.unlink()

    metodos = (
        (
            "ILS",
            [
                str(args.raiz / "build" / "bin" / "sopmv_ils"),
                "--ils-time-limit", str(args.ils_time_limit),
                "--ils-iterations", str(args.ils_iterations),
                "--ils-perturbation", str(args.ils_perturbation),
                "--seed", str(args.seed),
            ],
            {0},
        ),
        ("GREEDY", [str(args.raiz / "build" / "bin" / "sopmv_greedy")], {0}),
        (
            "CPLEX",
            [
                str(executavel_cplex),
                "--time-limit", str(args.cplex_time_limit),
                "--threads", str(args.cplex_threads),
                "--mip-gap", str(args.cplex_mip_gap),
                "--seed", str(args.seed),
                "--log-level", "0",
            ],
            {0, 4},
        ),
    )

    total = len(tarefas) * len(metodos)
    concluidas = 0
    escritor: csv.DictWriter | None = None
    with resultado.open("w", newline="", encoding="utf-8") as arquivo_final:
        with tempfile.TemporaryDirectory(prefix="vm1084_") as temporario:
            csv_temporario = Path(temporario) / "resultado.csv"
            for grupo, instancia in tarefas:
                percentual = "0" if grupo == "SOP" else grupo[len("SOPMV"):]
                for metodo, base, codigos_aceitos in metodos:
                    csv_temporario.unlink(missing_ok=True)
                    comando = base + [
                        "--instance", str(instancia),
                        "--csv", str(csv_temporario),
                    ]
                    processo = subprocess.run(
                        comando,
                        cwd=args.raiz,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    if processo.returncode not in codigos_aceitos:
                        detalhe = processo.stderr.strip() or "sem mensagem de erro"
                        raise RuntimeError(
                            f"{metodo} falhou em {instancia.name} "
                            f"(codigo {processo.returncode}): {detalhe}"
                        )

                    with csv_temporario.open(newline="", encoding="utf-8") as arquivo:
                        linhas = list(csv.DictReader(arquivo))
                    if len(linhas) != 1:
                        raise RuntimeError(
                            f"{metodo} produziu {len(linhas)} linhas para {instancia.name}"
                        )
                    consolidada = {
                        "solver": metodo,
                        "grupo_instancia": grupo,
                        "percentual_solicitado": percentual,
                        "seed": str(args.seed),
                        **linhas[0],
                    }
                    if escritor is None:
                        escritor = csv.DictWriter(
                            arquivo_final, fieldnames=list(consolidada.keys())
                        )
                        escritor.writeheader()
                    escritor.writerow(consolidada)
                    arquivo_final.flush()

                    concluidas += 1
                    print(
                        f"[{concluidas:02d}/{total:02d}] {metodo:6s} "
                        f"{grupo:7s} {instancia.name}",
                        flush=True,
                    )

    print(f"Concluido: {total} execucoes (ILS, Greedy e CPLEX).")
    print(f"CSV consolidado: {resultado}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nExecucao interrompida pelo usuario.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(1)
