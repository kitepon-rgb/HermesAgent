"""`fetch_tweet` ツール — raw x_search + Python パーサ (P7 V4)。

旧 V3 は `hermes -z` 経由で Grok-4.3 が synthesis していたが、本実装は
`x_search` を 1 回直接呼び出して JSON 応答を引き出し、Python 側でスキーマに
マップする。応答 ~25-45 秒、出力は決定的、Grok-4.3 quota 消費ゼロ。
"""

from __future__ import annotations

from typing import Any

from .._parse import extract_json, stringify_metrics, tweet_id_from_url
from ..x_search_client import call_x_search


_QUERY_TEMPLATE = """For the X post at {url}, return ONLY a single JSON object with these keys (no other text):
{{
  "author_username": string,
  "author_display_name": string,
  "created_at": string (ISO 8601 if possible, else any precise timestamp),
  "text": string (full post body, t.co URLs expanded),
  "metrics": {{"likes": int, "retweets": int, "replies": int, "quotes": int, "bookmarks": int, "views": int}},
  "quoted_tweet": null OR {{"tweet_id": string, "url": string, "author_username": string, "text": string}},
  "media": [ {{"type": "photo"|"video"|"animated_gif"|"link_card", "description": string}} ]
}}
Use null for unavailable fields. Do not invent. Output starts with {{ and ends with }}."""


def fetch_tweet(url: str) -> dict[str, Any]:
    """X 投稿 1 件を ConnectC2X 互換スキーマで返す (raw x_search 経路)。"""
    raw = call_x_search(
        query=_QUERY_TEMPLATE.format(url=url),
        enable_image_understanding=True,
        enable_video_understanding=True,
    )
    if not raw.get("success"):
        raise RuntimeError(f"x_search failed: {raw}")

    parsed = extract_json(raw.get("answer", ""))

    quoted = parsed.get("quoted_tweet")
    referenced_tweets: list[dict[str, Any]] = []
    if isinstance(quoted, dict):
        referenced_tweets.append(
            {
                "type": "quoted",
                "tweet_id": quoted.get("tweet_id"),
                "author_username": quoted.get("author_username"),
                "text": quoted.get("text"),
            }
        )

    media_out: list[dict[str, Any]] = []
    for m in parsed.get("media") or []:
        if not isinstance(m, dict):
            continue
        media_out.append(
            {
                "type": m.get("type"),
                "url": None,
                "alt_text": m.get("description"),
            }
        )

    return {
        "tweet_id": tweet_id_from_url(url) or "",
        "url": url,
        "author": {
            "username": parsed.get("author_username"),
            "display_name": parsed.get("author_display_name"),
        },
        "created_at": parsed.get("created_at"),
        "text": parsed.get("text"),
        "referenced_tweets": referenced_tweets,
        "metrics": stringify_metrics(parsed.get("metrics")),
        "media": media_out,
        "notes": None,
        "source": "x_search_raw_v4",
    }
