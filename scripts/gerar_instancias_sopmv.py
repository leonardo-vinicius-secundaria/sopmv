#!/usr/bin/env python3
"""Converte, em lote, instancias SOP em variantes SOPMV de 10%, 20% e 30%."""

from __future__ import annotations

import argparse
import hashlib
import random
import re
from pathlib import Path


PERCENTUAIS = (10, 20, 30)
PASTAS_PADRAO = {
    10: "sopmv_10",
    20: "sopmv_20",
    30: "sopmv_30",
}


def semente_estavel(semente: int, nome_arquivo: str) -> int:
    """Deriva uma semente por arquivo sem depender do hash aleatorio do Python."""
    resumo = hashlib.sha256(f"{semente}:{nome_arquivo}".encode("utf-8")).digest()
    return int.from_bytes(resumo[:8], "big")


def localizar_conjuntos(linhas: list[str]) -> tuple[int, list[tuple[int, list[str]]]]:
    try:
        secao = next(
            indice
            for indice, linha in enumerate(linhas)
            if linha.strip().upper().startswith("GTSP_SET_SECTION")
        )
    except StopIteration as erro:
        raise ValueError("secao GTSP_SET_SECTION nao encontrada") from erro

    cabecalho = linhas[secao].lower()
    if "mandatory" in cabecalho or "required" in cabecalho:
        raise ValueError("a instancia ja possui uma coluna de obrigatoriedade")

    conjuntos: list[tuple[int, list[str]]] = []
    for indice in range(secao + 1, len(linhas)):
        campos = linhas[indice].split()
        if campos and re.fullmatch(r"[+-]?\d+", campos[0]):
            if len(campos) < 3:
                raise ValueError(f"linha de conjunto invalida: {linhas[indice]!r}")
            conjuntos.append((indice, campos))

    if not conjuntos:
        raise ValueError("nenhum conjunto encontrado em GTSP_SET_SECTION")
    return secao, conjuntos


def arredondar_quantidade(total: int, percentual: int) -> int:
    # floor(total * percentual / 100 + 0.5), sem imprecisao de ponto flutuante.
    return (2 * total * percentual + 100) // 200


def criar_variante(
    linhas: list[str],
    secao: int,
    conjuntos: list[tuple[int, list[str]]],
    obrigatorios: set[int],
    percentual: int,
) -> list[str]:
    variante = list(linhas)
    variante[secao] = "GTSP_SET_SECTION: set_id set_profit mandatory id-vertex-list"

    for indice, linha in enumerate(variante):
        if linha.strip().upper().startswith("NAME:"):
            nome = linha.split(":", 1)[1].strip()
            variante[indice] = f"NAME: {nome}_MV{percentual}"
            break

    for indice, campos in conjuntos:
        id_conjunto = int(campos[0])
        obrigatorio = "1" if id_conjunto in obrigatorios else "0"
        variante[indice] = " ".join(campos[:2] + [obrigatorio] + campos[2:])

    return variante


def converter_arquivo(
    origem: Path,
    destinos: dict[int, Path],
    semente: int,
    sobrescrever: bool,
) -> list[tuple[int, Path, list[int]]]:
    linhas = origem.read_text(encoding="utf-8").splitlines()
    secao, conjuntos = localizar_conjuntos(linhas)

    # Lucro zero identifica o deposito; somente conjuntos lucrativos sao elegiveis.
    elegiveis = sorted(int(campos[0]) for _, campos in conjuntos if float(campos[1]) > 0)
    if not elegiveis:
        raise ValueError("a instancia nao possui conjuntos lucrativos elegiveis")

    random.Random(semente_estavel(semente, origem.name)).shuffle(elegiveis)
    gerados: list[tuple[int, Path, list[int]]] = []

    for percentual in PERCENTUAIS:
        quantidade = arredondar_quantidade(len(elegiveis), percentual)
        selecionados = set(elegiveis[:quantidade])
        destino = destinos[percentual] / origem.name
        if destino.exists() and not sobrescrever:
            raise FileExistsError(
                f"{destino} ja existe; use --sobrescrever para substitui-lo"
            )
        variante = criar_variante(linhas, secao, conjuntos, selecionados, percentual)
        destino.write_text("\n".join(variante) + "\n", encoding="utf-8")
        gerados.append((percentual, destino, sorted(selecionados)))

    return gerados


def main() -> int:
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Gera variantes SOPMV com 10%%, 20%% e 30%% de conjuntos obrigatorios."
    )
    parser.add_argument(
        "--origem",
        type=Path,
        default=raiz / "data" / "berlin52" / "sop",
        help="pasta com os arquivos .sop originais",
    )
    parser.add_argument(
        "--raiz-saida",
        type=Path,
        default=raiz / "data" / "berlin52",
        help="pasta que contem as tres pastas de destino",
    )
    parser.add_argument("--semente", type=int, default=202601)
    parser.add_argument("--sobrescrever", action="store_true")
    args = parser.parse_args()

    origem = args.origem.expanduser().resolve()
    raiz_saida = args.raiz_saida.expanduser().resolve()
    if not origem.is_dir():
        parser.error(f"pasta de origem inexistente: {origem}")

    arquivos = sorted(origem.glob("*.sop"))
    if not arquivos:
        parser.error(f"nenhum arquivo .sop encontrado em {origem}")

    destinos = {
        percentual: raiz_saida / PASTAS_PADRAO[percentual]
        for percentual in PERCENTUAIS
    }
    for pasta in destinos.values():
        pasta.mkdir(parents=True, exist_ok=True)

    total = 0
    for arquivo in arquivos:
        try:
            gerados = converter_arquivo(
                arquivo, destinos, args.semente, args.sobrescrever
            )
        except (OSError, ValueError) as erro:
            parser.error(f"falha em {arquivo}: {erro}")
        for percentual, destino, selecionados in gerados:
            print(
                f"[{percentual:2d}%] {destino.name}: "
                f"{len(selecionados)} obrigatorio(s) {selecionados}"
            )
            total += 1

    print(f"Concluido: {total} instancias geradas a partir de {len(arquivos)} arquivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
