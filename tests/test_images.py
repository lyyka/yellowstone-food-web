import asyncio
from unittest.mock import AsyncMock, patch

from api.images import generate_still, grok_still


def test_grok_still_reads_the_openai_style_url():
    payload = {"data": [{"url": "https://img.example/postcard.jpg"}]}

    class Resp:
        status_code = 200

        def json(self):
            return payload

    fake = AsyncMock()
    fake.__aenter__.return_value = fake
    fake.post = AsyncMock(return_value=Resp())
    with patch("api.images.grok_key", return_value="xai-test"), patch("api.images.httpx.AsyncClient", return_value=fake):
        url = asyncio.run(grok_still("aliens eat wolves"))
    assert url == "https://img.example/postcard.jpg"
    body = fake.post.await_args.kwargs["json"]
    assert body["model"] == "grok-imagine-image-2.0"
    assert body["aspect_ratio"] == "4:3"
    assert "aliens eat wolves" in body["prompt"]


def test_generate_still_uses_only_fal_when_asked():
    with (
        patch("api.images.grok_still", new=AsyncMock(return_value="https://grok.example/still.jpg")) as grok,
        patch("api.images.fal_still", new=AsyncMock(return_value="https://fal.example/still.jpg")) as fal,
    ):
        url = asyncio.run(generate_still("what if", "fal"))
    assert url == "https://fal.example/still.jpg"
    fal.assert_awaited_once()
    grok.assert_not_awaited()


def test_generate_still_falls_back_to_fal_when_auto_and_grok_is_quiet():
    with (
        patch("api.images.grok_still", new=AsyncMock(return_value=None)),
        patch("api.images.fal_still", new=AsyncMock(return_value="https://fal.example/still.jpg")) as fal,
    ):
        url = asyncio.run(generate_still("what if", "auto"))
    assert url == "https://fal.example/still.jpg"
    fal.assert_awaited_once()
