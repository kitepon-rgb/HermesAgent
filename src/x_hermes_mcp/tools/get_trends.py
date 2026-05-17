"""`get_trends` ツール — 地域別 X トレンド取得。"""

from __future__ import annotations

from typing import Any

from ..hermes_runner import run_json
from ..prompt_loader import fill, load


_PROMPT = load("get_trends")
_TIMEOUT = 360.0


def get_trends(region: str = "Japan", max_trends: int = 10) -> dict[str, Any]:
    """指定地域の現在の X トレンドを構造化リストで返す。

    各トレンドにカテゴリ・関連エンティティ・代表投稿 URL が付く。
    応答 3〜4 分 (件数分の証拠 URL 取得で重め)。
    """
    prompt = fill(_PROMPT, region=region, max_trends=max_trends)
    return run_json(prompt, timeout=_TIMEOUT)
