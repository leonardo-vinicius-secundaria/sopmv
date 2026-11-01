#!/usr/bin/env python3
"""Converte, em lote, instancias SOP em variantes SOPMV de 10%, 20% e 30%."""

from __future__ import annotations

import argparse
import hashlib
import math
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


def valor_cabecalho(linhas: list[str], chave: str) -> str:
    prefixo = f"{chave.upper()}:"
    for linha in linhas:
        if linha.strip().upper().startswith(prefixo):
            return linha.split(":", 1)[1].strip()
    raise ValueError(f"cabecalho {chave}: nao encontrado")


def rota_obrigatoria_gulosa(
    linhas: list[str], conjuntos: list[tuple[int, list[str]]], obrigatorios: set[int]
) -> float:
    """Constroi uma rota testemunha deposito-obrigatorios-deposito.

    Retorna o comprimento da rota. Se ele for <= TMAX, a instancia SOPMV e
    certamente viavel. O procedimento e apenas um certificado construtivo:
    uma rota acima de TMAX nao prova inviabilidade, devendo causar novo sorteio.
    """
    tmax = float(valor_cabecalho(linhas, "TMAX"))
    edge_type = valor_cabecalho(linhas, "EDGE_WEIGHT_TYPE").upper()
    try:
        inicio = next(i for i, linha in enumerate(linhas) if linha.strip().upper() == "NODE_COORD_SECTION")
    except StopIteration as erro:
        raise ValueError("NODE_COORD_SECTION nao encontrada") from erro
    coordenadas: dict[int, tuple[float, float]] = {}
    for linha in linhas[inicio + 1 :]:
        campos = linha.split()
        if not campos or linha.strip().upper().startswith("GTSP_SET_SECTION"):
            break
        if len(campos) >= 3 and re.fullmatch(r"[+-]?\d+", campos[0]):
            coordenadas[int(campos[0])] = (float(campos[1]), float(campos[2]))

    por_conjunto = {int(campos[0]): [int(no) for no in campos[2:]] for _, campos in conjuntos}
    deposito = next((cid for cid, nos in por_conjunto.items() if len(nos) and float(next(c[1] for _, c in conjuntos if int(c[0]) == cid)) == 0), None)
    if deposito is None or not por_conjunto[deposito]:
        raise ValueError("conjunto do deposito nao encontrado")
    depot_node = por_conjunto[deposito][0]

    def distancia(a: int, b: int) -> int:
        xa, ya = coordenadas[a]
        xb, yb = coordenadas[b]
        valor = math.hypot(xa - xb, ya - yb)
        if edge_type == "CEIL_2D":
            return math.ceil(valor)
        if edge_type == "EUC_2D":
            return math.floor(valor + 0.5)
        raise ValueError(f"EDGE_WEIGHT_TYPE nao suportado: {edge_type}")

    rota = [depot_node, depot_node]
    pendentes = set(obrigatorios)
    while pendentes:
        melhor: tuple[int, int, int, int] | None = None  # aumento, conjunto, no, posicao
        for conjunto in pendentes:
            for no in por_conjunto[conjunto]:
                for posicao in range(len(rota) - 1):
                    aumento = (
                        distancia(rota[posicao], no)
                        + distancia(no, rota[posicao + 1])
                        - distancia(rota[posicao], rota[posicao + 1])
                    )
                    candidato = (aumento, conjunto, no, posicao)
                    if melhor is None or candidato < melhor:
                        melhor = candidato
        assert melhor is not None
        _, conjunto, no, posicao = melhor
        rota.insert(posicao + 1, no)
        pendentes.remove(conjunto)
    return float(sum(distancia(a, b) for a, b in zip(rota, rota[1:])))


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
    somente_viaveis: bool = False,
    tentativas_maximas: int = 1000,
) -> list[tuple[int, Path, list[int]]]:
    linhas = origem.read_text(encoding="utf-8").splitlines()
    secao, conjuntos = localizar_conjuntos(linhas)

    # Lucro zero identifica o deposito; somente conjuntos lucrativos sao elegiveis.
    elegiveis = sorted(int(campos[0]) for _, campos in conjuntos if float(campos[1]) > 0)
    if not elegiveis:
        raise ValueError("a instancia nao possui conjuntos lucrativos elegiveis")

    gerados: list[tuple[int, Path, list[int]]] = []

    for percentual in PERCENTUAIS:
        quantidade = arredondar_quantidade(len(elegiveis), percentual)
        selecionados: set[int] | None = None
        for tentativa in range(tentativas_maximas):
            candidatos = list(elegiveis)
            nome_semente = origem.name if tentativa == 0 else f"{origem.name}:{percentual}:{tentativa}"
            random.Random(semente_estavel(semente, nome_semente)).shuffle(candidatos)
            proposta = set(candidatos[:quantidade])
            if not somente_viaveis or rota_obrigatoria_gulosa(linhas, conjuntos, proposta) <= float(valor_cabecalho(linhas, "TMAX")):
                selecionados = proposta
                break
        if selecionados is None:
            raise ValueError(
                f"nao foi possivel construir SOPMV{percentual} viavel apos {tentativas_maximas} sorteios"
            )
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
    parser.add_argument(
        "--pastas-saida",
        nargs=3,
        metavar=("PASTA_10", "PASTA_20", "PASTA_30"),
        default=[PASTAS_PADRAO[percentual] for percentual in PERCENTUAIS],
        help=(
            "nomes das pastas para 10%%, 20%% e 30%%, respectivamente "
            f"(padrao: {' '.join(PASTAS_PADRAO[percentual] for percentual in PERCENTUAIS)})"
        ),
    )
    parser.add_argument("--semente", type=int, default=202601)
    parser.add_argument("--sobrescrever", action="store_true")
    parser.add_argument(
        "--somente-viaveis",
        action="store_true",
        help=(
            "reamostra obrigatorios ate encontrar uma rota testemunha gulosa dentro de TMAX; "
            "desligado por padrao para reproduzir o sorteio aleatorio do artigo de 2024"
        ),
    )
    parser.add_argument("--tentativas-maximas", type=int, default=1000)
    args = parser.parse_args()

    origem = args.origem.expanduser().resolve()
    raiz_saida = args.raiz_saida.expanduser().resolve()
    if not origem.is_dir():
        parser.error(f"pasta de origem inexistente: {origem}")
    if args.tentativas_maximas <= 0:
        parser.error("--tentativas-maximas deve ser positivo")

    arquivos = sorted(origem.glob("*.sop"))
    if not arquivos:
        parser.error(f"nenhum arquivo .sop encontrado em {origem}")

    destinos = {
        percentual: raiz_saida / nome_pasta
        for percentual, nome_pasta in zip(PERCENTUAIS, args.pastas_saida)
    }
    for pasta in destinos.values():
        pasta.mkdir(parents=True, exist_ok=True)

    total = 0
    for arquivo in arquivos:
        try:
            gerados = converter_arquivo(
                arquivo,
                destinos,
                args.semente,
                args.sobrescrever,
                args.somente_viaveis,
                args.tentativas_maximas,
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
