from __future__ import annotations

import re

from api.fal import generate_still

POSTCARD_LOOK = (
    "Authentic vintage 1950s American gift-shop souvenir postcard, offset lithograph, "
    "cream deckled border, slight sun-fade, collectible Yellowstone National Park print. "
    "No modern logos, no UI, no QR code, no watermark. Do not render readable sentences; "
    "a tiny 'YELLOWSTONE' caption bar at the margin is ok. Cinematic, witty, printable."
)


def _label(row: dict) -> str:
    return (row.get("common_name") or row.get("name") or "").strip()


def _join(rows: list[dict], n: int = 3) -> str:
    names = [_label(r) for r in rows if _label(r)][:n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _cast(rows: list[dict], n: int = 4) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        sid = row.get("id")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append({"id": sid, "label": _label(row) or sid})
        if len(out) >= n:
            break
    return out


def souvenir_title(prompt: str) -> str:
    text = re.sub(r"^\s*what if\s+", "", prompt.strip(), flags=re.I)
    text = text.strip(" ?!.")
    if not text:
        return "Greetings from Yellowstone"
    if text[0].islower():
        text = text[0].upper() + text[1:]
    return text[:72]


def plan_postcard(
    prompt: str,
    plan: dict,
    removed: list[dict],
    released: list[dict],
    pressured: list[dict],
    focus: list[dict],
) -> dict:
    action = plan.get("action") or ""
    lead = _join(focus or removed, 2)
    up = _join(released)
    down = _join(pressured)
    title = souvenir_title(prompt)
    cast_rows = focus or removed or released or pressured

    if action == "imagine":
        scene = (
            f"The visitor's exact daydream, set in Yellowstone: {prompt.strip()}. "
            "Famous park landmarks (Old Faithful, bison, lodgepole, Grand Prismatic) witness the chaos. "
            "Playful, wondrous, still a postcard you would mail home."
        )
        caption = "A souvenir from a question the ranger did not see coming."
    elif action == "tell":
        scene = (
            f"Yellowstone animals living the visitor's joke. {lead or 'The usual cast'} in the middle of it. "
            f"Premise: {prompt.strip()}."
        )
        caption = f"{lead or 'The park'} stars in a story you can pin on the fridge."
    else:
        scene = (
            f"Yellowstone after the what-if. "
            f"{(lead + ' missing from the usual overlook. ') if lead else ''}"
            f"{('Bold, plentiful ' + up + '. ') if up else ''}"
            f"{('Threadbare ' + down + '. ') if down else ''}"
            f"Visitor asked: {prompt.strip()}."
        )
        caption = (
            f"{up or 'Someone'} gets loud"
            + (f"; {down} pays the bill" if down else "")
            + "."
        )

    return {
        "title": title,
        "caption": caption,
        "prompt": f"{POSTCARD_LOOK} Illustrated scene: {scene}",
        "cast": _cast(cast_rows),
        "photos": [r["photo_url"] for r in cast_rows if r.get("photo_url")][:4],
    }


async def render_postcard(card: dict) -> dict:
    url = await generate_still(card["prompt"])
    public = {k: v for k, v in card.items() if k != "prompt"}
    public["image_url"] = url
    return public
