"""`get_quote_tweets` ツール — raw x_search + Python パーサ (P7 V4)。

ソース著者を URL から抽出して `excluded_x_handles=[source_author]` で
x_search に渡すことで、ソース著者自身の follow-up 投稿を除外する。
"""

from __future__ import annotations

from typing import Any

from .._parse import author_from_url, extract_json, stringify_metrics, tweet_id_from_url
from ..x_search_client import call_x_search


_QUERY_TEMPLATE = """List 5-10 recent posts that quote-tweet the X post at {source_url}.

Return ONLY a single JSON object (no other text):
{{
  "source_total_quotes": string OR null,
  "quotes": [
    {{
      "tweet_id": string,
      "url": string,
      "author_username": string (without @),
      "author_display_name": string OR null,
      "created_at": string (ISO 8601 if possible),
      "text": string (full body of the quoting post),
      "language": string OR null (two-letter code like "ja", "en", "fr"),
      "metrics": {{"likes": int|null, "retweets": int|null, "replies": int|null}}
    }}
  ],
  "notes": string OR null
}}

For EACH quote the following fields are REQUIRED: tweet_id, url, author_username, text.
source_total_quotes is the total quote count on the source post (from its engagement metrics), as a number or null if unavailable.
Do not invent. Output starts with {{ and ends with }}."""


def get_quote_tweets(source_url: str, max_quotes: int = 8) -> dict[str, Any]:
    """ソースツイートを引用した最近の投稿を 5〜10 件サンプル (raw x_search 経路)。"""
    source_author = author_from_url(source_url)

    raw = call_x_search(
        query=_QUERY_TEMPLATE.format(source_url=source_url),
        excluded_x_handles=[source_author] if source_author else None,
    )
    if not raw.get("success"):
        raise RuntimeError(f"x_search failed: {raw}")

    parsed = extract_json(raw.get("answer", ""))

    quotes_out: list[dict[str, Any]] = []
    for q in parsed.get("quotes") or []:
        if not isinstance(q, dict):
            continue
        quotes_out.append(
            {
                "tweet_id": q.get("tweet_id"),
                "url": q.get("url"),
                "author_username": q.get("author_username"),
                "author_display_name": q.get("author_display_name"),
                "created_at": q.get("created_at"),
                "text": q.get("text"),
                "language": q.get("language"),
                "metrics": stringify_metrics(
                    q.get("metrics"),
                    keys=("likes", "retweets", "replies"),
                ) if q.get("metrics") else None,
            }
        )

    return {
        "source_tweet_url": source_url,
        "source_tweet_id": tweet_id_from_url(source_url),
        "source_total_quotes": (
            str(parsed["source_total_quotes"])
            if parsed.get("source_total_quotes") is not None
            else None
        ),
        "quotes": quotes_out,
        "notes": parsed.get("notes"),
        "source": "x_search_raw_v4",
    }
