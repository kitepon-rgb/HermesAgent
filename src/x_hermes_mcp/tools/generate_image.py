"""Generate an image via xAI and return three content blocks:

  1. ImageContent — JPEG (<=512px, q60). Rendered inline by Claude Code
     and (collapsed) by Claude Desktop. Silently dropped by Claude.ai web
     and ChatGPT (known platform limitation, see DOCS/plan.md Phase 10),
     so it is a "bonus" path, not the primary one.
  2. TextContent (user-facing) — leads with the stable permanent URL on
     OUR domain as a bare https:// link. Web clients auto-link bare URLs,
     so even when the inline image is dropped the user always has one
     click to view the result. Kept short so the LLM relays it as-is
     instead of summarising "完了しました" with no link.
  3. TextContent (machine-readable JSON) — full metadata (url, model,
     cost ticks, prompt, etc.) for callers that want to chain on it.

A simple time-based GC runs opportunistically on each call.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

from fastmcp.utilities.types import Image
from mcp.types import TextContent
from PIL import Image as PilImage

from ..image_client import ImageGenError, call_image_generate

log = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT_S = 30
# Aggressive defaults: a 768px / q75 JPEG of a high-frequency scene
# (brick walls, foliage) still went to ~190 KB inline, which some MCP
# clients drop or mis-render. 512px / q60 keeps everything under ~50 KB
# while still being a perfectly readable preview; the full-res image
# is always available via permanent_url.
_INLINE_MAX_PX = 512
_INLINE_JPEG_QUALITY = 60
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


def _user_facing_text(meta: dict[str, Any]) -> str:
    """The message the assistant should relay verbatim to the user.

    Lead with the URL, kept short and link-detector-friendly so web chat
    UIs auto-render it as a clickable link even when they drop the
    inline image block.
    """
    view_url = meta.get("permanent_url") or meta.get("url") or ""
    lines = [f"Generated image — open to view: {view_url}"]
    detail_bits: list[str] = []
    if meta.get("model"):
        detail_bits.append(str(meta["model"]))
    if meta.get("aspect_ratio"):
        detail_bits.append(str(meta["aspect_ratio"]))
    if meta.get("resolution"):
        detail_bits.append(str(meta["resolution"]))
    if detail_bits:
        lines.append("(" + " · ".join(detail_bits) + ")")
    if meta.get("hosting_error") or meta.get("download_error"):
        problem = meta.get("hosting_error") or meta.get("download_error")
        lines.append(f"Note: {problem}")
    return "\n".join(lines)


def _error_only(meta: dict[str, Any]) -> list[Any]:
    """Surface failures to the user too, not just in JSON.

    Without this, a download/hosting failure becomes an opaque
    `{"download_error": ...}` JSON dump and the LLM tends to silently
    report "completed!" with nothing to show. We force the error to
    travel in the user-facing text so the assistant can relay it.
    """
    parts = []
    if meta.get("error"):
        parts.append(f"Image generation failed: {meta['error']}")
    elif meta.get("download_error"):
        parts.append(
            f"Image generated but our server could not fetch it: "
            f"{meta['download_error']}"
        )
        if meta.get("url"):
            parts.append(f"xAI source (short-lived): {meta['url']}")
    else:
        parts.append("Image generation returned no usable URL.")
    return [
        TextContent(type="text", text="\n".join(parts)),
        TextContent(type="text", text=json.dumps(meta, ensure_ascii=False)),
    ]


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
        return _error_only({
            "error": str(exc),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "quality": quality,
            "source": "xai_imgen_raw_v1",
        })

    url = meta.get("url")
    if not url:
        return _error_only(meta)

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
        return _error_only(meta)

    now = time.time()
    _gc(now)

    # Persist original bytes under an unguessable id so the client always has
    # a stable URL on our domain — required because the xAI temp URL is
    # short-lived AND most web clients drop the inline ImageContent block.
    ext = _ext_from_mime(meta.get("mime_type"))
    file_id = uuid.uuid4().hex
    try:
        IMAGE_STORE.mkdir(parents=True, exist_ok=True)
        (IMAGE_STORE / f"{file_id}.{ext}").write_bytes(img_bytes)
        meta["permanent_url"] = f"{PUBLIC_BASE_URL}/images/{file_id}.{ext}"
    except OSError as exc:
        log.warning("image hosting save failed: %s", exc)
        meta["hosting_error"] = f"could not persist image locally: {exc}"

    inline_bytes = _compress_for_inline(img_bytes)
    meta["inline_bytes"] = len(inline_bytes)
    image = Image(data=inline_bytes, format="jpeg")
    user_text = TextContent(type="text", text=_user_facing_text(meta))
    meta_text = TextContent(type="text", text=json.dumps(meta, ensure_ascii=False))
    return [image, user_text, meta_text]
