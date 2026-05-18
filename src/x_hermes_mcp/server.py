"""X-HERMES-MCP サーバ — FastMCP エントリポイント。

トランスポートは env で切替:
- `X_HERMES_MCP_TRANSPORT=stdio` (既定、ローカル `.mcp.json` 用、認証なし)
- `X_HERMES_MCP_TRANSPORT=streamable-http` (Phase 4 本番デプロイ、OAuth 必須)

HTTP 系時の必須 env:
- `X_HERMES_MCP_BASE_URL`: サーバの公開 URL (例: `https://hermes.kitepon.dynv6.net`)
- `MCP_ADMIN_PASSWORD`: consent ページで使う master password
- `OAUTH_DB_PATH`: OAuth トークンを保存する SQLite パス
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from .tools.fetch_tweet import fetch_tweet as _fetch_tweet
from .tools.fetch_tweet_chain import fetch_tweet_chain as _fetch_tweet_chain
from .tools.get_quote_tweets import get_quote_tweets as _get_quote_tweets
from .tools.get_trends import get_trends as _get_trends
from .tools.search_tweets import search_tweets as _search_tweets
from .tools.x_search import x_search as _x_search


_TRANSPORT = os.getenv("X_HERMES_MCP_TRANSPORT", "stdio")
_HTTP_TRANSPORTS = {"streamable-http", "sse", "http"}
_oauth_provider = None  # 後で /consent ルート登録に再利用するため module-global


def _build_auth():
    """HTTP 系トランスポート時のみ OAuth provider を有効化。"""
    global _oauth_provider
    if _TRANSPORT not in _HTTP_TRANSPORTS:
        return None

    base_url = os.environ.get("X_HERMES_MCP_BASE_URL")
    if not base_url:
        raise RuntimeError(
            "X_HERMES_MCP_BASE_URL is required for HTTP transports "
            "(e.g., https://hermes.kitepon.dynv6.net)"
        )
    master_password = os.environ.get("MCP_ADMIN_PASSWORD")
    if not master_password:
        raise RuntimeError(
            "MCP_ADMIN_PASSWORD is required for HTTP transports — set a long "
            "random string in .env (used as the consent-page password)"
        )
    db_path = os.environ.get("OAUTH_DB_PATH", "/home/kite/.hermes/x_hermes_mcp_oauth.db")

    from .auth.provider import SqliteOAuthProvider
    _oauth_provider = SqliteOAuthProvider(
        base_url=base_url,
        master_password=master_password,
        db_path=db_path,
    )
    return _oauth_provider


mcp = FastMCP("X-HERMES-MCP", auth=_build_auth())


# ---------------- /consent route registration (HTTP only) ----------------

if _oauth_provider is not None:
    from .auth.pages import make_consent_handlers
    _consent_get, _consent_post = make_consent_handlers(_oauth_provider)

    @mcp.custom_route("/consent", methods=["GET"])
    async def consent_get(request):
        return await _consent_get(request)

    @mcp.custom_route("/consent", methods=["POST"])
    async def consent_post(request):
        return await _consent_post(request)


# ---------------- Tools ----------------
#
# Tool selection guide (use this to pick the right tool):
#
#   You have a SPECIFIC URL and want full details
#       → fetch_tweet              (single tweet, structured)
#       → fetch_tweet_chain        (tweet + its quoted posts, up to depth 2)
#
#   You want to find tweets MATCHING A KEYWORD or from a specific user
#       → search_tweets            (keyword + optional lang/date/from_user)
#
#   You have a SOURCE TWEET and want to see who QUOTED it
#       → get_quote_tweets         (5-10 quote samples + total quote count)
#
#   You want to know what's TRENDING right now in a region
#       → get_trends               (ranked trend list with evidence URLs)
#
#   Your need doesn't fit the above OR you want to combine angles
#       → x_search                 (raw, flexible, free-form natural language)
#
# All tools billed against X Premium Plus subscription quota (no separate
# API charge). All tools return a "source" field for provenance.


@mcp.tool
def x_search(
    query: str,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
) -> dict:
    """Free-form X research via xAI's `/responses` API — the flexible primitive.

    Use this when no specific wrapper fits, or when you want to combine
    multiple angles in one query. The response is xAI's native shape (natural
    language `answer` plus inline citation URLs), not a normalized schema.

    USE WHEN:
    - "What's the situation around <topic>?" — broad exploration
    - "Compare reactions to A vs B" — multi-angle / comparison queries
    - "Find <unusual pattern>" — anything that doesn't fit the wrappers
    - You want the AI side to control exactly what's asked / how to format

    PREFER SPECIFIC WRAPPERS WHEN APPLICABLE — they return ~3-5x fewer tokens
    by projecting to named fields:
    - fetch_tweet — you have a URL, want named fields
    - search_tweets — keyword search, want a result list
    - get_quote_tweets — quotes of a specific post
    - get_trends — current "what's hot" ranking
    - fetch_tweet_chain — multi-level quote tree

    Response time: ~30-45 sec.

    Output: { success, provider, credential_source, tool, model, query, answer
    (natural language, may include JSON if you asked), citations,
    inline_citations[{url, title, start_index, end_index}] }.

    Args:
      query: Natural-language search query (required). For structured output,
             you can ask for JSON inside the query (e.g., "return JSON: {...}").
      allowed_x_handles: Whitelist of X usernames (max 10). Mutually exclusive
                         with `excluded_x_handles`.
      excluded_x_handles: Blacklist of X usernames (max 10).
      from_date: Inclusive period start, YYYY-MM-DD.
      to_date: Inclusive period end, YYYY-MM-DD.
      enable_image_understanding: Have Grok describe attached photos / GIFs
                                   so visual content appears in `answer`.
      enable_video_understanding: Have Grok describe attached videos.
    """
    return _x_search(
        query=query,
        allowed_x_handles=allowed_x_handles,
        excluded_x_handles=excluded_x_handles,
        from_date=from_date,
        to_date=to_date,
        enable_image_understanding=enable_image_understanding,
        enable_video_understanding=enable_video_understanding,
    )


@mcp.tool
def fetch_tweet(url: str) -> dict:
    """Get a single X (Twitter) post's full details in normalized JSON.

    USE WHEN:
    - "Tell me about this post: <URL>"
    - "What are the engagement metrics on <URL>?"
    - "Who does <URL> quote? What was the original?"
    - You have a SPECIFIC URL and want named fields (author, metrics, etc.)

    DON'T USE FOR:
    - Multi-level quote tree → use `fetch_tweet_chain`.
    - "What's the discussion around this post?" → use `get_quote_tweets`
      (for quotes) or `x_search` (for broad reactions including replies).
    - "Find posts about <topic>" without a URL → use `search_tweets`.

    Backend: P7 V4 — calls xAI's x_search once with a JSON-output query,
    then Python parses and maps to the schema below. Response ~25-45 sec,
    deterministic, ~150 tokens output (vs ~400-500 for equivalent x_search).

    Output schema (ConnectC2X-compatible):
      tweet_id, url,
      author { username, display_name },
      created_at (ISO 8601 when xAI provides it, e.g. "2026-05-16T20:20:55Z"),
      text (t.co URLs expanded),
      referenced_tweets[] (depth 1, full tweet_id + author_username + text for
                          the quoted post),
      metrics { likes, retweets, replies, quotes, bookmarks, views } as exact
              integer strings,
      media[] { type, url:null, alt_text=Grok's visual description },
      notes (null — synthesis-era field, kept for schema compatibility),
      source: "x_search_raw_v4".

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
    """Search recent X posts by keyword and get a structured list of 5-10 results.

    USE WHEN:
    - "Find recent posts about <topic>"
    - "What did @<user> say about <topic> in the last week?"
    - "Show me <lang> posts mentioning <keyword>"
    - You want a LIST of candidate tweets to inspect / pick from.

    DON'T USE FOR:
    - You already have one specific URL → use `fetch_tweet`.
    - You want quotes of a specific post → use `get_quote_tweets`.
    - You want current trending topics (no specific keyword) → use `get_trends`.

    Per-result metrics are often null or 0 (X search page doesn't always show
    counts). For exact metrics on a specific result, follow up with
    `fetch_tweet(url)`.

    Backend: P7 V4 — raw x_search + Python parser. Response ~45-90 sec.

    Output: { query, filters, results[ each: tweet_id, url, author_username,
    author_display_name, created_at, text, metrics{likes, retweets, replies} ],
    total_estimated, notes, source: "x_search_raw_v4" }.

    Args:
      query: Keyword(s) to search.
      lang: Two-letter language code (e.g. "en", "ja") or None.
      since: Inclusive period start, YYYY-MM-DD, or None.
      until: Inclusive period end, YYYY-MM-DD, or None.
      from_user: Restrict to posts from one specific username (without @),
                 or None. Internally routed to x_search's allowed_x_handles.
    """
    return _search_tweets(
        query=query, lang=lang, since=since, until=until, from_user=from_user,
    )


@mcp.tool
def get_trends(region: str = "Japan", max_trends: int = 10) -> dict:
    """Get current X trending topics for a region, with categories and evidence URLs.

    USE WHEN:
    - "What's trending in Japan right now?"
    - "What are people talking about today?"
    - You want exploration — no specific topic in mind, just "current chatter".

    DON'T USE FOR:
    - Specific topic deep-dive → use `search_tweets` or `x_search`.
    - Engagement metrics on one tweet → use `fetch_tweet`.

    After identifying a trend you care about, follow up with `search_tweets`
    (for a list) or `x_search` (for free-form analysis) on that trend name.

    Backend: P7 V4. Response ~80-90 sec (Grok looks up an evidence URL per
    trend). Volume (post count) is usually null — X doesn't expose it.

    Output: { region, fetched_at (YYYY-MM-DD), trends[ each: rank, topic,
    category (game / idol / music / news / politics / sports / entertainment /
    tv / tech / business / people / other), related_to, volume, evidence_url,
    note ], notes, source: "x_search_raw_v4" }.

    Args:
      region: Region name as a string ("Japan", "Tokyo", "Global",
              "United States", etc.).
      max_trends: Desired number, 1-20. Default 10. Actual count may be lower.
    """
    return _get_trends(region=region, max_trends=max_trends)


@mcp.tool
def get_quote_tweets(source_url: str, max_quotes: int = 8) -> dict:
    """Sample recent posts that quote-tweeted a specific source post.

    USE WHEN:
    - "How are people responding to this announcement: <URL>?"
    - "Show me reactions / hot takes on <URL>"
    - "What are the quote tweets saying?"

    Source author's own follow-up posts are automatically excluded (via
    `excluded_x_handles` on x_search).

    DON'T USE FOR:
    - Replies (different from quotes) → use `x_search` with query like
      "replies to <URL>".
    - The source post's own details → use `fetch_tweet`.

    Sample only — returns 5-10 most recent. Won't enumerate hundreds. The
    response includes `source_total_quotes` (total quote count on the source
    post) so you know how representative the sample is.

    Backend: P7 V4. Response ~80-90 sec.

    Output: { source_tweet_url, source_tweet_id, source_total_quotes,
    quotes[ each: tweet_id, url, author_username, author_display_name,
    created_at, text, language, metrics{likes, retweets, replies} ], notes,
    source: "x_search_raw_v4" }.

    Args:
      source_url: URL of the source post whose quotes you want.
      max_quotes: Desired number of samples, 1-10. Default 8.
    """
    return _get_quote_tweets(source_url=source_url, max_quotes=max_quotes)


@mcp.tool
def fetch_tweet_chain(url: str, max_depth: int = 2) -> dict:
    """Recursively fetch a tweet and the posts it quotes (up to max_depth), in parallel.

    USE WHEN:
    - "Walk through this quote chain: <URL>"
    - "I want this post AND the post it quotes (and beyond)"
    - You need multi-step context spanning linked tweets.

    DON'T USE FOR:
    - A single tweet with no recursion → use `fetch_tweet` directly (faster).
    - Reactions to a post (quotes OF it, not quotes BY it) → use
      `get_quote_tweets`.

    Implementation: starts with `fetch_tweet(url)`, then for each tweet_id in
    `referenced_tweets`, builds the URL and recursively calls `fetch_tweet`
    in parallel (max 4 workers). Failures are captured per-node in `errors[]`
    so one broken branch doesn't abort the whole chain.

    Response time scales with depth: ~30s × max_depth + parallel fan-out cost.
    At max_depth=2 with typical fan-out: 60-120 sec.

    Output: { root_url, root_tweet_id, max_depth, nodes[] (flat list with
    each: depth, parent_tweet_id, data = fetch_tweet output), errors[] (per-
    node failures: depth, parent_tweet_id, url, error) }.

    Args:
      url: Canonical X post URL of the root.
      max_depth: Recursion depth, 1 or 2. Default 2. Hard cap at 2 — deeper
                 chains aren't supported by design (diminishing returns and
                 response time explosion).
    """
    return _fetch_tweet_chain(url=url, max_depth=max_depth)


def main() -> None:
    if _TRANSPORT == "stdio":
        mcp.run()
        return
    host = os.getenv("X_HERMES_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("X_HERMES_MCP_PORT", "65432"))
    # stateless_http=True: don't keep per-session state on the server, so a
    # container restart doesn't make every connected client error with
    # "Session not found". Our tools are all request/response — we don't use
    # server-initiated notifications, which is the only thing this disables.
    mcp.run(_TRANSPORT, host=host, port=port, stateless_http=True)


if __name__ == "__main__":
    main()
