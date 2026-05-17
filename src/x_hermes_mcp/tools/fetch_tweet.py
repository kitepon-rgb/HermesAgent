"""`fetch_tweet` ツール — URL 1 つを構造化 JSON にして返す。"""

from __future__ import annotations

from typing import Any

from ..hermes_runner import run_json
from ..prompt_loader import fill, load


_PROMPT = load("fetch_tweet")
_TIMEOUT = 300.0


def fetch_tweet(url: str) -> dict[str, Any]:
    """X (Twitter) の投稿 1 件を構造化 JSON で返す。

    内部で Hermes Agent の x_search (Grok 4.20-reasoning 経由) を 1〜数回呼び出して
    投稿の本文・著者・日付・metrics・1 階層の引用情報を抽出する。応答に約 2 分かかる。
    """
    prompt = fill(_PROMPT, url=url)
    return run_json(prompt, timeout=_TIMEOUT)
