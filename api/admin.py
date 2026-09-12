from __future__ import annotations

import csv
import io
import re
from dataclasses import replace

from api.graph_model import Edge, FoodWeb, Node
from api.normalize import infer_rank, node_id_for
from api.species import node_public

CSV_FIELDS = [
    "id",
    "name",
    "common_name",
    "rank",
    "kingdom",
    "trophic_hint",
    "in_region",
    "photo_url",
    "wikipedia_url",
    "observation_count",
    "eats",
]

EXAMPLE_ROWS = [
    {
        "id": "lynx-canadensis",
        "name": "Lynx canadensis",
        "common_name": "Canada Lynx",
        "rank": "species",
        "kingdom": "Animalia",
        "trophic_hint": "apex / predator",
        "in_region": "true",
        "photo_url": "",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Canada_lynx",
        "observation_count": "0",
        "eats": "Lepus americanus",
    },
    {
        "id": "lepus-americanus",
        "name": "Lepus americanus",
        "common_name": "Snowshoe Hare",
        "rank": "species",
        "kingdom": "Animalia",
        "trophic_hint": "herbivore / prey",
        "in_region": "true",
        "photo_url": "",
        "wikipedia_url": "",
        "observation_count": "0",
        "eats": "Salix, Populus tremuloides",
    },
]


def example_csv() -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(EXAMPLE_ROWS)
    return buf.getvalue()


def export_csv(web: FoodWeb) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for node in sorted(web.nodes.values(), key=lambda n: n.name.lower()):
        eats = [
            web.nodes[e.target].name
            for e in web.neighbors_out(node.id, {"preysOn", "eats", "kills"})
            if e.target in web.nodes
        ]
        writer.writerow(
            {
                "id": node.id,
                "name": node.name,
                "common_name": node.common_name or "",
                "rank": node.rank,
                "kingdom": node.kingdom or "",
                "trophic_hint": node.trophic_hint or "",
                "in_region": "true" if node.in_region else "false",
                "photo_url": node.photo_url or "",
                "wikipedia_url": node.wikipedia_url or "",
                "observation_count": str(node.observation_count),
                "eats": ", ".join(eats),
            }
        )
    return buf.getvalue()


def parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def species_payload(web: FoodWeb, node: Node) -> dict:
    eats = web.neighbors_out(node.id, {"preysOn", "eats", "kills"})
    eaten_by = web.neighbors_in(node.id, {"preysOn", "eats", "kills"})
    return {
        **node_public(node),
        "path": node.path,
        "prey_count": len(eats),
        "predator_count": len(eaten_by),
        "eats": [web.nodes[e.target].name for e in eats if e.target in web.nodes],
    }


def list_species(web: FoodWeb) -> list[dict]:
    rows = [species_payload(web, node) for node in web.nodes.values()]
    rows.sort(key=lambda r: (not r["in_region"], r["name"].lower()))
    return rows


def infer_trophic(web: FoodWeb, node: Node) -> str:
    if node.kingdom == "Plantae":
        return "producer"
    eats = web.neighbors_out(node.id, {"preysOn", "eats", "kills"})
    eaten_by = web.neighbors_in(node.id, {"preysOn", "eats", "kills"})
    if eats and not eaten_by:
        return "apex / predator"
    if eaten_by and not eats:
        return "herbivore / prey"
    if eats and eaten_by:
        return "mid-web"
    return "observed"


def apply_diet(web: FoodWeb, source_id: str, eats: list[str]) -> list[str]:
    skipped: list[str] = []
    web.edges = [e for e in web.edges if not (e.source == source_id and e.type in {"preysOn", "eats", "kills"})]
    for raw in eats:
        hint = raw.strip()
        if not hint:
            continue
        target = resolve_existing(web, hint)
        if not target:
            skipped.append(hint)
            continue
        if target.id == source_id:
            continue
        web.edges.append(Edge(source=source_id, target=target.id, type="eats", n_records=1, sources=["ledger"]))
    return skipped


def resolve_existing(web: FoodWeb, hint: str) -> Node | None:
    key = hint.strip()
    if not key:
        return None
    slug = node_id_for(key)
    if slug in web.nodes:
        return web.nodes[slug]
    if key in web.nodes:
        return web.nodes[key]
    lowered = key.lower()
    matches = [
        n
        for n in web.nodes.values()
        if n.name.lower() == lowered or (n.common_name or "").lower() == lowered
    ]
    return matches[0] if len(matches) == 1 else None


def node_from_fields(data: dict, existing: Node | None = None) -> Node:
    name = (data.get("name") or (existing.name if existing else "")).strip()
    if not name:
        raise ValueError("Scientific name is required")
    node_id = (data.get("id") or (existing.id if existing else "") or node_id_for(name)).strip()
    if not re.match(r"^[a-z0-9-]+$", node_id):
        node_id = node_id_for(name)
    return Node(
        id=node_id,
        name=name,
        common_name=empty_to_none(data.get("common_name", existing.common_name if existing else None)),
        rank=empty_to_none(data.get("rank")) or (existing.rank if existing else infer_rank(name)),
        path=existing.path if existing else empty_to_none(data.get("path")),
        in_region=parse_bool(data.get("in_region"), existing.in_region if existing else False),
        kingdom=empty_to_none(data.get("kingdom", existing.kingdom if existing else None)),
        observation_count=int(data.get("observation_count") or (existing.observation_count if existing else 0)),
        photo_url=empty_to_none(data.get("photo_url", existing.photo_url if existing else None)),
        wikipedia_url=empty_to_none(data.get("wikipedia_url", existing.wikipedia_url if existing else None)),
        external_ids=list(existing.external_ids) if existing else [],
        trophic_hint=empty_to_none(data.get("trophic_hint", existing.trophic_hint if existing else None)),
    )


def split_eats(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in re.split(r"[;,]", str(value)) if part.strip()]


def upsert_species(web: FoodWeb, data: dict, *, create: bool = False) -> tuple[Node, list[str]]:
    name = (data.get("name") or "").strip()
    requested_id = empty_to_none(data.get("id"))
    existing = None
    if requested_id and requested_id in web.nodes:
        existing = web.nodes[requested_id]
    elif name:
        existing = resolve_existing(web, name)
    if create and existing:
        raise ValueError(f"{existing.common_name or existing.name} is already on the ledger")
    node = node_from_fields(data, existing)
    if existing and node.id != existing.id:
        raise ValueError("Species id cannot change; edit the scientific name instead")
    if not existing and node.id in web.nodes:
        raise ValueError(f"Id {node.id} is already taken")
    web.nodes[node.id] = node
    skipped: list[str] = []
    eats_val = data.get("eats", None)
    if eats_val not in (None, ""):
        skipped = apply_diet(web, node.id, split_eats(eats_val))
    if not node.trophic_hint:
        web.nodes[node.id] = replace(node, trophic_hint=infer_trophic(web, node))
        node = web.nodes[node.id]
    return node, skipped


def delete_species(web: FoodWeb, node_id: str) -> Node:
    node = web.nodes.pop(node_id)
    web.edges = [e for e in web.edges if e.source != node_id and e.target != node_id]
    return node


def import_csv(web: FoodWeb, text: str) -> dict:
    sample = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(sample))
    if not reader.fieldnames:
        raise ValueError("CSV needs a header row")
    headers = [h.strip() for h in reader.fieldnames]
    if "name" not in headers:
        raise ValueError("CSV must include a name column (scientific name)")
    created = 0
    updated = 0
    errors: list[str] = []
    skipped_links: list[str] = []
    for i, raw in enumerate(reader, start=2):
        row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
        if not row.get("name"):
            continue
        existed = resolve_existing(web, row.get("id") or "") or resolve_existing(web, row["name"])
        try:
            _, skipped = upsert_species(web, row, create=False)
        except ValueError as exc:
            errors.append(f"Row {i}: {exc}")
            continue
        skipped_links.extend(skipped)
        if existed:
            updated += 1
        else:
            created += 1
    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "skipped_eats": skipped_links,
    }
