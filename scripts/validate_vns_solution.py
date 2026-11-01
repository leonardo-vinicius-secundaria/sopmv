#!/usr/bin/env python3
"""Valida independentemente o ultimo registro results.log produzido pelo VNS."""
import argparse
import math
import sys


def fields(line):
    return {p.split(":", 1)[0]: p.split(":", 1)[1]
            for p in line.strip().split(";") if ":" in p}


def instance(path):
    coords, clusters, mandatory = {}, {}, set()
    edge, start, end, section, mandatory_column = "", None, None, False, False
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line == "NODE_COORD_SECTION":
                section = "coords"; continue
            if line.startswith("GTSP_SET_SECTION"):
                section = "sets"
                mandatory_column = "mandatory" in line.lower() or "required" in line.lower()
                continue
            if line == "EOF": break
            if section == "coords":
                p = line.split()
                if len(p) >= 3: coords[int(p[0])] = (float(p[1]), float(p[2]))
                continue
            if section == "sets":
                p = line.split()
                if len(p) < 3: continue
                cid, reward = int(p[0]), float(p[1])
                offset = 3 if mandatory_column else 2
                if mandatory_column and int(p[2]): mandatory.add(cid)
                clusters[cid] = (reward, {int(x) for x in p[offset:]})
                continue
            if ":" in line:
                key, value = (x.strip() for x in line.split(":", 1))
                if key == "EDGE_WEIGHT_TYPE": edge = value.upper()
                elif key == "START_SET": start = int(value)
                elif key == "END_SET": end = int(value)
                elif key == "MANDATORY_SETS": mandatory.update(map(int, value.replace(",", " ").split()))
    if start is None: start = 0
    if end is None: end = start
    return coords, clusters, mandatory, edge, start, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--results-log", required=True)
    args = ap.parse_args()
    record = next((x for x in reversed(open(args.results_log, encoding="utf-8").readlines()) if x.strip()), "")
    if not record:
        return fail("results.log vazio")
    r = fields(record)
    try:
        # O VNS registra IDs de vertices em base zero; os arquivos TSPLIB
        # desta colecao usam IDs em base um.
        nodes = [int(x) + 1 for x in r["RESULT_TARGET_IDS"].split(",")]
        route_clusters = [int(x) for x in r["RESULT_CLUSTER_IDS"].split(",")]
        reported_reward, reported_length = float(r["REWARDS"]), float(r["LENGTH"])
        budget = float(r["BUDGET"])
    except (KeyError, ValueError) as e:
        return fail("registro VNS incompleto: " + str(e))
    coords, clusters, mandatory, edge, start, end = instance(args.instance)
    errors = []
    if len(nodes) != len(route_clusters) or len(nodes) < 2: errors.append("rota VNS malformada")
    if route_clusters[0] != start or route_clusters[-1] != end: errors.append("deposito inicial/final incorreto")
    served = set(route_clusters[1:-1])
    missing = mandatory - served
    if missing: errors.append("obrigatorios ausentes: " + ",".join(map(str, sorted(missing))))
    for node, cluster in zip(nodes, route_clusters):
        if cluster not in clusters or node not in clusters[cluster][1]:
            errors.append("representante %s nao pertence ao conjunto %s" % (node, cluster))
    distance = 0.0
    for a, b in zip(nodes, nodes[1:]):
        if a not in coords or b not in coords: errors.append("no ausente nas coordenadas"); break
        d = math.hypot(coords[a][0] - coords[b][0], coords[a][1] - coords[b][1])
        distance += math.ceil(d) if edge == "CEIL_2D" else math.floor(d + .5)
    reward = sum(clusters[c][0] for c in served if c != start and c != end)
    if distance > budget + 1e-9: errors.append("TMAX violado: %.6f > %.6f" % (distance, budget))
    if abs(distance - reported_length) > 1e-6: errors.append("distancia divergente")
    if abs(reward - reported_reward) > 1e-6: errors.append("recompensa divergente")
    if errors: return fail("; ".join(errors))
    print("VALIDO reward=%g distance=%g budget=%g mandatory=%s" %
          (reward, distance, budget, ",".join(map(str, sorted(mandatory)))))


def fail(message):
    print("INVALIDO: " + message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
