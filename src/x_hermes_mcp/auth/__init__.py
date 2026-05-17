"""OAuth 2.1 server for X-HERMES-MCP — single-user, SQLite-backed.

FastMCP の `OAuthProvider` を継承して `/authorize` `/token` `/register`
`/revoke` `/.well-known/oauth-*` の SDK 自動生成ルートを得る。`/consent` の
GET+POST は別途 `pages.py` の custom_route で組み込む。

ip-mcp (同作者) の SqliteOAuthProvider パターンをベースに移植。
"""
