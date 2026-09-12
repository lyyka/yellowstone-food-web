from __future__ import annotations

import re

from api.graph_model import FoodWeb, Node

ALIASES = {
    "wolf": "canis-lupus",
    "wolves": "canis-lupus",
    "gray wolf": "canis-lupus",
    "grey wolf": "canis-lupus",
    "elk": "cervus-canadensis",
    "wapiti": "cervus-canadensis",
    "moose": "alces-alces",
    "bison": "bos-bison",
    "buffalo": "bos-bison",
    "coyote": "canis-latrans",
    "coyotes": "canis-latrans",
    "cougar": "puma-concolor",
    "mountain lion": "puma-concolor",
    "puma": "puma-concolor",
    "bear": "ursus-arctos",
    "grizzly": "ursus-arctos",
    "grizzly bear": "ursus-arctos",
    "black bear": "ursus-americanus",
    "beaver": "castor-canadensis",
    "beavers": "castor-canadensis",
    "aspen": "populus-tremuloides",
    "willow": "salix",
    "willows": "salix",
    "mule deer": "odocoileus-hemionus",
    "deer": "odocoileus-hemionus",
    "lynx": "lynx-canadensis",
    "fox": "vulpes-vulpes",
    "pronghorn": "antilocapra-americana",
}


def resolve_taxon(web: FoodWeb, hint: str) -> Node | None:
    if not hint:
        return None
    key = hint.strip().lower()
    key = re.sub(r"[^a-z0-9\s-]", "", key)
    if key in ALIASES and ALIASES[key] in web.nodes:
        return web.nodes[ALIASES[key]]
    slug = key.replace(" ", "-")
    if slug in web.nodes:
        return web.nodes[slug]
    matches: list[Node] = []
    for node in web.nodes.values():
        names = [node.name.lower(), (node.common_name or "").lower(), node.id]
        if any(key == n or key in n.split() or n.startswith(key) for n in names if n):
            matches.append(node)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return None
    in_region = [m for m in matches if m.in_region]
    pool = in_region or matches
    return max(pool, key=lambda n: n.observation_count)
