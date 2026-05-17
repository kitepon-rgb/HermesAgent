"""raw x_search の JSON answer をパースするための共有ヘルパ。

各 raw ツール (`fetch_tweet` / `search_tweets` / `get_quote_tweets` / `get_trends`)
が共通で使う:

- `extract_json` — Grok が ` ```json ... ``` ` ラップしてくる場合と裸 JSON で
  返してくる場合の両方を扱える balanced-brace 抽出器
- `stringify_metrics` — V3 の str 互換のために int 値を str 化
- `tweet_id_from_url` / `author_from_url` — URL 解析
"""

from __future__ import annotations

import json
import re
from typing import Any


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_STATUS_ID_RE = re.compile(r"/status/(\d+)")
_X_AUTHOR_RE = re.compile(r"x\.com/([^/?#]+)/status/", re.IGNORECASE)

_DEFAULT_METRIC_KEYS = (
    "likes",
    "retweets",
    "replies",
    "quotes",
    "bookmarks",
    "views",
)


def extract_json(text: str) -> dict[str, Any]:
    """answer 文字列の中から最初の JSON オブジェクトを取り出してパースする。

    Grok がコードフェンスでラップしてくる場合と、裸の JSON で返してくる場合の
    両方に対応する。balanced-brace 検出で誤切断を避ける。
    """
    text = text.strip()
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        return json.loads(fence_match.group(1))

    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in answer: {text[:200]!r}")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced JSON in answer")


def stringify_metrics(
    m: dict[str, Any] | None,
    keys: tuple[str, ...] = _DEFAULT_METRIC_KEYS,
) -> dict[str, str | None]:
    """V3 と互換性のため metrics 値を str に揃える (元データは int で来る)。"""
    if not isinstance(m, dict):
        return {k: None for k in keys}
    out: dict[str, str | None] = {}
    for key in keys:
        v = m.get(key)
        out[key] = str(v) if v is not None else None
    return out


def tweet_id_from_url(url: str) -> str | None:
    if not url:
        return None
    m = _STATUS_ID_RE.search(url)
    return m.group(1) if m else None


def author_from_url(url: str) -> str | None:
    if not url:
        return None
    m = _X_AUTHOR_RE.search(url)
    if not m:
        return None
    handle = m.group(1).lstrip("@")
    # `x.com/i/status/...` のような handle 不明 URL は除外
    if handle.lower() == "i":
        return None
    return handle
