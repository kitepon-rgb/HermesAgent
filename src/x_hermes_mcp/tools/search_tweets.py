"""`search_tweets` ツール — raw x_search + Python パーサ (P7 V4)。

`from_user` は `allowed_x_handles=[user]`、`since`/`until` は `from_date`/`to_date`
として x_search の構造化パラメータに直接渡す。JSON 応答を Python でパース。
"""

from __future__ import annotations

from typing import Any

from .._parse import extract_json, stringify_metrics
from ..x_search_client import call_x_search


_QUERY_TEMPLATE = """Search X for posts matching the keyword "{query}"{lang_clause}, ordered by recency. Aim for 5-10 results.

Return ONLY a single JSON object (no other text):
{{
  "results": [
    {{
      "tweet_id": string,
      "url": string (canonical https://x.com/<author>/status/<id>),
      "author_username": string (without @),
      "author_display_name": string OR null,
      "created_at": string (ISO 8601 if possible, else any timestamp),
      "text": string (one-line snippet or full body),
      "metrics": {{"likes": int|null, "retweets": int|null, "replies": int|null}}
    }}
  ],
  "total_estimated": string OR null,
  "notes": string OR null
}}

For EACH result the following fields are REQUIRED and must not be null: tweet_id, url, author_username, text. Metrics may be null per-field.
Do not invent. Output starts with {{ and ends with }}."""


def search_tweets(
    query: str,
    lang: str | None = None,
    since: str | None = None,
    until: str | None = None,
    from_user: str | None = None,
) -> dict[str, Any]:
    """キーワードで X 投稿を検索し 5〜10 件返す (raw x_search 経路)。"""
    # 言語は x_search パラメータが無いのでクエリ文字列に埋める
    lang_clause = f" (language: {lang})" if lang else ""

    raw = call_x_search(
        query=_QUERY_TEMPLATE.format(query=query, lang_clause=lang_clause),
        allowed_x_handles=[from_user] if from_user else None,
        from_date=since,
        to_date=until,
    )
    if not raw.get("success"):
        raise RuntimeError(f"x_search failed: {raw}")

    parsed = extract_json(raw.get("answer", ""))

    results_out: list[dict[str, Any]] = []
    for r in parsed.get("results") or []:
        if not isinstance(r, dict):
            continue
        results_out.append(
            {
                "tweet_id": r.get("tweet_id"),
                "url": r.get("url"),
                "author_username": r.get("author_username"),
                "author_display_name": r.get("author_display_name"),
                "created_at": r.get("created_at"),
                "text": r.get("text"),
                "metrics": stringify_metrics(
                    r.get("metrics"),
                    keys=("likes", "retweets", "replies"),
                ) if r.get("metrics") else None,
            }
        )

    return {
        "query": query,
        "filters": {
            "lang": lang,
            "since": since,
            "until": until,
            "from_user": from_user,
        },
        "results": results_out,
        "total_estimated": parsed.get("total_estimated"),
        "notes": parsed.get("notes"),
        "source": "x_search_raw_v4",
    }
