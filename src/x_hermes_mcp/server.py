"""X-HERMES-MCP サーバ — FastMCP エントリポイント。

トランスポートは env で切替:
- `X_HERMES_MCP_TRANSPORT=stdio` (既定、ローカル `.mcp.json` 用)
- `X_HERMES_MCP_TRANSPORT=streamable-http` (Phase 4 本番デプロイ用)

streamable-http / sse 時は `X_HERMES_MCP_TOKEN` 必須 (bearer 認証)。
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from .tools.fetch_tweet import fetch_tweet as _fetch_tweet
from .tools.fetch_tweet_chain import fetch_tweet_chain as _fetch_tweet_chain
from .tools.get_quote_tweets import get_quote_tweets as _get_quote_tweets
from .tools.get_trends import get_trends as _get_trends
from .tools.search_tweets import search_tweets as _search_tweets


_TRANSPORT = os.getenv("X_HERMES_MCP_TRANSPORT", "stdio")
_HTTP_TRANSPORTS = {"streamable-http", "sse", "http"}


def _build_auth():
    """HTTP 系トランスポート時のみ bearer auth を有効化。"""
    if _TRANSPORT not in _HTTP_TRANSPORTS:
        return None
    token = os.environ.get("X_HERMES_MCP_TOKEN")
    if not token:
        raise RuntimeError(
            "X_HERMES_MCP_TOKEN is required when X_HERMES_MCP_TRANSPORT is "
            f"{_TRANSPORT!r}. Set it to a long random string in .env."
        )
    from fastmcp.server.auth.providers.debug import DebugTokenVerifier
    return DebugTokenVerifier(
        validate=lambda t: t == token,
        client_id="x-hermes-mcp",
    )


mcp = FastMCP("X-HERMES-MCP", auth=_build_auth())


@mcp.tool
def fetch_tweet(url: str) -> dict:
    """Fetch a single X (Twitter) post and return its structured JSON.

    Source: Hermes Agent's x_search via Grok, billed against the X Premium Plus
    subscription quota (no per-call API charge). Response time: ~1.5 minutes.

    Output: tweet_id, url, author{username, display_name}, created_at, text,
    referenced_tweets (depth 1), metrics{likes, retweets, replies, quotes,
    bookmarks, views} as string integers, media (often empty), notes.

    Coverage limits vs. ConnectC2X fetch_tweet:
    - Single tweet only — use fetch_tweet_chain for multi-level expansion.
    - Media URLs not surfaced.
    - Dates are human-readable strings.

    Args:
      url: Canonical X post URL, e.g. https://x.com/xai/status/2055745332919808181
    """
    return _fetch_tweet(url)


@mcp.tool
def search_tweets(
    query: str,
    lang: str | None = None,
    since: str | None = None,
    until: str | None = None,
    from_user: str | None = None,
) -> dict:
    """Search X posts matching a keyword and return 5-10 structured results.

    Source: Hermes Agent's x_search via Grok. Response time: ~45-90 seconds.

    Output: query, filters, results[{tweet_id, url, author_username, created_at,
    text, metrics}], total_estimated, notes.

    Per-result metrics are usually null. For detailed metrics on a specific
    tweet, call fetch_tweet on its URL.

    Args:
      query: Keyword(s) to search.
      lang: Two-letter language code (e.g. "en", "ja") or None.
      since: Inclusive start date as YYYY-MM-DD or None.
      until: Inclusive end date as YYYY-MM-DD or None.
      from_user: Restrict to posts from a specific username (without @), or None.
    """
    return _search_tweets(
        query=query, lang=lang, since=since, until=until, from_user=from_user,
    )


@mcp.tool
def get_trends(region: str = "Japan", max_trends: int = 10) -> dict:
    """Return current X trends for a region with categories and evidence URLs.

    Source: Hermes Agent's x_search via Grok. Response time: ~3-4 minutes.

    Output: region, fetched_at, trends[{rank, topic, category, related_to,
    volume, evidence_url, note}], notes. Volume usually null.

    Args:
      region: Region name as a string ("Japan", "Tokyo", "Global", etc.).
      max_trends: Desired number, 1-20. Default 10.
    """
    return _get_trends(region=region, max_trends=max_trends)


@mcp.tool
def get_quote_tweets(source_url: str, max_quotes: int = 8) -> dict:
    """Sample 5-10 recent posts that quote-tweeted a specific source post.

    Source: Hermes Agent's x_search via Grok. Response time: ~2.5-3 minutes.

    Output: source_tweet_url, source_tweet_id, source_total_quotes,
    quotes[{tweet_id, url, author_username, created_at, text, language,
    metrics}], notes.

    Args:
      source_url: URL of the source post.
      max_quotes: Desired number of samples, 1-10. Default 8.
    """
    return _get_quote_tweets(source_url=source_url, max_quotes=max_quotes)


@mcp.tool
def fetch_tweet_chain(url: str, max_depth: int = 2) -> dict:
    """Fetch a tweet and its referenced posts up to `max_depth` levels in parallel.

    Output: root_url, root_tweet_id, max_depth, nodes[{depth, parent_tweet_id,
    data: fetch_tweet output}], errors[].

    Args:
      url: Canonical X post URL of the root.
      max_depth: Recursion depth, 1 or 2. Default 2. Hard cap at 2.
    """
    return _fetch_tweet_chain(url=url, max_depth=max_depth)


def main() -> None:
    if _TRANSPORT == "stdio":
        mcp.run()
        return
    host = os.getenv("X_HERMES_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("X_HERMES_MCP_PORT", "65432"))
    mcp.run(_TRANSPORT, host=host, port=port)


if __name__ == "__main__":
    main()
