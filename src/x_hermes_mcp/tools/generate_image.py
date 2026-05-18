"""Generate an image via xAI and return both:

  1. an MCP ImageContent block — JPEG-recompressed and resized to <=768px
     so the base64 payload stays under ~100 KB (a 300-400 KB inline image
     ran into intermittent rendering failures on Claude.ai).
  2. a metadata dict — includes the original xAI temp URL plus a stable
     `permanent_url` served from this server (so clients that prefer
     <img src> over base64 always have a working source).

A simple time-based GC runs opportunistically on each call.
"""

from __future__ import annotations

import io
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

from fastmcp.utilities.types import Image
from PIL import Image as PilImage

from ..image_client import ImageGenError, call_image_generate

log = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT_S = 30
_INLINE_MAX_PX = 768          # cap longest side for inline base64
_INLINE_JPEG_QUALITY = 75     # JPEG quality for inline base64
_RETENTION_SECONDS = 30 * 24 * 3600

IMAGE_STORE = Path(os.getenv("X_HERMES_IMAGE_STORE", "/data/images"))
PUBLIC_BASE_URL = os.getenv(
    "X_HERMES_MCP_BASE_URL", "https://hermes.kitepon.dynv6.net"
).rstrip("/")


def _ext_from_mime(mime: str | None) -> str:
    if not mime or "/" not in mime:
        return "png"
    sub = mime.split("/", 1)[1].lower()
    return "jpg" if sub == "jpeg" else sub


def _gc(now: float) -> None:
    """Opportunistic delete of files older than _RETENTION_SECONDS.

    Cheap (single stat per file) so it's fine to run on every tool call.
    Wrapped in broad except — disk hiccups must not break image generation.
    """
    try:
        if not IMAGE_STORE.is_dir():
            return
        cutoff = now - _RETENTION_SECONDS
        for p in IMAGE_STORE.iterdir():
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
            except OSError:
                continue
    except Exception as exc:
        log.warning("image GC skipped: %s", exc)


def _compress_for_inline(img_bytes: bytes) -> bytes:
    """Resize + JPEG-recompress to keep inline payload small.

    On any failure, fall back to the original bytes — better to ship a
    bigger image than to ship nothing.
    """
    try:
        pil = PilImage.open(io.BytesIO(img_bytes))
        if pil.mode not in {"RGB", "L"}:
            pil = pil.convert("RGB")
        pil.thumbnail((_INLINE_MAX_PX, _INLINE_MAX_PX), PilImage.LANCZOS)
        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=_INLINE_JPEG_QUALITY, optimize=True)
        return buf.getvalue()
    except Exception as exc:
        log.warning("inline compression failed (%s); using original bytes", exc)
        return img_bytes


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

    now = time.time()
    _gc(now)

    # Persist original bytes under an unguessable id so the client can fall
    # back to <img src=...> against our own domain.
    ext = _ext_from_mime(meta.get("mime_type"))
    file_id = uuid.uuid4().hex
    try:
        IMAGE_STORE.mkdir(parents=True, exist_ok=True)
        (IMAGE_STORE / f"{file_id}.{ext}").write_bytes(img_bytes)
        meta["permanent_url"] = f"{PUBLIC_BASE_URL}/images/{file_id}.{ext}"
    except OSError as exc:
        # Hosting is a fallback path, not the primary one — log and continue
        # so the inline image still works.
        log.warning("image hosting save failed: %s", exc)
        meta["hosting_error"] = f"could not persist image locally: {exc}"

    inline_bytes = _compress_for_inline(img_bytes)
    meta["inline_bytes"] = len(inline_bytes)
    image = Image(data=inline_bytes, format="jpeg")
    return [image, meta]
