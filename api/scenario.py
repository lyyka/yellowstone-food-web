from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field

from api.cascade import CascadeResult
from api.graph_model import FoodWeb, Node
from api.grok import as_paragraphs, grok_chat, grok_key
from api.resolve import ALIASES, resolve_taxon
from api.species import node_public

FRACTION_RE = re.compile(
    r"(?:remove|extinct|wipe|lose|disappear|gone|vanished)?[^\d%]{0,40}(\d{1,3})\s*%",
    re.I,
)
HALF_RE = re.compile(r"\b(half|50 percent|fifty percent)\b", re.I)
HUNTERS_RE = re.compile(r"\b(hunters?|predators?|carnivores?|apex)\b", re.I)
GRAZERS_RE = re.compile(r"\b(grazers?|herbivores?|prey animals|ungulates)\b", re.I)
PLANTS_RE = re.compile(r"\b(plants?|willows?|aspen|producers?)\b", re.I)
ROLEPLAY_RE = re.compile(
    r"\b(everyone|everybody|we all|i|people)\b.+\b(tried|try|became|become|acted|act like|be a|be the)\b",
    re.I,
)


@dataclass
class ScenarioPlan:
    action: str
    fraction: float | None = None
    guild: str | None = None
    names: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class AppliedScenario:
    removed_ids: list[str]
    plan: ScenarioPlan
    focus_ids: list[str] = field(default_factory=list)


def parse_scenario_rules(text: str) -> ScenarioPlan:
    raw = text.strip()
    if m := FRACTION_RE.search(raw):
        pct = min(max(int(m.group(1)), 1), 90)
        return ScenarioPlan(action="remove_fraction", fraction=pct / 100, rationale=f"Remove {pct}% of park mammals.")
    if HALF_RE.search(raw) and re.search(r"\b(species|mammals|animals|web)\b", raw, re.I):
        return ScenarioPlan(action="remove_fraction", fraction=0.5, rationale="Remove half of the park mammals.")
    if HUNTERS_RE.search(raw) and re.search(r"\b(all|every|remove|gone|disappear)\b", raw, re.I):
        return ScenarioPlan(action="remove_guild", guild="hunters", rationale="Remove hunting mammals.")
    if GRAZERS_RE.search(raw) and re.search(r"\b(all|every|remove|gone|disappear)\b", raw, re.I):
        return ScenarioPlan(action="remove_guild", guild="grazers", rationale="Remove grazers and prey mammals.")
    if PLANTS_RE.search(raw) and re.search(r"\b(all|every|remove|gone|disappear)\b", raw, re.I):
        return ScenarioPlan(action="remove_guild", guild="plants", rationale="Remove plant foods from the snapshot.")
    if ROLEPLAY_RE.search(raw) or (
        not re.search(r"\b(remove|extinct|wipe|disappear|gone)\b", raw, re.I)
        and _names_in_text(raw)
    ):
        return ScenarioPlan(
            action="tell",
            names=_names_in_text(raw) or [raw],
            rationale="Answer the question as a story about that animal's life in the park.",
        )
    return ScenarioPlan(
        action="imagine",
        rationale="Paint the visitor's wild what-if as a Yellowstone souvenir story.",
    )


def _names_in_text(text: str) -> list[str]:
    low = text.lower()
    found = []
    for alias in sorted(ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", low):
            found.append(alias)
    return found


def apply_plan(web: FoodWeb, plan: ScenarioPlan, prompt: str) -> AppliedScenario:
    pool = [n for n in web.nodes.values() if n.in_region]
    removed: list[str] = []
    focus: list[str] = []
    if plan.action == "remove_fraction":
        frac = plan.fraction or 0.5
        n = max(1, round(len(pool) * frac))
        n = min(n, max(len(pool) - 1, 1))
        rng = random.Random(hashlib.sha256(prompt.lower().encode()).hexdigest())
        removed = [node.id for node in rng.sample(pool, n)]
    elif plan.action == "remove_guild":
        removed = [node.id for node in pool if _in_guild(node, plan.guild or "")]
        if plan.guild == "plants":
            removed = [nid for nid, node in web.nodes.items() if node.kingdom == "Plantae"]
    elif plan.action == "remove_named":
        for name in plan.names:
            hit = resolve_taxon(web, name)
            if hit:
                removed.append(hit.id)
    elif plan.action in {"tell", "imagine"}:
        for name in plan.names:
            hit = resolve_taxon(web, name)
            if hit:
                focus.append(hit.id)
        if not focus:
            for name in _names_in_text(prompt):
                hit = resolve_taxon(web, name)
                if hit:
                    focus.append(hit.id)
        return AppliedScenario(removed_ids=[], plan=plan, focus_ids=list(dict.fromkeys(focus)))
    removed = list(dict.fromkeys(rid for rid in removed if rid in web.nodes))
    focus = list(dict.fromkeys(focus))
    if not removed:
        raise ValueError("Could not map that prompt onto species in this web.")
    return AppliedScenario(removed_ids=removed, plan=plan, focus_ids=focus)


def _in_guild(node: Node, guild: str) -> bool:
    hint = (node.trophic_hint or "").lower()
    if guild == "hunters":
        return "apex" in hint or "predator" in hint
    if guild == "grazers":
        return "herbivore" in hint or "prey" in hint
    return False


async def interpret_with_grok(web: FoodWeb, prompt: str, fallback: ScenarioPlan) -> ScenarioPlan:
    if fallback.action in {"remove_fraction", "remove_guild"}:
        return fallback
    if not grok_key():
        return fallback
    roster = []
    for node in web.nodes.values():
        if not node.in_region:
            continue
        roster.append(
            f"{node.id} | {node.common_name or node.name} | {node.trophic_hint or 'unknown'}"
        )
    system = (
        "Map a messy visitor question onto one experiment JSON. "
        "Playful questions about real park animals (everyone becomes wolves) are action=tell. "
        "Wild hypotheticals that are not a real extinction — aliens, magic, time travel, "
        "the moon falling into Old Faithful — are action=imagine. names may be empty. "
        "Actual extinctions/removals use remove_named, remove_fraction, or remove_guild. "
        'JSON: {"action":"tell"|"imagine"|"remove_fraction"|"remove_guild"|"remove_named",'
        '"fraction":number|null,"guild":"hunters"|"grazers"|"plants"|null,'
        '"names":[string],"rationale":string}. '
        "When names are used, pick common names from the roster. "
        "Never turn a sci-fi or joke prompt into a species removal."
    )
    text = await grok_chat(
        f"Question: {prompt}\nRoster:\n" + "\n".join(roster[:80]),
        system=system,
        json_mode=True,
        temperature=0.2,
    )
    if not text:
        return fallback
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return fallback
    action = data.get("action") or fallback.action
    if action not in {"remove_fraction", "remove_guild", "remove_named", "tell", "imagine"}:
        return fallback
    if fallback.action == "imagine" and str(action).startswith("remove"):
        return fallback
    return ScenarioPlan(
        action=action,
        fraction=data.get("fraction"),
        guild=data.get("guild"),
        names=list(data.get("names") or fallback.names),
        rationale=data.get("rationale") or fallback.rationale,
    )


def _notes_for_story(web: FoodWeb, result: CascadeResult | None, focus_ids: list[str]) -> str:
    lines = []
    ids = focus_ids or (result.removed_ids if result else [])
    for nid in ids[:4]:
        node = web.nodes.get(nid)
        if not node:
            continue
        eats = [web.nodes[e.target].common_name or web.nodes[e.target].name for e in web.neighbors_out(nid, {"preysOn", "eats", "kills"})][:8]
        eaten = [web.nodes[e.source].common_name or web.nodes[e.source].name for e in web.neighbors_in(nid, {"preysOn", "eats", "kills"})][:6]
        lines.append(
            f"{node.common_name or node.name} usually hunts or browses: {', '.join(eats) or 'nothing listed'}. "
            f"Things that eat them: {', '.join(eaten) or 'almost nobody in this notebook'}."
        )
    if result and result.effects:
        up = [web.nodes[e.node_id].common_name or web.nodes[e.node_id].name for e in result.effects if e.delta_sign > 0][:8]
        down = [web.nodes[e.node_id].common_name or web.nodes[e.node_id].name for e in result.effects if e.delta_sign < 0][:8]
        lines.append(f"If those animals stepped out: easier times for {', '.join(up) or 'nobody obvious'}; tougher times for {', '.join(down) or 'nobody obvious'}.")
    return "\n".join(lines)


async def narrate_scenario(
    prompt: str,
    result: CascadeResult | None,
    web: FoodWeb,
    plan: ScenarioPlan,
    focus_ids: list[str] | None = None,
) -> list[str] | None:
    notes = _notes_for_story(web, result, focus_ids or [])
    if plan.action == "imagine":
        task = (
            "This is a souvenir daydream, not a removal experiment. "
            "Honor their exact premise (yes, even aliens). "
            "Let real Yellowstone animals react in character. "
            "Write 3 short paragraphs separated by blank lines, fun to read aloud, "
            "ending with a wink that this is a postcard, not a park report."
        )
    else:
        task = (
            "Answer them in 3 short paragraphs separated by blank lines. "
            "Lean into their phrasing. Make it fun to read aloud."
        )
    raw = await grok_chat(
        (
            f'The visitor asked, exactly: "{prompt}"\n\n'
            f"What we think they meant: {plan.rationale}\n\n"
            f"Park notebook (optional color, not a cage):\n{notes or 'No cascade this time — just the visitor's premise and the park as a stage.'}\n\n"
            f"{task}"
        ),
        temperature=0.94 if plan.action == "imagine" else 0.92,
    )
    return as_paragraphs(raw) if raw else None


def public_nodes(web: FoodWeb, ids: list[str]) -> list[dict]:
    return [node_public(web.nodes[i]) for i in ids if i in web.nodes]
