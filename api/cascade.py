from __future__ import annotations

from dataclasses import dataclass, field

from api.graph_model import FoodWeb

TROPHIC = {"preysOn", "eats", "kills"}


@dataclass
class Effect:
    node_id: str
    delta_sign: int
    depth: int
    strength: float
    reason_edge_ids: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class CascadeResult:
    removed: str
    effects: list[Effect]
    story: list[str]
    removed_ids: list[str] = field(default_factory=list)


def run_cascade(web: FoodWeb, removed_id: str, max_depth: int = 3) -> CascadeResult:
    result = run_cascade_many(web, [removed_id], max_depth)
    result.removed = removed_id
    return result


def run_cascade_many(web: FoodWeb, removed_ids: list[str], max_depth: int = 3) -> CascadeResult:
    gone = [rid for rid in removed_ids if rid in web.nodes]
    if not gone:
        raise KeyError(removed_ids[0] if removed_ids else "none")
    removed_set = set(gone)
    effects: dict[str, Effect] = {}

    for removed_id in gone:
        for edge in web.neighbors_out(removed_id, TROPHIC):
            if edge.target in removed_set:
                continue
            remaining = web.predator_count(edge.target, excluding=removed_set)
            strength = 1.0 if remaining == 0 else 1.0 / (remaining + 1)
            prey = web.nodes[edge.target]
            prior = effects.get(edge.target)
            if prior is None or strength > prior.strength:
                effects[edge.target] = Effect(
                    node_id=edge.target,
                    delta_sign=1,
                    depth=1,
                    strength=strength,
                    reason_edge_ids=[f"{edge.source}->{edge.target}:{edge.type}"],
                    reason=f"Fewer predators of {prey.common_name or prey.name}",
                )

        for edge in web.neighbors_in(removed_id, TROPHIC):
            if edge.source in removed_set or edge.source in effects:
                continue
            pred = web.nodes[edge.source]
            effects[edge.source] = Effect(
                node_id=edge.source,
                delta_sign=-1,
                depth=1,
                strength=0.6,
                reason_edge_ids=[f"{edge.source}->{edge.target}:{edge.type}"],
                reason=f"Lost {web.nodes[removed_id].common_name or web.nodes[removed_id].name} as food",
            )

    frontier = list(effects.items())
    for node_id, effect in frontier:
        if effect.depth >= max_depth:
            continue
        damping = 0.5 ** effect.depth
        if effect.delta_sign > 0:
            for edge in web.neighbors_out(node_id, TROPHIC):
                if edge.target in removed_set or edge.target in effects:
                    continue
                target = web.nodes[edge.target]
                effects[edge.target] = Effect(
                    node_id=edge.target,
                    delta_sign=-1,
                    depth=effect.depth + 1,
                    strength=effect.strength * damping,
                    reason_edge_ids=[f"{edge.source}->{edge.target}:{edge.type}"],
                    reason=f"More pressure from {web.nodes[node_id].common_name or web.nodes[node_id].name} on {target.common_name or target.name}",
                )
        else:
            for edge in web.neighbors_out(node_id, TROPHIC):
                if edge.target in removed_set or edge.target in effects:
                    continue
                target = web.nodes[edge.target]
                effects[edge.target] = Effect(
                    node_id=edge.target,
                    delta_sign=1,
                    depth=effect.depth + 1,
                    strength=effect.strength * damping,
                    reason_edge_ids=[f"{edge.source}->{edge.target}:{edge.type}"],
                    reason=f"Less pressure from {web.nodes[node_id].common_name or web.nodes[node_id].name} on {target.common_name or target.name}",
                )

    names = [web.nodes[i].common_name or web.nodes[i].name for i in gone]
    story = _story_many(web, names, list(effects.values()))
    ranked = sorted(effects.values(), key=lambda e: (-e.strength, e.depth, e.node_id))
    primary = gone[0]
    return CascadeResult(removed=primary, effects=ranked, story=story, removed_ids=gone)


ICONIC = (
    "cervus-canadensis",
    "odocoileus-hemionus",
    "alces-alces",
    "bos-bison",
    "castor-canadensis",
    "salix",
    "populus-tremuloides",
    "poaceae",
)


def _story(web: FoodWeb, removed, effects: list[Effect]) -> list[str]:
    return _story_many(web, [removed.common_name or removed.name], effects)


def _story_many(web: FoodWeb, names: list[str], effects: list[Effect]) -> list[str]:
    if len(names) == 1:
        label = names[0]
        lead = f"Removing {label} reshapes the documented food web — not a population forecast, just knock-ons on recorded who-eats-whom links."
    else:
        label = ", ".join(names[:6]) + ("…" if len(names) > 6 else "")
        lead = (
            f"Removing {len(names)} species at once ({label}) is a thought experiment on this snapshot. "
            "It is not a real extinction model."
        )
    lines: list[str] = [lead]
    depth1_up = [e for e in effects if e.depth == 1 and e.delta_sign > 0]
    depth1_down = [e for e in effects if e.depth == 1 and e.delta_sign < 0]
    depth2 = [e for e in effects if e.depth == 2]

    if depth1_up:
        labels = [_label(web, e.node_id) for e in _prefer_iconic(depth1_up)[:5]]
        lines.append(
            f"With {label} gone, predation eases on {', '.join(labels)} — they are released from a documented predator."
        )
    if depth1_down:
        labels = [_label(web, e.node_id) for e in depth1_down[:5]]
        lines.append(f"Animals that ate {label} lose a food source: {', '.join(labels)}.")
    if depth2:
        down = [e for e in depth2 if e.delta_sign < 0]
        if down:
            labels = [_label(web, e.node_id) for e in _prefer_iconic(down)[:5]]
            lines.append(
                f"That extra browsing/hunting pressure then hits {', '.join(labels)} — the classic two-hop trophic cascade."
            )
        up = [e for e in depth2 if e.delta_sign > 0]
        if up:
            labels = [_label(web, e.node_id) for e in up[:4]]
            lines.append(f"A dip in mid-web hunters can give {', '.join(labels)} a break.")
    if not depth1_up and not depth1_down:
        lines.append("This snapshot has no trophic edges for that species yet — try another node.")
    return lines


def _prefer_iconic(effects: list[Effect]) -> list[Effect]:
    return sorted(
        effects,
        key=lambda e: (0 if e.node_id in ICONIC else 1, -e.strength, e.depth, e.node_id),
    )


def _label(web: FoodWeb, node_id: str) -> str:
    node = web.nodes[node_id]
    return node.common_name or node.name
