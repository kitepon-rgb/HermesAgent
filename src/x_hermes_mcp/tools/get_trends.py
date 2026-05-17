"""`get_trends` ツール — raw x_search + Python パーサ (P7 V4)。

x_search に「現在の地域別 X トレンドを JSON で返せ」と指示。各トレンドに
カテゴリ・関連エンティティ・代表投稿 URL を含めさせる。
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .._parse import extract_json
from ..x_search_client import call_x_search


_QUERY_TEMPLATE = """List the current X trending topics for region "{region}" (like the X "Trends for you" panel). Aim for {max_trends} trends.

Return ONLY a single JSON object (no other text):
{{
  "trends": [
    {{
      "rank": int OR null,
      "topic": string (verbatim trend word or hashtag),
      "category": string (one of: game / idol / music / news / politics / sports / entertainment / tv / tech / business / people / other),
      "related_to": string OR null (specific entity name, e.g. a celebrity / game title / company),
      "volume": string OR null (post count if shown on X, e.g. "12.3K Posts"),
      "evidence_url": string (one canonical https://x.com/<author>/status/<id> exemplifying this trend),
      "note": string OR null (short context: event, date, what is happening)
    }}
  ],
  "notes": string OR null
}}

For EACH trend: topic, category, evidence_url are REQUIRED.
Do not invent. Output starts with {{ and ends with }}."""


def get_trends(region: str = "Japan", max_trends: int = 10) -> dict[str, Any]:
    """地域別 X トレンドリストを構造化で返す (raw x_search 経路)。"""
    raw = call_x_search(
        query=_QUERY_TEMPLATE.format(region=region, max_trends=max_trends),
    )
    if not raw.get("success"):
        raise RuntimeError(f"x_search failed: {raw}")

    parsed = extract_json(raw.get("answer", ""))

    trends_out: list[dict[str, Any]] = []
    for t in parsed.get("trends") or []:
        if not isinstance(t, dict):
            continue
        trends_out.append(
            {
                "rank": t.get("rank"),
                "topic": t.get("topic"),
                "category": t.get("category"),
                "related_to": t.get("related_to"),
                "volume": t.get("volume"),
                "evidence_url": t.get("evidence_url"),
                "note": t.get("note"),
            }
        )

    return {
        "region": region,
        "fetched_at": date.today().isoformat(),
        "trends": trends_out,
        "notes": parsed.get("notes"),
        "source": "x_search_raw_v4",
    }
