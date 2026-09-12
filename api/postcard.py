from __future__ import annotations

import re

from api.fal import generate_still

# Style comes AFTER the subject. Flux Schnell latches onto the first tokens,
# so "vintage Yellowstone postcard" first paints bison and geysers and drops aliens.
POSTCARD_LOOK = (
    "Style only, never the subject: vintage 1950s American gift-shop lithograph, "
    "cream deckled border, slight sun-fade, witty pulp souvenir print. "
    "No modern logos, no UI, no QR code, no watermark, no readable paragraphs. "
    "A tiny YELLOWSTONE caption bar at the margin is ok."
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


def _visual_hooks(prompt: str) -> str:
    text = prompt.lower()
    bits: list[str] = []
    if re.search(r"\b(aliens?|martians?|ufos?|flying saucers?|spaceships?)\b", text):
        bits.append(
            "green cartoon aliens in chrome flying saucers, big UFO discs in the sky, "
            "visible tractor beams"
        )
    if re.search(r"\b(magic|wizard)\b", text):
        bits.append("sparkling spells, pointed hats, glowing wands")
    if re.search(r"\btime travel\b", text):
        bits.append("a spinning clockwork time machine")
    if re.search(r"\b(dinosaurs?|kaiju|godzilla|dragons?)\b", text):
        bits.append("a giant creature towering over the trees")
    return ". ".join(bits)


def _literal_scene(prompt: str, extra: str = "") -> str:
    asked = prompt.strip().rstrip("?.!")
    hooks = _visual_hooks(prompt)
    hook_line = f"Must-see objects, large and obvious: {hooks}. " if hooks else ""
    return (
        f"{hook_line}"
        f"PRIMARY SUBJECT, large in frame, must match this what-if exactly: {asked}. "
        "Draw that event literally as a funny souvenir illustration. "
        f"{extra}"
        "Yellowstone National Park is only the STAGE: geyser steam, lodgepole pines, "
        "and golden grass stay in the BACKGROUND. "
        "Do not replace the requested event with a calm wildlife landscape. "
        "Do not add bison, elk, or geysers as the main characters unless the visitor named them. "
        "Cartoon physics is fine; keep it mail-home cute, not gory."
    )


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
    named = _join(cast_rows, 4)

    if action == "imagine":
        extra = (
            f"The named park animals in the action are {named}. "
            if named
            else ""
        )
        scene = _literal_scene(prompt, extra)
        caption = "A souvenir from a question the ranger did not see coming."
    elif action == "tell":
        extra = f"{lead} is the star of the joke. " if lead else ""
        scene = _literal_scene(prompt, extra)
        caption = f"{lead or 'The park'} stars in a story you can pin on the fridge."
    else:
        extra = (
            f"{(lead + ' are missing. ') if lead else ''}"
            f"{('Crowd of ' + up + '. ') if up else ''}"
            f"{('Scarce ' + down + '. ') if down else ''}"
        )
        scene = _literal_scene(prompt, extra)
        caption = (
            f"{up or 'Someone'} gets loud"
            + (f"; {down} pays the bill" if down else "")
            + "."
        )

    return {
        "title": title,
        "caption": caption,
        "prompt": f"{scene} {POSTCARD_LOOK}",
        "cast": _cast(cast_rows),
        "photos": [r["photo_url"] for r in cast_rows if r.get("photo_url")][:4],
    }


async def render_postcard(card: dict) -> dict:
    url = await generate_still(card["prompt"])
    public = {k: v for k, v in card.items() if k != "prompt"}
    public["image_url"] = url
    return public
