from __future__ import annotations

import os

import httpx

FAL_ENDPOINT = os.environ.get("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")
STYLE = (
    "Educational natural-history gouache painting of Yellowstone National Park, "
    "golden hour, cinematic still, realistic North American wildlife, no text, "
    "no captions, no watermark, no logos, no collage borders."
)


def fal_key() -> str | None:
    return os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY")


async def generate_still(prompt: str) -> str | None:
    key = fal_key()
    if not key:
        return None
    url = f"https://fal.run/{FAL_ENDPOINT}"
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            res = await client.post(
                url,
                headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "image_size": "landscape_4_3",
                    "num_images": 1,
                    "num_inference_steps": 4,
                    "acceleration": "high",
                    "output_format": "jpeg",
                },
            )
        if res.status_code >= 400:
            return None
        images = res.json().get("images") or []
        if not images:
            return None
        return images[0].get("url")
    except httpx.HTTPError:
        return None
