"""`get_quote_tweets` ツール — 指定ツイートを引用したポスト一覧。"""

from __future__ import annotations

from typing import Any

from ..hermes_runner import run_json
from ..prompt_loader import fill, load


_PROMPT = load("get_quote_tweets")
_TIMEOUT = 300.0


def get_quote_tweets(source_url: str, max_quotes: int = 8) -> dict[str, Any]:
    """ソースツイートを引用した最近のポストを 5〜10 件サンプル取得する。

    各引用ツイートに著者・日付・本文・言語ヒントが付く。
    引用総数 (`source_total_quotes`) も合わせて取得。応答 2〜3 分。
    """
    prompt = fill(_PROMPT, source_url=source_url, max_quotes=max_quotes)
    return run_json(prompt, timeout=_TIMEOUT)
