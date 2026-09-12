from __future__ import annotations

import os

import httpx

VOICE = (
    "You are a Yellowstone field-guide who talks like a sharp, warm human — "
    "campfire story, not a textbook. Answer the visitor's actual wording first. "
    "Use everyday language: elk getting cocky, willows getting mowed, wolves as the park's night shift. "
    "Name animals like characters. Vary sentence length. A little humor is good. "
    "Never say: released, knock-on, who-eats-whom, trophic, snapshot, headcount, "
    "documented food web, thought experiment, predation eases. "
    "Do not invent extra park mammals beyond the notes unless the visitor invited something wild "
    "(aliens, magic, time travel). Then invent freely, but keep the named park animals in the cast. "
    "You may guess at the spirit of a messy question (e.g. 'everyone tried to gray wolf' "
    "means people or animals all acting like wolves). "
    "If they bring aliens, time travel, magic, or anything not in the notebook, play along — "
    "keep Yellowstone's real animals in the scene as witnesses or co-stars. "
    "End with one grounded wink: this is a souvenir from the gift-shop of the mind, not a census. "
    "No markdown, no bullet lists, no numbered steps."
)


def grok_key() -> str | None:
    key = os.environ.get("XAI_API_KEY")
    return key or None


async def grok_chat(
    user: str,
    *,
    system: str = VOICE,
    temperature: float = 0.85,
    json_mode: bool = False,
) -> str | None:
    api_key = grok_key()
    if not api_key:
        return None
    payload: dict = {
        "model": os.environ.get("XAI_MODEL", "grok-4"),
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        payload["temperature"] = min(temperature, 0.3)
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            r = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def as_paragraphs(text: str) -> list[str]:
    chunks = [p.strip() for p in text.replace("\r", "").split("\n\n") if p.strip()]
    if len(chunks) == 1:
        chunks = [p.strip() for p in text.split("\n") if p.strip()]
    cleaned = []
    for chunk in chunks:
        line = " ".join(chunk.split())
        if line:
            cleaned.append(line)
    return cleaned[:6] or [text.strip()]
