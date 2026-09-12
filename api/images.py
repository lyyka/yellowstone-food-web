from __future__ import annotations

import os

import httpx

from api.fal import generate_still as fal_still
from api.grok import grok_key

XAI_IMAGE_URL = "https://api.x.ai/v1/images/generations"


def image_model() -> str:
    return os.environ.get("XAI_IMAGE_MODEL", "grok-imagine-image-2.0")


async def grok_still(prompt: str) -> str | None:
    key = grok_key()
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=70.0) as client:
            res = await client.post(
                XAI_IMAGE_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": image_model(),
                    "prompt": prompt,
                    "n": 1,
                    "aspect_ratio": "4:3",
                    "resolution": "1k",
                    "quality": os.environ.get("XAI_IMAGE_QUALITY", "low"),
                },
            )
        if res.status_code >= 400:
            return None
        rows = res.json().get("data") or []
        if not rows:
            return None
        return rows[0].get("url")
    except httpx.HTTPError:
        return None


async def generate_still(prompt: str, provider: str | None = None) -> str | None:
    kind = (provider or "grok").strip().lower()
    if kind in {"fal", "flux", "schnell"}:
        return await fal_still(prompt)
    if kind in {"auto", "any"}:
        return await grok_still(prompt) or await fal_still(prompt)
    return await grok_still(prompt)
