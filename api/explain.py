from __future__ import annotations

from typing import Any

from api.cascade import CascadeResult
from api.graph_model import FoodWeb
from api.grok import as_paragraphs, grok_chat


def template_story(result: CascadeResult) -> list[str]:
    return list(result.story)


async def enrich_story(
    web: FoodWeb,
    result: CascadeResult,
    question: str | None = None,
) -> dict[str, Any]:
    base = template_story(result)
    lesson = _lesson(web, result)
    notes = _fact_sheet(web, result)
    raw = await grok_chat(
        (
            f'The visitor asked: "{question or "what happens if this animal is gone?"}"\n\n'
            f"{notes}\n\n"
            "Write 3 short paragraphs separated by blank lines. "
            "Talk to them, not about 'the model'."
        ),
        temperature=0.9,
    )
    return {
        "story": as_paragraphs(raw) if raw else base,
        "template_story": base,
        "lesson": lesson,
        "llm": bool(raw),
    }


def _fact_sheet(web: FoodWeb, result: CascadeResult) -> str:
    gone = result.removed_ids or [result.removed]
    labels = [web.nodes[i].common_name or web.nodes[i].name for i in gone if i in web.nodes]
    up = []
    down = []
    for effect in result.effects[:10]:
        node = web.nodes[effect.node_id]
        name = node.common_name or node.name
        if effect.delta_sign > 0:
            up.append(name)
        else:
            down.append(name)
    return (
        f"Animals set aside in this telling: {', '.join(labels) or 'none'}.\n"
        f"Creatures that might breathe easier: {', '.join(up) or 'none listed'}.\n"
        f"Creatures that might have a harder season: {', '.join(down) or 'none listed'}."
    )


def _lesson(web: FoodWeb, result: CascadeResult) -> dict[str, str]:
    removed = web.nodes[result.removed]
    has_plants = any(
        web.nodes[e.node_id].kingdom == "Plantae" and e.delta_sign < 0 for e in result.effects
    )
    if has_plants:
        return {
            "title": "When the hunter leaves town",
            "blurb": (
                f"Take {removed.common_name or removed.name} off the night shift and the grazers "
                "often throw a party — then the willows pay the tab. That's the Yellowstone wolf story "
                "in street clothes."
            ),
        }
    if any(e.delta_sign > 0 and e.depth == 1 for e in result.effects):
        return {
            "title": "Someone else gets the leftovers",
            "blurb": (
                "Lose a hunter and the animals on its menu may swagger for a while. "
                "The park does not send a memo; the menu just shifts."
            ),
        }
    return {
        "title": "A park is a dinner table",
        "blurb": (
            "We only know the meals people have written down. A missing line on the menu "
            "is missing paperwork, not proof that nobody ate."
        ),
    }
