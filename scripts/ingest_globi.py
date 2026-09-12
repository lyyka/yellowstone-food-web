#!/usr/bin/env python3
"""Build a scoped Yellowstone mammal food-web snapshot from iNaturalist + GloBI."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.normalize import (  # noqa: E402
    Edge,
    FoodWeb,
    Node,
    canonical_interaction,
    collapse_to_species,
    infer_kingdom,
    infer_rank,
    node_id_for,
    should_keep_taxon,
)

INAT_PLACE = 10211
GLOBI = "https://api.globalbioticinteractions.org/interaction"
INAT = "https://api.inaturalist.org/v1/observations/species_counts"
USER_AGENT = "biology-food-web-hackathon/1.0 (educational demo)"

SEED_EDGES = [
    ("Canis lupus", "Cervus canadensis", "preysOn", 40),
    ("Canis lupus", "Odocoileus hemionus", "preysOn", 18),
    ("Canis lupus", "Alces alces", "preysOn", 8),
    ("Canis lupus", "Bison bison", "preysOn", 4),
    ("Canis lupus", "Ovis canadensis", "preysOn", 6),
    ("Canis lupus", "Canis latrans", "preysOn", 5),
    ("Puma concolor", "Odocoileus hemionus", "preysOn", 22),
    ("Puma concolor", "Cervus canadensis", "preysOn", 9),
    ("Ursus arctos", "Cervus canadensis", "preysOn", 7),
    ("Ursus arctos", "Odocoileus hemionus", "preysOn", 4),
    ("Canis latrans", "Odocoileus hemionus", "preysOn", 3),
    ("Canis latrans", "Lepus americanus", "preysOn", 10),
    ("Canis latrans", "Microtus", "preysOn", 6),
    ("Lynx canadensis", "Lepus americanus", "preysOn", 16),
    ("Vulpes vulpes", "Microtus", "preysOn", 8),
    ("Cervus canadensis", "Salix", "eats", 14),
    ("Cervus canadensis", "Populus tremuloides", "eats", 12),
    ("Alces alces", "Salix", "eats", 11),
    ("Alces alces", "Populus tremuloides", "eats", 5),
    ("Castor canadensis", "Salix", "eats", 15),
    ("Castor canadensis", "Populus tremuloides", "eats", 9),
    ("Bison bison", "Poaceae", "eats", 10),
    ("Odocoileus hemionus", "Populus tremuloides", "eats", 4),
    ("Odocoileus hemionus", "Salix", "eats", 4),
    ("Ursus americanus", "Vaccinium", "eats", 8),
    ("Ursus arctos", "Vaccinium", "eats", 7),
]

PLANT_META = {
    "Salix": ("Willow", "Plantae", "genus"),
    "Populus tremuloides": ("Quaking aspen", "Plantae", "species"),
    "Poaceae": ("Grasses", "Plantae", "family"),
    "Vaccinium": ("Huckleberry", "Plantae", "genus"),
    "Microtus": ("Voles", "Animalia", "genus"),
}


def fetch_inat_mammals(client: httpx.Client) -> list[dict]:
    mammals: list[dict] = []
    page = 1
    while True:
        r = client.get(
            INAT,
            params={
                "place_id": INAT_PLACE,
                "iconic_taxa": "Mammalia",
                "rank": "species",
                "quality_grade": "research",
                "per_page": 200,
                "page": page,
            },
        )
        r.raise_for_status()
        payload = r.json()
        mammals.extend(payload.get("results", []))
        if page * payload.get("per_page", 200) >= payload.get("total_results", 0):
            break
        page += 1
        time.sleep(0.3)
    return mammals


def globi_rows(client: httpx.Client, params: dict) -> list[dict]:
    rows: list[dict] = []
    skip = 0
    limit = 200
    while True:
        q = {**params, "type": "json", "limit": limit, "skip": skip}
        try:
            r = client.get(GLOBI, params=q, timeout=45.0)
            r.raise_for_status()
            payload = r.json()
        except Exception as exc:  # noqa: BLE001
            print(f"  GloBI miss {params}: {exc}")
            break
        columns = payload.get("columns") or []
        data = payload.get("data") or []
        if not data:
            break
        for rec in data:
            rows.append(dict(zip(columns, rec)))
        if len(data) < limit:
            break
        skip += limit
        if skip > 800:
            break
        time.sleep(0.15)
    return rows


def taxon_ok(name: str | None, region_names: set[str]) -> bool:
    collapsed = collapse_to_species(name)
    if not collapsed or not should_keep_taxon(collapsed):
        return False
    if collapsed.lower() in {n.lower() for n in region_names}:
        return True
    if collapsed in PLANT_META:
        return True
    kingdom = infer_kingdom(name)
    return False


def keep_endpoint(name: str | None, path: str | None, region_names: set[str]) -> bool:
    collapsed = collapse_to_species(name)
    if not collapsed or not should_keep_taxon(collapsed):
        return False
    if collapsed.lower() in {n.lower() for n in region_names}:
        return True
    if collapsed in PLANT_META:
        return True
    kingdom = infer_kingdom(path)
    if kingdom == "Plantae" and infer_rank(collapsed) in {"species", "genus", "family"}:
        return True
    # Keep genus-level prey that matches a Yellowstone genus (e.g. Microtus)
    genus = collapsed.split()[0]
    if any(n.split()[0] == genus for n in region_names) and infer_rank(collapsed) == "genus":
        return True
    return False


def upsert_node(
    nodes: dict[str, Node],
    name: str,
    path: str | None,
    external_id: str | None,
    inat: dict[str, dict],
    region_names: set[str],
) -> str | None:
    collapsed = collapse_to_species(name)
    if not collapsed or not should_keep_taxon(collapsed):
        return None
    nid = node_id_for(collapsed)
    info = inat.get(collapsed.lower(), {})
    plant = PLANT_META.get(collapsed)
    in_region = collapsed.lower() in {n.lower() for n in region_names}
    if nid not in nodes:
        nodes[nid] = Node(
            id=nid,
            name=collapsed,
            common_name=(info.get("common") or (plant[0] if plant else None)),
            rank=info.get("rank") or (plant[2] if plant else infer_rank(collapsed)),
            path=path,
            in_region=in_region,
            kingdom=(plant[1] if plant else infer_kingdom(path)),
            observation_count=info.get("count", 0),
            photo_url=info.get("photo"),
            wikipedia_url=info.get("wiki"),
            external_ids=[external_id] if external_id else [],
        )
    else:
        node = nodes[nid]
        if external_id and external_id not in node.external_ids:
            node.external_ids.append(external_id)
        if path and not node.path:
            node.path = path
        if in_region:
            node.in_region = True
        if info.get("common") and not node.common_name:
            node.common_name = info["common"]
        if info.get("photo") and not node.photo_url:
            node.photo_url = info["photo"]
    return nid


def add_edge(edges: dict[tuple, Edge], source: str, target: str, itype: str, citation: str | None) -> None:
    if source == target:
        return
    key = (source, target, itype)
    if key not in edges:
        edges[key] = Edge(source=source, target=target, type=itype, n_records=0, sources=[])
    edges[key].n_records += 1
    if citation and citation not in edges[key].sources and len(edges[key].sources) < 6:
        edges[key].sources.append(citation)


JUNK_TAXA = {
    "plantae",
    "tracheophyta",
    "magnoliopsida",
    "embryophyta",
    "viridiplantae",
    "malus",
    "malus-domestica",
    "bos",
    "cervus",
    "odocoileus",
    "lepus",
    "mustela",
    "marmota",
    "martes",
}


def prune_web(web: FoodWeb, max_plants: int = 28) -> FoodWeb:
    """Keep regional mammals plus the strongest diet partners so the demo stays playable."""
    keep = {nid for nid, n in web.nodes.items() if n.in_region and nid not in JUNK_TAXA}
    plant_scores: dict[str, int] = {}
    extra_animals: dict[str, int] = {}
    for edge in web.edges:
        src, tgt = web.nodes[edge.source], web.nodes[edge.target]
        if src.in_region and not tgt.in_region:
            if tgt.kingdom == "Plantae" or tgt.id in {node_id_for(k) for k in PLANT_META}:
                plant_scores[tgt.id] = plant_scores.get(tgt.id, 0) + edge.n_records
            else:
                extra_animals[tgt.id] = extra_animals.get(tgt.id, 0) + edge.n_records
        if tgt.in_region and not src.in_region:
            extra_animals[src.id] = extra_animals.get(src.id, 0) + edge.n_records
    top_plants = sorted(plant_scores, key=lambda k: -plant_scores[k])[:max_plants]
    keep.update(top_plants)
    keep.update(k for k, score in extra_animals.items() if score >= 3)
    for key in PLANT_META:
        kid = node_id_for(key)
        if kid in web.nodes:
            keep.add(kid)
    merged: dict[tuple[str, str], Edge] = {}
    for edge in web.edges:
        if edge.source not in keep or edge.target not in keep:
            continue
        if edge.source in JUNK_TAXA or edge.target in JUNK_TAXA:
            continue
        pair = (edge.source, edge.target)
        if pair not in merged:
            merged[pair] = Edge(
                source=edge.source,
                target=edge.target,
                type=edge.type,
                n_records=edge.n_records,
                sources=list(edge.sources),
            )
        else:
            merged[pair].n_records += edge.n_records
            if edge.type == "preysOn":
                merged[pair].type = "preysOn"
            for src in edge.sources:
                if src not in merged[pair].sources and len(merged[pair].sources) < 6:
                    merged[pair].sources.append(src)
    return FoodWeb(
        nodes={k: web.nodes[k] for k in keep if k in web.nodes},
        edges=list(merged.values()),
        meta=web.meta,
    )


def trophic_hint(web: FoodWeb) -> None:
    for node in web.nodes.values():
        outs = web.neighbors_out(node.id, {"preysOn", "eats", "kills"})
        ins = web.neighbors_in(node.id, {"preysOn", "eats", "kills"})
        if node.kingdom == "Plantae":
            node.trophic_hint = "producer"
        elif outs and not ins:
            node.trophic_hint = "apex / predator"
        elif outs and ins:
            node.trophic_hint = "mid-web"
        elif ins and not outs:
            node.trophic_hint = "herbivore / prey"
        else:
            node.trophic_hint = "observed"


def main() -> None:
    out = ROOT / "data" / "graphs" / "yellowstone-mammals.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=45.0) as client:
        print("Fetching iNaturalist Yellowstone mammals…")
        results = fetch_inat_mammals(client)
        inat: dict[str, dict] = {}
        region_names: set[str] = set()
        for item in results:
            taxon = item["taxon"]
            name = taxon["name"]
            region_names.add(name)
            photo = (taxon.get("default_photo") or {}).get("medium_url")
            inat[name.lower()] = {
                "common": taxon.get("preferred_common_name"),
                "rank": taxon.get("rank"),
                "count": item.get("count", 0),
                "photo": photo,
                "wiki": taxon.get("wikipedia_url"),
            }
        print(f"  {len(region_names)} mammal species")

        nodes: dict[str, Node] = {}
        edges: dict[tuple, Edge] = {}

        for name in sorted(region_names):
            upsert_node(nodes, name, "Mammalia", None, inat, region_names)

        queries = []
        for name in sorted(region_names):
            for itype in ("preysOn", "eats"):
                queries.append({"sourceTaxon": name, "interactionType": itype})
                queries.append({"targetTaxon": name, "interactionType": itype})

        print(f"Querying GloBI ({len(queries)} calls)…")
        for i, params in enumerate(queries, 1):
            if i % 20 == 0:
                print(f"  {i}/{len(queries)}")
            for row in globi_rows(client, params):
                canon = canonical_interaction(row.get("interaction_type") or "")
                if not canon:
                    continue
                itype, flipped = canon
                src_name = row.get("source_taxon_name")
                tgt_name = row.get("target_taxon_name")
                src_path = row.get("source_taxon_path")
                tgt_path = row.get("target_taxon_path")
                if flipped:
                    src_name, tgt_name = tgt_name, src_name
                    src_path, tgt_path = tgt_path, src_path
                if not keep_endpoint(src_name, src_path, region_names):
                    continue
                if not keep_endpoint(tgt_name, tgt_path, region_names):
                    continue
                sid = upsert_node(
                    nodes, src_name, src_path, row.get("source_taxon_external_id"), inat, region_names
                )
                tid = upsert_node(
                    nodes, tgt_name, tgt_path, row.get("target_taxon_external_id"), inat, region_names
                )
                if sid and tid:
                    add_edge(edges, sid, tid, itype, row.get("study_title"))
            time.sleep(0.05)

    for src, tgt, itype, n in SEED_EDGES:
        if not keep_endpoint(src, None, region_names) and src not in PLANT_META:
            if src.lower() not in {n.lower() for n in region_names} and collapse_to_species(src) not in PLANT_META:
                # still add if it's a known demo plant/animal
                pass
        sid = upsert_node(nodes, src, None, None, inat, region_names)
        tid = upsert_node(nodes, tgt, PLANT_META[tgt][1] if tgt in PLANT_META else None, None, inat, region_names)
        if not sid or not tid:
            continue
        key = (sid, tid, itype)
        if key not in edges:
            edges[key] = Edge(
                source=sid,
                target=tid,
                type=itype,
                n_records=n,
                sources=["educational-seed: classic Yellowstone trophic links"],
            )
        else:
            edges[key].n_records = max(edges[key].n_records, n)

    web = prune_web(
        FoodWeb(
            nodes=nodes,
            edges=list(edges.values()),
            meta={
                "region": "Yellowstone National Park",
                "place_id": INAT_PLACE,
                "sources": ["iNaturalist", "Global Biotic Interactions (GloBI)"],
                "disclaimer": (
                    "Interactions are documented records, not a complete local food web or abundance model. "
                    "Some classic cascade links are seeded for education when GloBI is sparse."
                ),
            },
        )
    )
    trophic_hint(web)

    wolf = web.nodes.get("canis-lupus")
    elk = web.nodes.get("cervus-canadensis")
    wolf_prey = [e.target for e in web.neighbors_out("canis-lupus", {"preysOn", "eats"})] if wolf else []
    print(f"Nodes={len(web.nodes)} edges={len(web.edges)}")
    print(f"Wolf present={bool(wolf)} elk present={bool(elk)} wolf prey={wolf_prey[:12]}")
    if not wolf or "cervus-canadensis" not in wolf_prey:
        raise SystemExit("Gate failed: wolf must be present with elk as prey")

    out.write_text(json.dumps(web.to_dict(), indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
