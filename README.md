# X-HERMES-MCP

MCP server that wraps [Hermes Agent](https://github.com/NousResearch/hermes-agent)'s
`x_search` capability behind a clean tool surface. Personal-use X (Twitter)
research powered by Grok-4.x, billed against your existing **X Premium Plus**
subscription quota (no per-call API charge).

Built to be reachable from Claude Code, Claude.ai, Codex CLI, and ChatGPT
Connectors via OAuth 2.1 over HTTPS.

## Status

- Phase 1–4 complete: prompts authored, MCP server built, deployed on home
  server behind Caddy + DDNS.
- Phase 6 complete: OAuth 2.1 provider (SQLite-backed, master-password consent)
  for Claude.ai / ChatGPT discovery compatibility.
- Phase 7 partial: `x_search` raw tool added — direct call to xAI's Responses
  API, bypassing Grok-4.3 synthesis. ~30s vs ~90s for wrapped tools.

See [`DOCS/plan.md`](DOCS/plan.md) for the full state-of-the-world.

## Tools exposed

| Tool | Path | Response | Notes |
|---|---|---|---|
| `x_search` | Raw xAI Responses API | ~30-45 s | Fastest. Returns raw `{answer, citations, ...}` |
| `fetch_tweet` | Grok-mediated wrap | ~90 s | Schema-conforming single-tweet structure |
| `search_tweets` | Grok-mediated wrap | ~45-90 s | Keyword search → tweet list |
| `get_trends` | Grok-mediated wrap | ~3-4 min | Region → trends with evidence URLs |
| `get_quote_tweets` | Grok-mediated wrap | ~2.5 min | Source tweet → quote sample |
| `fetch_tweet_chain` | Composition | ~3-5 min | Multi-depth quote graph |

The `x_search` (raw) tool is the fast path; the others apply Grok-4.3
synthesis to fit a ConnectC2X-compatible schema. See
[`DOCS/prompts/`](DOCS/prompts/) for the synthesized prompts.

## Architecture

```text
[MCP client]                  [home server, 192.168.1.2]
  Claude Code  ────HTTPS────►  Caddy (TLS, hermes.kitepon.dynv6.net)
  Claude.ai    ────HTTPS────►       │
  Codex CLI    ────HTTPS────►       ▼
  ChatGPT      ────HTTPS────►  X-HERMES-MCP container (FastMCP, port 65432)
                                    │
                                    ▼
                              Hermes Agent venv (bind-mounted ~/.hermes/)
                                    │
                                    ▼
                              xAI Responses API / Grok-4.3
                              (billed against X Premium Plus)
```

## Project rules

Read [`CLAUDE.md`](CLAUDE.md) before contributing — it lists the absolute
rules (secrets handling, billing-path discipline, coding discipline).

## License

Personal project. No license declared — treat as proprietary unless / until
this changes.
