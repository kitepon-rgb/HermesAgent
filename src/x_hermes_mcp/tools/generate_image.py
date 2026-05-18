"""Thin MCP-side wrapper around image_client.call_image_generate.

Downloads the temp URL returned by xAI and returns the bytes as an MCP
``ImageContent`` block so clients (Claude.ai, ChatGPT connectors, etc.)
can render inline without hitting CORS / expiry on the original URL.
The metadata dict is returned alongside so the original URL, model,
cost, etc. stay visible.
"""

from __future__ import annotations

from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

from fastmcp.utilities.types import Image

from ..image_client import ImageGenError, call_image_generate

_DOWNLOAD_TIMEOUT_S = 30


def _format_from_mime(mime: str | None) -> str:
    if not mime or "/" not in mime:
        return "png"
    return mime.split("/", 1)[1].lower()


def generate_image(
    *,
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
    quality: bool = False,
) -> list[Any]:
    try:
        meta = call_image_generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            quality=quality,
        )
    except ImageGenError as exc:
        return [{
            "error": str(exc),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "quality": quality,
            "source": "xai_imgen_raw_v1",
        }]

    url = meta.get("url")
    if not url:
        return [meta]

    # imgen.x.ai 403s requests with the default `Python-urllib/*` UA, so we
    # pose as a generic browser. The content is the same bytes either way.
    req = urllib_request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (x-hermes-mcp)"},
    )
    try:
        with urllib_request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT_S) as resp:
            if resp.status != 200:
                raise URLError(f"HTTP {resp.status}")
            img_bytes = resp.read()
    except (URLError, TimeoutError, OSError) as exc:
        meta["download_error"] = f"failed to fetch image bytes: {exc}"
        return [meta]

    image = Image(data=img_bytes, format=_format_from_mime(meta.get("mime_type")))
    return [image, meta]
