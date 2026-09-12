from __future__ import annotations

from dataclasses import dataclass, field

INVERSE_TO_CANONICAL = {
    "preyedUponBy": "preysOn",
    "eatenBy": "eats",
    "killedBy": "kills",
    "hasParasite": "parasiteOf",
    "pollinatedBy": "pollinates",
}

CANONICAL_TYPES = {"preysOn", "eats", "kills", "parasiteOf", "pollinates"}

DROPPED_TAXA = {
    "canis familiaris",
    "homo sapiens",
    "bos taurus",
    "sus scrofa domesticus",
    "felis catus",
}

SYNONYMS = {
    "cervus elaphus": "Cervus canadensis",
    "canis lupus familiaris": "Canis familiaris",
    "alces alces": "Alces alces",
    "odocoileus virginianus": "Odocoileus virginianus",
}


def collapse_to_species(name: str | None) -> str | None:
    if not name:
        return None
    name = name.strip()
    key = name.lower()
    if key in SYNONYMS:
        return SYNONYMS[key]
    parts = name.split()
    if len(parts) >= 3 and parts[0][0].isupper() and parts[1][0].islower():
        if parts[1].lower() == "lupus" and parts[2].lower() == "familiaris":
            return "Canis familiaris"
        return f"{parts[0]} {parts[1]}"
    return name


def should_keep_taxon(name: str | None) -> bool:
    collapsed = collapse_to_species(name)
    if not collapsed:
        return False
    return collapsed.lower() not in DROPPED_TAXA


def node_id_for(name: str, _external_id: str | None = None) -> str:
    collapsed = collapse_to_species(name) or name
    return collapsed.lower().replace(" ", "-")


def canonical_interaction(interaction_type: str) -> tuple[str, bool] | None:
    if interaction_type in INVERSE_TO_CANONICAL:
        return INVERSE_TO_CANONICAL[interaction_type], True
    if interaction_type in CANONICAL_TYPES:
        return interaction_type, False
    return None


def infer_rank(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2 and parts[1][0].islower():
        return "species"
    return "genus"


def infer_kingdom(path: str | None) -> str | None:
    if not path:
        return None
    lower = path.lower()
    if "plantae" in lower or "viridiplantae" in lower or "embryophyta" in lower:
        return "Plantae"
    if "mammalia" in lower:
        return "Animalia"
    if "animalia" in lower or "metazoa" in lower:
        return "Animalia"
    if "fungi" in lower:
        return "Fungi"
    return None


@dataclass
class Node:
    id: str
    name: str
    common_name: str | None = None
    rank: str = "species"
    path: str | None = None
    in_region: bool = False
    kingdom: str | None = None
    observation_count: int = 0
    photo_url: str | None = None
    wikipedia_url: str | None = None
    external_ids: list[str] = field(default_factory=list)
    trophic_hint: str | None = None


@dataclass
class Edge:
    source: str
    target: str
    type: str
    n_records: int = 1
    sources: list[str] = field(default_factory=list)


@dataclass
class FoodWeb:
    nodes: dict[str, Node]
    edges: list[Edge]
    meta: dict = field(default_factory=dict)

    def neighbors_out(self, node_id: str, types: set[str] | None = None) -> list[Edge]:
        return [
            e
            for e in self.edges
            if e.source == node_id and (types is None or e.type in types)
        ]

    def neighbors_in(self, node_id: str, types: set[str] | None = None) -> list[Edge]:
        return [
            e
            for e in self.edges
            if e.target == node_id and (types is None or e.type in types)
        ]

    def predator_count(self, node_id: str, excluding: str | set[str] | None = None) -> int:
        preds = {e.source for e in self.neighbors_in(node_id, {"preysOn", "eats", "kills"})}
        if isinstance(excluding, str):
            preds.discard(excluding)
        elif excluding:
            preds -= set(excluding)
        return len(preds)

    def to_dict(self) -> dict:
        return {
            "meta": self.meta,
            "nodes": [n.__dict__ for n in self.nodes.values()],
            "edges": [e.__dict__ for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FoodWeb":
        nodes = {n["id"]: Node(**{k: v for k, v in n.items() if k in Node.__dataclass_fields__}) for n in data["nodes"]}
        edges = [Edge(**{k: v for k, v in e.items() if k in Edge.__dataclass_fields__}) for e in data["edges"]]
        return cls(nodes=nodes, edges=edges, meta=data.get("meta", {}))
