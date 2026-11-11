#!/usr/bin/env python3
"""Gera, isoladamente, substitutos SOPMV pequenos com rota obrigatoria viavel.

Os arquivos existentes em ``data/`` nunca sao lidos como destino nem alterados.
Cada instancia abaixo e reamostrada ate que uma rota gulosa deposito--obrigatorios
--deposito respeite TMAX. Essa rota e um certificado construtivo de viabilidade.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_instancias_sopmv as generator  # reutiliza parser e metricas do projeto


TARGETS = (
    "11berlin52_T40_p1_MV30", "11berlin52_T40_p2_MV30",
    "11berlin52_T60_p1_MV20", "11berlin52_T60_p1_MV30",
    "11eil51_T40_p1_MV20", "11eil51_T40_p1_MV30",
    "11eil51_T40_p2_MV30", "11eil51_T60_p1_MV30",
    "11eil51_T60_p2_MV30", "14st70_T40_p1_MV20",
    "14st70_T40_p1_MV30", "14st70_T40_p2_MV20",
    "14st70_T40_p2_MV30", "16eil76_T40_p1_MV10",
    "16eil76_T40_p1_MV20", "16eil76_T40_p1_MV30",
    "16eil76_T40_p2_MV20", "16eil76_T40_p2_MV30",
    "16eil76_T60_p2_MV30", "11berlin52_T40_p2_MV20",
    "14st70_T80_p2_MV30", "16eil76_T40_p2_MV10",
)


def parse_target(target: str) -> tuple[str, int]:
    base, marker, ratio = target.rpartition("_MV")
    if not marker or not base or ratio not in {"10", "20", "30"}:
        raise ValueError(f"alvo invalido: {target}")
    return base, int(ratio)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--max-attempts", type=int, default=10_000)
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "new_experiments" / "sopmv_feasible_replacements_20261110",
        help="novo diretorio isolado; deve nao existir",
    )
    args = parser.parse_args()
    if args.max_attempts <= 0:
        parser.error("--max-attempts deve ser positivo")

    output = args.output.resolve()
    if output.exists():
        parser.error(f"destino ja existe: {output}; escolha outro --output")
    instances_dir = output / "instances"
    instances_dir.mkdir(parents=True)
    manifest_rows: list[dict[str, object]] = []

    for target in TARGETS:
        base, ratio = parse_target(target)
        source = root / "data" / "instancias_pequenas" / "sop" / f"{base}.sop"
        if not source.is_file():
            raise FileNotFoundError(f"instancia SOP de origem ausente: {source}")
        lines = source.read_text(encoding="utf-8").splitlines()
        section, sets = generator.localizar_conjuntos(lines)
        eligible = sorted(int(fields[0]) for _, fields in sets if float(fields[1]) > 0)
        quantity = generator.arredondar_quantidade(len(eligible), ratio)
        tmax = float(generator.valor_cabecalho(lines, "TMAX"))

        selected = None
        witness = None
        for attempt in range(args.max_attempts):
            shuffled = list(eligible)
            token = f"{target}:replacement:{attempt}"
            generator.random.Random(generator.semente_estavel(args.seed, token)).shuffle(shuffled)
            proposal = set(shuffled[:quantity])
            length = generator.rota_obrigatoria_gulosa(lines, sets, proposal)
            if length <= tmax:
                selected, witness = proposal, length
                break
        if selected is None:
            raise RuntimeError(f"{target}: nenhuma rota-testemunha em {args.max_attempts} tentativas")

        destination = instances_dir / f"{target}.sop"
        variant = generator.criar_variante(lines, section, sets, selected, ratio)
        destination.write_text("\n".join(variant) + "\n", encoding="utf-8")
        manifest_rows.append({
            "replacement_instance": target,
            "source_instance": source.relative_to(root).as_posix(),
            "mandatory_percent": ratio,
            "mandatory_sets": ";".join(map(str, sorted(selected))),
            "tmax": tmax,
            "greedy_witness_distance": witness,
            "attempt": attempt + 1,
            "seed": args.seed,
            "instance_path": destination.relative_to(output).as_posix(),
        })

    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    (output / "README.txt").write_text(
        "Substitutos isolados das 22 instancias SOPMV pequenas problematicas.\n"
        "Cada arquivo possui uma rota-testemunha gulosa que atende todos os obrigatorios\n"
        "dentro de TMAX; detalhes reprodutiveis em manifest.csv.\n",
        encoding="utf-8",
    )
    print(f"Geradas {len(manifest_rows)} instancias em {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
