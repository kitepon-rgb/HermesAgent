"""Thin MCP-side wrapper around image_client.call_image_generate."""

from __future__ import annotations

from typing import Any

from ..image_client import ImageGenError, call_image_generate


def generate_image(
    *,
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
    quality: bool = False,
) -> dict[str, Any]:
    try:
        return call_image_generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            quality=quality,
        )
    except ImageGenError as exc:
        return {
            "error": str(exc),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "quality": quality,
            "source": "xai_imgen_raw_v1",
        }
