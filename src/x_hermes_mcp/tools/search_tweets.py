"""`search_tweets` ツール — キーワードでの投稿一覧取得。"""

from __future__ import annotations

from typing import Any

from ..hermes_runner import run_json
from ..prompt_loader import fill, load


_PROMPT = load("search_tweets")
_TIMEOUT = 240.0


def search_tweets(
    query: str,
    lang: str | None = None,
    since: str | None = None,
    until: str | None = None,
    from_user: str | None = None,
) -> dict[str, Any]:
    """キーワードで X 投稿を検索し、5〜10 件の構造化リストを返す。

    `since` / `until` を過去長期にすると `search_tweets_all` 相当の全期間検索になる。
    各エントリは tweet_id / url / author / 日付 / 短い本文。詳細データは fetch_tweet を呼ぶ。
    """
    prompt = fill(
        _PROMPT,
        query=query,
        lang=lang if lang is not None else "null",
        since=since if since is not None else "null",
        until=until if until is not None else "null",
        from_user=from_user if from_user is not None else "null",
    )
    return run_json(prompt, timeout=_TIMEOUT)
