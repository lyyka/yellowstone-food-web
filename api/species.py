from __future__ import annotations

from api.graph_model import FoodWeb, Node

TROPHIC = {"preysOn", "eats", "kills"}


def node_public(node: Node) -> dict:
    return {
        "id": node.id,
        "name": node.name,
        "common_name": node.common_name,
        "rank": node.rank,
        "in_region": node.in_region,
        "kingdom": node.kingdom,
        "trophic_hint": node.trophic_hint,
        "observation_count": node.observation_count,
        "photo_url": node.photo_url,
        "wikipedia_url": node.wikipedia_url,
    }


def _link(node: Node, records: int, relation: str) -> dict:
    return {**node_public(node), "n_records": records, "relation": relation}


def blurb_for(web: FoodWeb, node: Node, eats: list[dict], eaten_by: list[dict]) -> str:
    name = node.common_name or node.name
    if node.kingdom == "Plantae":
        if eaten_by:
            grazers = ", ".join(x["common_name"] or x["name"] for x in eaten_by[:3])
            return f"{name} is a producer. In this snapshot it is eaten by {grazers}."
        return f"{name} is a producer — energy enters the web here, through photosynthesis."
    if eats and eaten_by:
        return (
            f"{name} sits mid-web: it hunts or browses on {len(eats)} recorded foods "
            f"and is itself prey for {len(eaten_by)} predators."
        )
    if eats and not eaten_by:
        foods = ", ".join(x["common_name"] or x["name"] for x in eats[:3])
        return f"{name} is near the top of this snapshot. Documented foods include {foods}."
    if eaten_by:
        return f"{name} is recorded as prey for {len(eaten_by)} hunters in the Yellowstone web."
    return f"{name} is on the park list, but this snapshot has no trophic edges for it yet."


def neighborhood(web: FoodWeb, node_id: str, limit: int = 12) -> dict:
    node = web.nodes[node_id]
    out_edges = sorted(
        web.neighbors_out(node_id, TROPHIC),
        key=lambda e: -e.n_records,
    )[:limit]
    in_edges = sorted(
        web.neighbors_in(node_id, TROPHIC),
        key=lambda e: -e.n_records,
    )[:limit]
    eats = [_link(web.nodes[e.target], e.n_records, e.type) for e in out_edges]
    eaten_by = [_link(web.nodes[e.source], e.n_records, e.type) for e in in_edges]
    graph_nodes = {node_id: node_public(node)}
    graph_edges = []
    for edge in out_edges + in_edges:
        graph_nodes[edge.source] = node_public(web.nodes[edge.source])
        graph_nodes[edge.target] = node_public(web.nodes[edge.target])
        graph_edges.append(
            {
                "source": edge.source,
                "target": edge.target,
                "type": edge.type,
                "n_records": edge.n_records,
            }
        )
    return {
        "species": node_public(node),
        "eats": eats,
        "eaten_by": eaten_by,
        "blurb": blurb_for(web, node, eats, eaten_by),
        "graph": {"nodes": list(graph_nodes.values()), "edges": graph_edges},
    }


def catalog(web: FoodWeb) -> list[dict]:
    rows = []
    for node in web.nodes.values():
        if not node.in_region:
            continue
        eats = web.neighbors_out(node.id, TROPHIC)
        eaten_by = web.neighbors_in(node.id, TROPHIC)
        eat_links = [_link(web.nodes[e.target], e.n_records, e.type) for e in eats]
        pred_links = [_link(web.nodes[e.source], e.n_records, e.type) for e in eaten_by]
        rows.append(
            {
                **node_public(node),
                "prey_count": len(eats),
                "predator_count": len(eaten_by),
                "blurb": blurb_for(web, node, eat_links, pred_links),
            }
        )
    rows.sort(key=lambda r: (-r["observation_count"], r["name"]))
    return rows
