"""`fetch_tweet_chain` ツール — fetch_tweet を再帰的に並列実行して引用ツリーを展開する。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .fetch_tweet import fetch_tweet


_HARD_MAX_DEPTH = 2
_PARALLEL_WORKERS = 4


def _build_url(author_username: str | None, tweet_id: str) -> str:
    """`referenced_tweets` のエントリから X 投稿 URL を組み立てる。"""
    if author_username:
        return f"https://x.com/{author_username}/status/{tweet_id}"
    return f"https://x.com/i/status/{tweet_id}"


def _safe_fetch(url: str) -> dict[str, Any]:
    """fetch_tweet を呼んで、失敗時はエラー情報を返す (ツリー全体を壊さない)。"""
    try:
        return {"ok": True, "url": url, "data": fetch_tweet(url)}
    except Exception as exc:
        return {"ok": False, "url": url, "error": f"{type(exc).__name__}: {exc}"}


def fetch_tweet_chain(url: str, max_depth: int = 2) -> dict[str, Any]:
    """ルート URL の引用ツイートを `max_depth` 階層まで並列展開して返す。

    max_depth は 1 または 2 (ハード上限 2)。各 fetch_tweet は ~1.5 分。
    並列実行のため、depth=2 でファンアウト数件でも全体 ~3〜5 分で収まる想定。
    """
    if max_depth < 1 or max_depth > _HARD_MAX_DEPTH:
        raise ValueError(f"max_depth must be 1..{_HARD_MAX_DEPTH}, got {max_depth}")

    nodes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    root_result = _safe_fetch(url)
    if not root_result["ok"]:
        return {
            "root_url": url,
            "max_depth": max_depth,
            "nodes": [],
            "errors": [{"depth": 0, "parent_tweet_id": None, **root_result}],
        }

    root_data = root_result["data"]
    root_tweet_id = root_data.get("tweet_id")
    nodes.append({"depth": 0, "parent_tweet_id": None, "data": root_data})

    def _collect_children(parent_data: dict[str, Any]) -> list[tuple[str, str]]:
        """parent_data の `referenced_tweets` から (parent_tweet_id, url) のリストを作る。"""
        parent_id = parent_data.get("tweet_id")
        children: list[tuple[str, str]] = []
        for ref in parent_data.get("referenced_tweets") or []:
            tid = ref.get("tweet_id")
            if not tid:
                continue
            child_url = _build_url(ref.get("author_username"), tid)
            children.append((parent_id, child_url))
        return children

    depth_1_jobs = _collect_children(root_data)

    if depth_1_jobs:
        with ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS) as pool:
            futures = [pool.submit(_safe_fetch, u) for _, u in depth_1_jobs]
            depth_1_results = [f.result() for f in futures]
        for (parent_id, _u), result in zip(depth_1_jobs, depth_1_results):
            if result["ok"]:
                nodes.append({"depth": 1, "parent_tweet_id": parent_id, "data": result["data"]})
            else:
                errors.append({"depth": 1, "parent_tweet_id": parent_id, **result})

    if max_depth >= 2:
        depth_2_jobs: list[tuple[str, str]] = []
        for node in nodes:
            if node["depth"] != 1:
                continue
            depth_2_jobs.extend(_collect_children(node["data"]))

        if depth_2_jobs:
            with ThreadPoolExecutor(max_workers=_PARALLEL_WORKERS) as pool:
                futures = [pool.submit(_safe_fetch, u) for _, u in depth_2_jobs]
                depth_2_results = [f.result() for f in futures]
            for (parent_id, _u), result in zip(depth_2_jobs, depth_2_results):
                if result["ok"]:
                    nodes.append({"depth": 2, "parent_tweet_id": parent_id, "data": result["data"]})
                else:
                    errors.append({"depth": 2, "parent_tweet_id": parent_id, **result})

    return {
        "root_url": url,
        "root_tweet_id": root_tweet_id,
        "max_depth": max_depth,
        "nodes": nodes,
        "errors": errors,
    }
