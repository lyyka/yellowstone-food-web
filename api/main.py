from __future__ import annotations

import asyncio

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from api import admin as ledger
from api.cascade import run_cascade, run_cascade_many
from api.explain import enrich_story
from api.graph_model import FoodWeb
from api.nl import parse_query
from api.resolve import resolve_taxon
from api.scenario import apply_plan, interpret_with_grok, narrate_scenario, parse_scenario_rules, public_nodes
from api.species import catalog, neighborhood, node_public
from api.store import get_web, persist_web
from api.postcard import plan_postcard, render_postcard

app = FastAPI(title="Yellowstone What-If Food Web", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RemoveBody(BaseModel):
    id: str | None = None
    name: str | None = None


class QueryBody(BaseModel):
    text: str


class ScenarioBody(BaseModel):
    text: str


class SpeciesBody(BaseModel):
    id: str | None = None
    name: str
    common_name: str | None = None
    rank: str | None = None
    kingdom: str | None = None
    trophic_hint: str | None = None
    in_region: bool = False
    photo_url: str | None = None
    wikipedia_url: str | None = None
    observation_count: int = 0
    path: str | None = None
    eats: list[str] | None = None


def load_web() -> FoodWeb:
    return get_web()


@app.get("/health")
def health() -> dict:
    web = load_web()
    return {"ok": True, "nodes": len(web.nodes), "edges": len(web.edges)}


@app.get("/graph")
def get_graph() -> dict:
    web = load_web()
    payload = web.to_dict()
    payload["presets"] = [
        {
            "id": "yellowstone-mammals",
            "label": "Yellowstone mammals",
            "hook": "Remove wolves and watch elk, then willow, light up.",
        }
    ]
    return payload


@app.get("/species")
def list_species() -> dict:
    web = load_web()
    return {
        "region": web.meta.get("region", "Yellowstone National Park"),
        "disclaimer": web.meta.get("disclaimer", ""),
        "species": catalog(web),
    }


@app.get("/species/{species_id}")
def get_species(species_id: str) -> dict:
    web = load_web()
    if species_id not in web.nodes:
        node = resolve_taxon(web, species_id.replace("-", " "))
        if not node:
            raise HTTPException(404, "Species not in this food web")
        species_id = node.id
    return neighborhood(web, species_id)


@app.get("/search")
def search(q: str) -> dict:
    web = load_web()
    node = resolve_taxon(web, q)
    hits = []
    needle = q.lower()
    for n in web.nodes.values():
        blob = f"{n.name} {n.common_name or ''} {n.id}".lower()
        if needle in blob:
            hits.append(_node_public(n))
        if len(hits) >= 12:
            break
    return {"resolved": _node_public(node) if node else None, "hits": hits}


@app.post("/remove")
async def remove_species(body: RemoveBody) -> dict:
    web = load_web()
    node = None
    if body.id and body.id in web.nodes:
        node = web.nodes[body.id]
    elif body.name:
        node = resolve_taxon(web, body.name)
    if not node:
        raise HTTPException(404, "Species not in this food web")
    result = run_cascade(web, node.id)
    narrative = await enrich_story(web, result, f"remove {node.common_name or node.name}")
    return _cascade_payload(web, node.id, result, narrative)


@app.post("/query")
async def natural_query(body: QueryBody) -> dict:
    web = load_web()
    parsed = parse_query(body.text)
    node = resolve_taxon(web, parsed.taxon_hint)
    if not node:
        raise HTTPException(404, f"Could not match “{parsed.taxon_hint}” to a species in this web")

    if parsed.intent == "remove":
        result = run_cascade(web, node.id)
        narrative = await enrich_story(web, result, body.text)
        return {
            "intent": parsed.intent,
            "focus": _node_public(node),
            **_cascade_payload(web, node.id, result, narrative),
        }

    if parsed.intent == "predators_of":
        edges = web.neighbors_in(node.id, {"preysOn", "eats", "kills"})
        return {
            "intent": parsed.intent,
            "focus": _node_public(node),
            "story": [
                f"{node.common_name or node.name} is eaten by "
                + (_join(web, [e.source for e in edges]) or "no documented predators in this snapshot")
                + "."
            ],
            "highlight_node_ids": [node.id] + [e.source for e in edges],
            "highlight_edge_keys": [f"{e.source}->{e.target}" for e in edges],
            "effects": [],
        }

    if parsed.intent == "prey_of":
        edges = web.neighbors_out(node.id, {"preysOn", "eats", "kills"})
        return {
            "intent": parsed.intent,
            "focus": _node_public(node),
            "story": [
                f"{node.common_name or node.name} eats "
                + (_join(web, [e.target for e in edges]) or "nothing recorded here yet")
                + "."
            ],
            "highlight_node_ids": [node.id] + [e.target for e in edges],
            "highlight_edge_keys": [f"{e.source}->{e.target}" for e in edges],
            "effects": [],
        }

    return {
        "intent": "find",
        "focus": _node_public(node),
        "story": [
            f"{node.common_name or node.name} ({node.name}) — {node.trophic_hint or 'park species'}. "
            "Click Remove to run a what-if cascade."
        ],
        "highlight_node_ids": [node.id],
        "highlight_edge_keys": [],
        "effects": [],
    }


@app.post("/scenario")
async def run_scenario(body: ScenarioBody) -> dict:
    web = load_web()
    prompt = body.text.strip()
    if not prompt:
        raise HTTPException(400, "Ask a what-if question first.")
    rules = parse_scenario_rules(prompt)
    plan = await interpret_with_grok(web, prompt, rules)
    try:
        applied = apply_plan(web, plan, prompt)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    result = None
    if applied.removed_ids:
        result = run_cascade_many(web, applied.removed_ids)
    up = [e for e in (result.effects if result else []) if e.delta_sign > 0][:12]
    down = [e for e in (result.effects if result else []) if e.delta_sign < 0][:12]
    removed_pub = public_nodes(web, result.removed_ids if result else applied.focus_ids)
    released_pub = [
        {**public_nodes(web, [e.node_id])[0], "reason": e.reason, "strength": e.strength}
        for e in up
        if e.node_id in web.nodes
    ]
    pressured_pub = [
        {**public_nodes(web, [e.node_id])[0], "reason": e.reason, "strength": e.strength}
        for e in down
        if e.node_id in web.nodes
    ]
    focus_pub = public_nodes(web, applied.focus_ids or applied.removed_ids)
    card = plan_postcard(
        prompt,
        {"action": plan.action, "fraction": plan.fraction, "guild": plan.guild},
        removed_pub,
        released_pub,
        pressured_pub,
        focus_pub,
    )
    grok, postcard = await asyncio.gather(
        narrate_scenario(
            prompt,
            result,
            web,
            plan,
            focus_ids=applied.focus_ids or applied.removed_ids,
        ),
        render_postcard(card),
    )
    fallback_story = (
        result.story
        if result
        else [
            "The park will try on whatever you just asked — aliens, vanished hunters, a valley of wolves — "
            "and send you home with a postcard of how it felt."
        ]
    )
    imagined = plan.action in {"tell", "imagine"}
    return {
        "prompt": prompt,
        "plan": {
            "action": plan.action,
            "fraction": plan.fraction,
            "guild": plan.guild,
            "rationale": plan.rationale or applied.plan.rationale,
        },
        "removed": removed_pub,
        "released": released_pub,
        "pressured": pressured_pub,
        "story": grok or fallback_story,
        "template_story": result.story if result else fallback_story,
        "llm": bool(grok),
        "postcard": postcard,
        "lesson": {
            "title": "A souvenir what-if" if imagined else "A custom what-if",
            "blurb": (
                "Wild premises get a story and a postcard. When you actually vanish a species, "
                "we still run it through the park's dinner table first."
            ),
        },
    }


@app.get("/admin/species")
def admin_list_species() -> dict:
    web = get_web()
    return {"species": ledger.list_species(web), "count": len(web.nodes)}


@app.get("/admin/species/template.csv")
def admin_template_csv() -> PlainTextResponse:
    return PlainTextResponse(
        ledger.example_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="species-ledger-example.csv"'},
    )


@app.get("/admin/species/export.csv")
def admin_export_csv() -> PlainTextResponse:
    return PlainTextResponse(
        ledger.export_csv(get_web()),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="species-ledger.csv"'},
    )


@app.post("/admin/species/import")
async def admin_import_csv(file: UploadFile = File(...)) -> dict:
    raw = (await file.read()).decode("utf-8-sig")
    try:
        report = ledger.import_csv(get_web(), raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    persist_web()
    return report


@app.post("/admin/species")
def admin_create_species(body: SpeciesBody) -> dict:
    web = get_web()
    try:
        node, skipped = ledger.upsert_species(web, body.model_dump(), create=True)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    persist_web()
    return {**ledger.species_payload(web, node), "skipped_eats": skipped}


@app.get("/admin/species/{species_id}")
def admin_get_species(species_id: str) -> dict:
    web = get_web()
    if species_id not in web.nodes:
        raise HTTPException(404, "Species not on the ledger")
    return ledger.species_payload(web, web.nodes[species_id])


@app.put("/admin/species/{species_id}")
def admin_update_species(species_id: str, body: SpeciesBody) -> dict:
    web = get_web()
    if species_id not in web.nodes:
        raise HTTPException(404, "Species not on the ledger")
    payload = body.model_dump()
    payload["id"] = species_id
    try:
        node, skipped = ledger.upsert_species(web, payload, create=False)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    persist_web()
    return {**ledger.species_payload(web, node), "skipped_eats": skipped}


@app.delete("/admin/species/{species_id}")
def admin_delete_species(species_id: str) -> dict:
    web = get_web()
    if species_id not in web.nodes:
        raise HTTPException(404, "Species not on the ledger")
    node = ledger.delete_species(web, species_id)
    persist_web()
    return {"ok": True, "id": node.id}


def _cascade_payload(web, removed_id, result, narrative) -> dict:
    highlight_nodes = [removed_id] + [e.node_id for e in result.effects]
    edge_keys = []
    for effect in result.effects:
        edge_keys.extend(effect.reason_edge_ids)
    return {
        "removed": _node_public(web.nodes[removed_id]),
        "effects": [
            {
                **e.__dict__,
                "common_name": web.nodes[e.node_id].common_name,
                "name": web.nodes[e.node_id].name,
                "kingdom": web.nodes[e.node_id].kingdom,
            }
            for e in result.effects
        ],
        "story": narrative["story"],
        "template_story": narrative["template_story"],
        "lesson": narrative["lesson"],
        "llm": narrative["llm"],
        "highlight_node_ids": highlight_nodes,
        "highlight_edge_keys": edge_keys,
    }


def _node_public(node) -> dict:
    return node_public(node)


def _join(web: FoodWeb, ids: list[str]) -> str:
    labels = [web.nodes[i].common_name or web.nodes[i].name for i in ids[:8]]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" and {labels[-1]}"
