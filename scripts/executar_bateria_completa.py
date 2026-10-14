#!/usr/bin/env python3
"""Executa CPLEX, ILS, GREEDY e SA_PD nas quatro familias de instancias."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path


FAMILIAS = (
    ("SOP", 0, "sop"),
    ("SOPMV10", 10, "sopmv_10"),
    ("SOPMV20", 20, "sopmv_20"),
    ("SOPMV30", 30, "sopmv_30"),
)


def argumentos() -> argparse.Namespace:
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Executa os quatro resolvedores e produz somente um CSV consolidado."
    )
    parser.add_argument(
        "--saida", type=Path,
        default=raiz / "experiments" / "berlin52_bateria_completa",
    )
    parser.add_argument("--cplex-time-limit", type=float, default=3600.0)
    parser.add_argument("--ils-time-limit", type=float, default=10.0)
    parser.add_argument(
        "--sa-time-limit",
        type=float,
        help="limite por instancia; se omitido, usa o padrao do SA-PD",
    )
    parser.add_argument("--seed", type=int, default=202601)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--mip-gap", type=float, default=0.0)
    parser.add_argument("--sobrescrever", action="store_true")
    parser.set_defaults(raiz=raiz)
    args = parser.parse_args()

    if args.cplex_time_limit < 0 or args.ils_time_limit < 0:
        parser.error("os limites de tempo nao podem ser negativos")
    if args.sa_time_limit is not None and args.sa_time_limit < 0:
        parser.error("--sa-time-limit nao pode ser negativo")
    if args.threads <= 0:
        parser.error("--threads deve ser positivo")
    if args.mip_gap < 0:
        parser.error("--mip-gap nao pode ser negativo")
    return args


def comandos(args: argparse.Namespace) -> tuple[tuple[str, list[str], set[int]], ...]:
    binario = args.raiz / "build" / "bin"
    cplex = [
        str(binario / "sopmv_cplex"),
        "--time-limit", str(args.cplex_time_limit),
        "--threads", str(args.threads),
        "--mip-gap", str(args.mip_gap),
        "--seed", str(args.seed),
        "--log-level", "0",
    ]
    ils = [
        str(binario / "sopmv_ils"),
        "--ils-time-limit", str(args.ils_time_limit),
        "--seed", str(args.seed),
    ]
    greedy = [str(binario / "sopmv_greedy")]
    sa_pd = [str(binario / "sopmv_sa"), "--seed", str(args.seed)]
    if args.sa_time_limit is not None:
        sa_pd += ["--sa-time-limit", str(args.sa_time_limit)]
    return (
        ("CPLEX", cplex, {0, 4}),  # 4 significa inviabilidade provada.
        ("ILS", ils, {0}),
        ("GREEDY", greedy, {0}),
        ("SA_PD", sa_pd, {0}),
    )


def ler_unica_linha(csv_temporario: Path) -> dict[str, str]:
    with csv_temporario.open(newline="", encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    if len(linhas) != 1:
        raise RuntimeError(
            f"esperava uma linha no CSV temporario, mas encontrei {len(linhas)}"
        )
    return linhas[0]


def main() -> int:
    args = argumentos()
    saida = args.saida.expanduser().resolve()
    resultado = saida / "resultados.csv"

    if resultado.exists() and not args.sobrescrever:
        raise SystemExit(
            f"Erro: {resultado} ja existe. Use --sobrescrever para iniciar uma nova bateria."
        )

    tarefas: list[tuple[str, int, Path]] = []
    for grupo, percentual, nome_pasta in FAMILIAS:
        pasta = args.raiz / "data" / "berlin52" / nome_pasta
        if not pasta.is_dir():
            raise SystemExit(f"Erro: pasta de instancias nao encontrada: {pasta}")
        instancias = sorted(pasta.glob("*.sop"))
        if not instancias:
            raise SystemExit(f"Erro: nenhuma instancia .sop encontrada em {pasta}")
        tarefas.extend((grupo, percentual, caminho) for caminho in instancias)

    metodos = comandos(args)
    ausentes = [comando[0] for _, comando, _ in metodos if not Path(comando[0]).is_file()]
    if ausentes:
        raise SystemExit("Erro: binarios nao encontrados: " + ", ".join(ausentes))

    saida.mkdir(parents=True, exist_ok=True)
    if resultado.exists():
        resultado.unlink()

    total = len(tarefas) * len(metodos)
    concluidas = 0
    escritor: csv.DictWriter[str] | None = None

    with resultado.open("w", newline="", encoding="utf-8") as arquivo_final:
        with tempfile.TemporaryDirectory(prefix="sopmv_bateria_") as temporario:
            csv_temporario = Path(temporario) / "resultado.csv"
            for grupo, percentual, instancia in tarefas:
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

                    linha = ler_unica_linha(csv_temporario)
                    consolidada = {
                        "solver": metodo,
                        "grupo_instancia": grupo,
                        "percentual_solicitado": str(percentual),
                        "seed": str(args.seed),
                        **linha,
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
                        f"[{concluidas:03d}/{total}] {metodo:6s} "
                        f"{grupo:8s} {instancia.name}",
                        flush=True,
                    )

    print(f"Concluido: {total} execucoes.")
    print(f"CSV final: {resultado}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nBateria interrompida pelo usuario.", file=sys.stderr)
        raise SystemExit(130)
    except (OSError, RuntimeError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        raise SystemExit(1)
