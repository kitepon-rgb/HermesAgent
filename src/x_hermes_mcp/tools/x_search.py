"""`x_search` ツール — xAI Responses API 直接呼び出し (Grok-4.3 ラップなし)。"""

from __future__ import annotations

from typing import Any

from ..x_search_client import call_x_search


def x_search(
    query: str,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
) -> dict[str, Any]:
    """x_search 直接呼び出し。Hermes Python venv 内で `x_search_tool()` を実行し、
    xAI Responses API の生の構造体を返す。応答 30〜45 秒。
    """
    return call_x_search(
        query=query,
        allowed_x_handles=allowed_x_handles,
        excluded_x_handles=excluded_x_handles,
        from_date=from_date,
        to_date=to_date,
        enable_image_understanding=enable_image_understanding,
        enable_video_understanding=enable_video_understanding,
    )
