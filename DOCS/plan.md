# Hermes Agent MCP ラッパー計画

最終更新: 2026-05-18

## ゴール

X Premium Plus サブスクリプション (¥3,400/月) 以外の追加課金を発生させずに、X 検索系の MCP サーバ (`X-HERMES-MCP`) を自分用に構築する。最終的に外出先の Claude / Codex から呼び出せるところまで持っていく。

達成基準:

- Hermes 経由の Grok 検索が、自分用 MCP として MCP クライアントから自然に呼べる
- AI が X 関連の検索をする時、自然に Hermes 経路を優先選択する
- 構造化 API データが必要な 3 機能は ConnectC2X 直接利用で別経路に切り分けられている
- 外出先のノートからも、自宅サーバ越しに同じツールが呼べる
- **ConnectC2X 本体のコード / 説明文は無変更**

## アーキテクチャ方針 (2026-05-17 決定)

| 用途 | 道具 | コスト |
|---|---|---|
| Grok 経路の検索・要約 (5 機能) | **X-HERMES-MCP** (本プロジェクトで構築) | 0 円 (Premium Plus 内) |
| 構造化 API データ (3 機能) | **既存 ConnectC2X MCP に直接接続** | X 開発者 pay-per-use 課金 (どうせ発生) |
| `xurl` の登録 | **行わない** (pay-per-use 残高を保護) | 0 円 |

クライアント側 (Claude / Codex / ChatGPT) で **ConnectC2X の重複ツールを無効化** することで、AI に Hermes 経路を自然に選ばせる。ConnectC2X 自体は無変更。

## 確定事実 (2026-05-17 実測)

| 項目 | 状態 |
|---|---|
| Hermes Agent v0.14.0 | `/home/kite/.hermes/` にインストール済み |
| xAI Grok OAuth (`xai-oauth-oauth-1`) | 認証済み、`logged in` |
| 既定モデル | `grok-4.3` (provider: `xai-oauth`) |
| `x_search` ツール | CLI で動作確認済み、内部で `grok-4.20-reasoning` 使用 |
| `XAI_API_KEY` | 未設定 (追加課金経路ゼロ) |
| `xurl` 登録 | **行わない方針** (本日決定) |
| X 開発者プラットフォーム | **pay-per-use 課金モデル**、残高 $7.07 (本日発見) |
| Web ダッシュボード | `127.0.0.1:9119` で起動可能 (`hermes dashboard --tui`) |

## 機能カバレッジ最終方針

| ConnectC2X ツール | 担当 | 備考 |
|---|---|---|
| `fetch_tweet` (URL → 本文・metrics) | **X-HERMES-MCP** | metrics は丸め値 (5.2K, 1.58M 形式) |
| `search_tweets` (キーワード) | **X-HERMES-MCP** | URL リスト + 必要なら N+1 で本文化 |
| `search_tweets_all` (全期間) | **X-HERMES-MCP** | x_search の期間指定で代替 |
| `get_trends` (地域別トレンド) | **X-HERMES-MCP** | x_search 多段呼び出し |
| `get_quote_tweets` | **X-HERMES-MCP** | サンプル取得 |
| `count_tweets` (時系列件数) | **ConnectC2X 直接利用** | x_search では取得不可 |
| `get_retweeted_by` (RT 者列挙) | **ConnectC2X 直接利用** | x_search では取得不可 |
| `get_list_tweets` (リスト由来) | **ConnectC2X 直接利用** | x_search では取得不可 |

## 既存資産・参考

- `/home/kite/projects/ConnectC2X/src/tools/` — 各機能の現行実装。引数・出力形のリファレンス
- `/home/kite/.hermes/hermes-agent/skills/social-media/xurl/SKILL.md` — xurl スキル定義 (採用しないが API v2 仕様参考として残す)
- `/home/kite/.claude/plans/mcp-premium-swirling-bear.md` — 起点となった置き換え想像案

## x_search 詳細パラメータ仕様 (Hermes 経路、xAI ドキュメント由来)

プロンプト V3 で活用している x_search の正式パラメータ:

| パラメータ | 型 | 用途 |
|---|---|---|
| `query` | string (必須) | 自然言語検索クエリ |
| `allowed_x_handles` | list[str] (max 10) | 検索対象アカウント |
| `excluded_x_handles` | list[str] (max 10) | 除外アカウント |
| `from_date` | YYYY-MM-DD | 期間下限 |
| `to_date` | YYYY-MM-DD | 期間上限 |
| `enable_image_understanding` | bool | 画像内容理解 (alt_text に説明が入る) |
| `enable_video_understanding` | bool | 動画内容理解 |

x_search の返り値構造:

- `answer` — Grok 合成の自然文回答
- `citations` — 通常空 (xAI 側で埋まらないことが多い)
- `inline_citations` — `[{url, title, start_index, end_index}]`
- `credential_source` — `xai-oauth` または `xai`
- `model` — `grok-4.20-reasoning`
- `query` — 実際に投げられたクエリ
- `provider` — `xai`
- `tool` — `x_search`
- `success` — bool

これらをプロンプトで明示的に Grok に渡させることで、自然言語に依存しない構造化呼び出しになる。プロンプト V3 で `enable_image_understanding=true` を指示したところ、fetch_tweet の `media[].alt_text` が空ではなく Grok の画像解釈で埋まるようになった (V2 まで「常に空、構造的限界」と書いていた箇所が改善)。

---

## Phase 1 — Hermes ツール疎通 (✓ 完了)

- [x] Hermes Agent インストール
- [x] xAI Grok OAuth 認証
- [x] 既定モデルを `grok-4.3` に設定
- [x] `x_search` ツールが CLI で動作することを確認
- [x] CLI 既定ツールセットに `x_search` を追加
- [x] xurl 不採用方針確定 (pay-per-use 残高を Hermes 経路に流さない)

## Phase 2 — プロンプトで Hermes 5 機能を構造化

各機能について:

- (a) 厳密スキーマを与えた `hermes -z` プロンプトを書く
- (b) ConnectC2X 出力と並べて比較する
- (c) `DOCS/prompts/<tool_name>.md` に保存する

実装する 5 機能 (x_search ベース):

- [x] `fetch_tweet` 相当 — URL → 構造化 JSON (本文・著者・日付・metrics・引用 ID 言及) — [DOCS/prompts/fetch_tweet.md](prompts/fetch_tweet.md), 応答 ~2 分、media のみ未取得
- [x] `search_tweets` 相当 — キーワード → ツイートリスト構造化 — [DOCS/prompts/search_tweets.md](prompts/search_tweets.md), 応答 ~46 秒、5-10 件取得、metrics は per-result null
- [x] `search_tweets_all` 相当 — 全期間検索 — `search_tweets` プロンプトを `since` / `until` 引数で長期間カバーする形で対応 (Grok 経路には Pro 区分なし)。MCP 化時に別名で公開するかは Phase 3 設計判断
- [x] `get_trends` 相当 — 地域指定 → トレンドリスト構造化 (証拠 URL 付き) — [DOCS/prompts/get_trends.md](prompts/get_trends.md), 応答 ~3.5 分、9 件取得、volume のみ取得不可
- [x] `get_quote_tweets` 相当 — ツイート ID → 引用一覧構造化 — [DOCS/prompts/get_quote_tweets.md](prompts/get_quote_tweets.md), 応答 ~2.7 分、5-10 件サンプル、source の引用総数も取れる

実装しない 3 機能 (ConnectC2X 直接利用):
- `count_tweets` (時系列件数)
- `get_retweeted_by` (RT 者列挙)
- `get_list_tweets` (リスト由来)

検証項目:
- 出力が JSON Schema に準拠するか
- 1 回の呼び出しで完結するか、N+1 呼び出しが必要か
- 平均応答時間 / Grok 推論時間
- Grok サブスク quota への影響観測

## Phase 3 — X-HERMES-MCP として MCP 化

### サーバ識別子

`X-HERMES-MCP` — `.mcp.json` / `config.toml` / Connectors UI 上での名称

### 設計判断 (2026-05-17 確定)

- **採用**: 自作 Python MCP サーバ (FastMCP)
- **不採用**: `hermes mcp serve` (メッセージング会話ブリッジ専用、汎用ツール公開には使えない)
- **理由**: FastMCP が Hermes に同梱済み (`optional-skills/mcp/fastmcp/`)、`api_wrapper.py` テンプレが流用可能、stdio/HTTP 両対応で Phase 3/4 を同じコードで通せる
- **内部呼び出し方式**: 各 MCP ツール関数 → subprocess で `hermes -z "..."` を起動 → 標準出力の JSON をパースして返す
- **プロンプトテンプレ管理**: `DOCS/prompts/*.md` から本文を抽出するローダ層で吸収 (テンプレ修正だけで挙動を調整できる)

### 実装

- [x] `hermes mcp` サブコマンドの仕様調査 — メッセージング専用、不採用確定
- [x] 設計判断: FastMCP 自作ラッパに決定
- [x] プロジェクト構成決定 (`uv` + `pyproject.toml`、`src/x_hermes_mcp/` レイアウト)
- [x] `src/x_hermes_mcp/hermes_runner.py` — subprocess ラッパ (タイムアウト・JSON パース・例外型)
- [x] `src/x_hermes_mcp/prompt_loader.py` — `DOCS/prompts/*.md` から `## 採用プロンプト` 直下のコードフェンスを抽出 + `{VAR}` 置換
- [x] `src/x_hermes_mcp/tools/fetch_tweet.py` — MVP 1 機能
- [x] `src/x_hermes_mcp/tools/search_tweets.py` / `get_trends.py` / `get_quote_tweets.py`
- [x] `src/x_hermes_mcp/tools/fetch_tweet_chain.py` — 上位コンポジション (max_depth=2 既定、ThreadPoolExecutor で並列 fan-out、エラーはノード単位で収集)
- [x] `src/x_hermes_mcp/server.py` — 5 ツール (`fetch_tweet` / `search_tweets` / `get_trends` / `get_quote_tweets` / `fetch_tweet_chain`) を FastMCP に登録
- [x] サーバ単体での疎通確認 (`mcp.list_tools()` で 5 ツール、`call_tool('fetch_tweet')` で end-to-end 通った、応答 1 分 25 秒、JSON 出力 9 キー揃う)
- [x] プロジェクト `.mcp.json` に `X-HERMES-MCP` を `uv run x-hermes-mcp` (stdio) で登録
- [x] Claude Code 再起動 → 5 ツールが MCP 経由で可視確認 (2026-05-17)
- [x] Claude Code から `fetch_tweet` 呼び出し → end-to-end 動作確認 (応答 ~90 秒、JSON 9 キー揃う、metrics 正確値、`link_card` も検出)

### 公開ツール一覧 (6 ツール)

**Raw 経路** (P7 で追加、xAI Responses API 直接呼び出し、Grok-4.3 synthesis 無し):

- `x_search` — 検索 + 構造化応答。**応答 30〜45 秒** (最速)、出力は xAI 生構造体
  - パラメータ: `query` (必須), `allowed_x_handles`, `excluded_x_handles`, `from_date`, `to_date`, `enable_image_understanding`, `enable_video_understanding`
  - 戻り: `{success, provider, credential_source, tool, model, query, answer, citations, inline_citations}`

**Synthesized 経路** (Phase 2-3 で作った Grok 経由スキーマ整形ツール):

- `fetch_tweet` — URL → 単一ツイート ConnectC2X 互換 schema (V3、image understanding 有効)
- `search_tweets` — キーワード → ツイートリスト構造化 (V3、`allowed_x_handles`/`from_date`/`to_date` を構造化パラメータで渡す)
- `get_trends` — 地域 → トレンドリスト構造化 (V1)
- `get_quote_tweets` — ツイート URL → 引用ツイート一覧 (V2、`excluded_x_handles=[source_author]` で自己除外)
- `fetch_tweet_chain` — 上位コンポジション、URL + `max_depth`(1〜2) → ツリー構造
  - 内部実装: root を `fetch_tweet` で取得 → `referenced_tweets[*].tweet_id` を並列展開
  - 最大応答時間目安: ~4 分 (depth 2、ファンアウト並列処理)
  - ConnectC2X の 5 階層自動展開には合わせない (実時間の代償が大きすぎる)

**使い分けガイド**:

- 高速・確実・構造化されてれば良い → **`x_search` (raw)**
- ConnectC2X 互換スキーマで使い回したい → `fetch_tweet` 等の synthesized
- 引用ツリー深掘り → `fetch_tweet_chain`

### クライアント側ツール優先制御

ConnectC2X 本体は無変更。**クライアント側で重複ツールを無効化** する:

**Claude Code** (`~/.claude/settings.json` または プロジェクト `.claude/settings.json`):

```json
{
  "permissions": {
    "deny": [
      "mcp__connectc2x__search_tweets",
      "mcp__connectc2x__search_tweets_all",
      "mcp__connectc2x__fetch_tweet",
      "mcp__connectc2x__fetch_timeline",
      "mcp__connectc2x__get_quote_tweets",
      "mcp__connectc2x__get_trends"
    ]
  }
}
```

→ ConnectC2X 側で 5 機能を deny。残る 3 機能 (`count_tweets` / `get_retweeted_by` / `get_list_tweets`) は有効のまま。

**Codex CLI** (`~/.codex/config.toml`):

```toml
[mcp_servers.connectc2x]
url = "..."
tools_deny = [
  "search_tweets", "search_tweets_all", "fetch_tweet",
  "fetch_timeline", "get_quote_tweets", "get_trends"
]
```

**ChatGPT (Custom GPT / Connectors)**:

- Connectors UI で ConnectC2X 側の上記 6 ツールのトグルを OFF

### 検証

- [ ] Claude Code で X 検索系の質問を投げ、AI が `X-HERMES-MCP` 側を選ぶことを確認
- [ ] 構造化データ要求 (RT 者リストなど) で ConnectC2X 側が選ばれることを確認
- [ ] 両者の使い分けが自然に成立しているか観察

## Phase 4 — ホームサーバ (192.168.1.2) デプロイ

### デプロイ設計 (2026-05-17 確定)

| 項目 | 採用 | 既存パターン参照 |
|---|---|---|
| 外部到達 | DDNS サブドメイン + 共通 Caddy (TLS 終端) | `~/license-server/Caddyfile` 一元管理 |
| サブドメイン | `hermes.kitepon.dynv6.net` | 将来 Phase 5+ の親ドメインとしても使う |
| 認証 | **OAuth 2.1 (SQLite-backed、master password consent)** ← P6 で bearer から移行 | ip-mcp パターン踏襲 |
| トランスポート | streamable-http | FastMCP 標準 |
| ポート | 65432 (192.168.1.2 にバインド) | 既存クラスタ全部から離れた 6 万番台 |
| ホスト構成 | Docker compose (`~/X-HERMES-MCP/`) | `~/ip-mcp/` を踏襲 |
| Hermes 同梱 | host の `~/.hermes/` を **同一パスで** bind mount | venv の絶対パス shebang のため |
| LAN マシン側 | `/etc/hosts` に `192.168.1.2 hermes.kitepon.dynv6.net` を追記 | ルータがヘアピン NAT 非対応 |

### Caddy 設定 (`~/license-server/Caddyfile` の末尾に追記)

```caddy
hermes.kitepon.dynv6.net {
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        -X-Powered-By
        -Server
    }
    reverse_proxy 192.168.1.2:65432 {
        flush_interval -1
    }
}
```

反映: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`

### デプロイ手順

- [x] 設計確定 (2026-05-17)
- [x] 本リポジトリに Docker 構成 (`Dockerfile` / `docker-compose.yml` / `docker-compose.override.yml` / `.env.example` / `.dockerignore`) を追加
- [x] `src/x_hermes_mcp/server.py` を transport + auth env 駆動に改修 (stdio / streamable-http 両対応)
- [x] `src/x_hermes_mcp/hermes_runner.py` を `HERMES_BIN` env override 対応に改修
- [x] GitHub repo `kitepon-rgb/HermesAgent` (public) 作成、リポジトリを host (`~/HermesAgent/`) に clone
- [x] host の `~/HermesAgent/.env` を生成し `X_HERMES_MCP_TOKEN` をセット (chmod 600)
- [x] host に Hermes Agent をインストール (`install.sh --skip-setup --skip-browser`)
- [x] WSL から host へ OAuth state (`~/.hermes/auth.json`) を scp、`xai-oauth: logged in` 確認
- [x] `docker compose up -d --build` で起動
- [x] container の bind mount を `/home/kite/.local/share/uv` 追加 (venv shebang 解決)
- [x] container 環境に `HOME=/home/kite` を追加 (UID 1000 で起動時の `~` 解決)
- [x] `~/license-server/Caddyfile` に `hermes.kitepon.dynv6.net` ブロック追記、Caddy reload
- [x] LAN マシン (WSL) の `/etc/hosts` に `192.168.1.2 hermes.kitepon.dynv6.net` 追記
- [x] 疎通確認 (`curl -H "Authorization: Bearer $TOKEN" https://hermes.kitepon.dynv6.net/mcp` → 200)
- [x] Claude Code の `.mcp.json` を HTTP リモート版に書き換え (token は chat 非表示で scp 経由)、再起動して接続確認
- [x] **end-to-end 動作確認 (2026-05-18)**: `mcp__X-HERMES-MCP__fetch_tweet` 経由で実 X 投稿の構造化 JSON が返ることを確認
- [x] 既存 ConnectC2X (同マシン稼働中) との同居動作を確認 (ポート 65432 vs 3001、Caddy 別サブドメイン、衝突なし)

---

## Phase 6 — OAuth 2.1 化 (Claude.ai / ChatGPT 対応、2026-05-18 完了)

### 背景

Phase 4 の static bearer 認証は Claude Code / Codex CLI からは使えるが、**Claude.ai のコネクタは OAuth ディスカバリ必須** で受け入れない:

- 試行ログ: `POST /mcp` → 401 → `/.well-known/oauth-protected-resource` → 404 → `/.well-known/oauth-authorization-server` → 404 → `/register` → 404 → 「Couldn't reach the MCP server」表示
- ChatGPT Connectors も同様に OAuth ベースのみ

### 設計判断

- ip-mcp の `auth/` パターン (SQLite-backed `OAuthAuthorizationServerProvider` 継承) を **同作者作品として参考にして移植**
- FastMCP 3.x の `OAuthProvider` を継承することで `/authorize` `/token` `/register` `/revoke` `/.well-known/oauth-*` の SDK 自動ルートを得る
- master password 1 個でブラウザ consent → トークン発行のシンプルなフロー (single user 想定)

### OAuth 実装

- [x] `src/x_hermes_mcp/auth/provider.py` — `SqliteOAuthProvider` 実装 (DCR / auth_code / access_token / refresh_token 4 表、aiosqlite で async)
- [x] `src/x_hermes_mcp/auth/pages.py` — `/consent` GET+POST ハンドラ (master password 入力フォーム)
- [x] `server.py` — transport が HTTP 系の時に OAuth provider をマウント、`@mcp.custom_route("/consent")` で consent ページ登録
- [x] `.env.example` 更新: `MCP_ADMIN_PASSWORD`, `X_HERMES_MCP_BASE_URL`, `OAUTH_DB_PATH` を追加、`X_HERMES_MCP_TOKEN` を廃止
- [x] host で master password 生成 (`secrets.token_urlsafe(32)`)、`.env` chmod 600 で配置
- [x] OAuth DB (`/home/kite/.hermes/x_hermes_mcp_oauth.db`) は bind mount される `~/.hermes/` 配下なのでコンテナ再生成でトークン永続
- [x] container rebuild → discovery エンドポイント 200 OK + DCR `/register` 201 確認

### クライアント側 OAuth 接続手順

1. `.mcp.json` から `Authorization: Bearer ...` ヘッダを削除 (URL だけにする)
2. Claude Code / Claude.ai / ChatGPT 再起動
3. 初回接続時にブラウザで `/consent?session_id=...` が開く → master password 入力
4. 認可コード → トークン交換 → 以降は refresh で自動更新

---

## Phase 7 — Raw x_search 直接呼び出し (Grok-4.3 synthesis バイパス、2026-05-18 P1 完了)

### 動機

既存 5 ツールはすべて `hermes -z` 経由で **Grok-4.3 (oneshot)** を起動し、その内部で `x_search` を呼んでいた。実態:

- データソースは x_search のみ
- Grok-4.3 の役割は「`x_search.answer` の自然文を ConnectC2X 互換 schema に整形する」だけ
- このラップで 60〜120 秒の応答時間 + synthesis 揺らぎを払っている

### Raw 化の方針

- `tools.x_search_tool()` は通常の Python 関数で、xAI `/responses` エンドポイントを直接叩いて構造体を返す
- これを **subprocess で Hermes Python 経由で呼ぶ** ことで Grok-4.3 ラップを完全に省ける
- 応答 30〜45 秒、決定的出力、Grok-4.3 quota 消費ゼロ (内部の grok-4.20-reasoning 分のみ)

### Raw 実装 (P1)

- [x] `src/x_hermes_mcp/x_search_client.py` — `call_x_search(...)`、Hermes Python に subprocess してパラメータを JSON stdin で渡し、結果を JSON stdout で受ける
- [x] `src/x_hermes_mcp/tools/x_search.py` — 上記の薄い MCP 用ラッパ
- [x] `server.py` に `x_search` を 6 番目のツールとして登録
- [x] ローカル実測: 35 秒、19 件 inline_citations、xAI 生構造体
- [x] container でも subprocess 経由で `tools.x_search_tool` import 可能を確認、デプロイ

### P2 完了 (2026-05-18): fetch_tweet バックエンド置換

- [x] x_search に「JSON で全項目返せ」と頼むクエリテンプレを設計、ISO 8601 / exact integer / 引用ツイート完全展開が単発で取れることを実測
- [x] `tools/fetch_tweet.py` を raw + balanced-brace JSON extractor + Python マッパに置換
- [x] スキーマ互換性確保 (metrics は str 化、`source: x_search_raw_v4` provenance タグ追加)
- [x] ローカル実測: **27.7 秒** (V3 ~90 秒の 3.3x 高速、metrics 常に正確値、created_at が ISO 8601 timestamp)
- [x] 6 ツール登録のままサーバ起動確認、デプロイ
- [x] `DOCS/prompts/fetch_tweet.md` を「V3 は非アクティブ・歴史記録」とマーク

### P3 完了 (2026-05-18): 残り 3 ツールも raw 化

- [x] `src/x_hermes_mcp/_parse.py` を新設し `extract_json` / `stringify_metrics` / `tweet_id_from_url` / `author_from_url` を共有ヘルパとして集約 (4 ツールから import)
- [x] `tools/search_tweets.py` を置換 (V4): `from_user` を `allowed_x_handles`、`since/until` を `from_date/to_date` として x_search の構造化パラメータに直接マップ。ローカル実測 82 秒、10 件取得、ISO 8601 タイムスタンプ、display_name 取得確認
- [x] `tools/get_quote_tweets.py` を置換 (V4): URL から `source_author` を抽出して `excluded_x_handles=[source_author]` を渡し自己投稿を除外。ローカル実測 86 秒、`source_total_quotes=465` 取得、10 件、言語検出
- [x] `tools/get_trends.py` を置換 (V4): JSON で trend list を返させて Python マップ。ローカル実測 86 秒、10 件、ランク/カテゴリ/証拠 URL 揃う
- [x] `DOCS/prompts/*.md` を「P3 で raw に置換、本ファイルは歴史記録」とマーク
- [x] サーバ起動確認 (6 ツール登録のまま)

### P4 自動完了 (2026-05-18): fetch_tweet_chain は自動的に高速化

`fetch_tweet_chain` は `fetch_tweet` を内部で再帰呼び出しする合成ツールなので、P2 で `fetch_tweet` バックエンドが raw 化された時点で自動的に raw ベース動作になった。実装コードの変更は不要。

- [x] 実測: depth 2 / fan-out 1 で **60.6 秒** (V3 baseline 3〜4 分 ≒ 3〜4 倍速)
- [x] 並列性そのまま、エラー時のノード単位収集動作も継続

### Phase 7 完走時点での到達点 (実測ベース)

| ツール | V3 baseline | **V4 raw** | 短縮率 |
|---|---|---|---|
| `fetch_tweet` | ~90 秒 | **27.7 秒** | 3.3x |
| `search_tweets` | ~45-90 秒 | **82 秒** | 同等 |
| `get_quote_tweets` | ~160 秒 | **86 秒** | 1.9x |
| `get_trends` | ~210 秒 | **86 秒** | 2.4x |
| `fetch_tweet_chain` (depth 2) | ~180-300 秒 | **60.6 秒** | 3〜5x |

副次効果:

- 出力決定性 (synthesis 揺らぎ消滅)、ISO 8601 timestamp、metrics は exact integer
- Grok-4.3 quota 消費ほぼゼロ (内部 grok-4.20-reasoning 分のみ)
- 各レスポンスに `source: "x_search_raw_v4"` provenance タグで追跡可能

---

## Phase 8 — 接続安定化 (refresh grace + stateless HTTP、2026-05-18 完了)

### 顕在化した不具合 (運用後切り分け)

Phase 6 で OAuth を立ててから、claude.ai / ChatGPT 双方で「使おうとしたら 401 / Connection failed」を断続的に踏んだ。実ログから 2 系統の独立した不具合と切り分け:

1. **リフレッシュトークン rotation のレース**
   - `exchange_refresh_token` が旧トークンを即削除 → クライアントが新トークンを通信断やレースで保存し損ねた時、次の更新で旧トークンを再送 → サーバは無効と判定 → クライアントは資格情報破棄 → 新規 DCR → consent ページの master password 再入力が必要
   - 実ログ: 約 11 時間で claude.ai のクライアントが 3 回 DCR 登録、いずれも consent 未完了で 401 連打

2. **メモリ常駐セッション**
   - `streamable-http` の既定はサーバ側 in-memory に `Mcp-Session-Id` を保持
   - コンテナ再生成で全クライアントが `-32600 "Session not found"` を喰らう
   - 実ログ: docker compose rebuild 直後の `POST /mcp` がこのエラーで失敗

### 対策

- [x] `src/x_hermes_mcp/auth/provider.py`: リフレッシュトークン rotation に 60 秒 grace period 追加
  - 旧トークンは即削除せず `consumed_at` を立て、発行済みの新トークン応答 (`successor_token_response_json`) を保存
  - grace 内の旧トークン再要求には**同じ応答を idempotent に返す** (RFC 6749/OAuth 2.1 のローテーションは維持)
  - schema additive migration (`PRAGMA table_info` 冪等チェック → `ALTER TABLE ADD COLUMN`)
- [x] `tests/test_refresh_grace.py`: 4 ケースのスモークテスト (新規 rotation / grace 内冪等 replay / grace 切れ拒否 / 後継トークン正常 rotation)
- [x] `src/x_hermes_mcp/server.py`: `mcp.run(..., stateless_http=True)` でセッション状態を持たない
  - サーバ再起動でクライアントが詰まらない
  - サーバ→クライアント push 通知は使ってないので副作用なし (起動ログに `(stateless)` 表示)

### 別件 (今回は応急対応のみ、恒久対策は別途)

DNS 層で `hermes.kitepon.dynv6.net` が一部リゾルバで NXDOMAIN になる事案が並行発生:

- ddnser コンテナが 09:55 JST に停止 → 再起動 (`docker inspect` で `RestartCount=0 ExitCode=0` → クラッシュではなく手動 restart 相当)
- 停止期間中に Cloudflare 公開 DNS (1.1.1.1) が NXDOMAIN をネガティブキャッシュ
- ChatGPT/OpenAI のコネクタプロキシがこのリゾルバ系統を引いていたため `mcp_network_error` 連発
- 応急: `https://cloudflare-dns.com/api/v1/purge?domain=hermes.kitepon.dynv6.net&type=A` で手動 purge → 即復旧
- 恒久対策候補: ddnser の停止アラート、もしくは DNS 周りを Cloudflare DNS 等のより伝播強い経路に移行

---

## Phase 9 — 画像生成ツール追加 (xAI OAuth 直叩き、2026-05-18 完了)

### 経緯

Hermes 組み込みの `image_generation_tool.py` は FAL.ai 経路で、`FAL_API_KEY` が必須 → 追加課金経路発生 → 本プロジェクトの原則 (Premium Plus quota 内に収める) と衝突。

ただし Hermes 側の `tools/xai_http.py:resolve_xai_http_credentials()` は **xai-oauth (SuperGrok / Premium Plus) を最優先で返してから XAI_API_KEY にフォールバック**する設計で、コメントには「direct xAI endpoints (images, TTS, STT, etc.) を OAuth と整合させる」と明示。

実機検証:
- OAuth トークンで `POST https://api.x.ai/v1/images/generations` → **200 OK + 画像 URL** が返る
- `usage.cost_in_usd_ticks: 200000000` (pay-per-use 換算 $0.20) が応答に乗るが、課金経路は OAuth (= サブスク quota)
- `XAI_API_KEY` 未設定 = pay-per-use 経路ゼロ = 課金宛先が無い、なので最悪 dev console プリペイド残高 $7.07 が天井

→ Premium Plus quota 内で動く想定で実装、リポを **private 化** して取り扱う方針 (経路を広めると xAI が塞ぐ可能性、SuperGrok 全ユーザの便益を損ねる)。

### 実装

- [x] `src/x_hermes_mcp/image_client.py` — `call_image_generate(...)`、Hermes Python に subprocess して `resolve_xai_http_credentials()` で OAuth bearer を取り、`POST /v1/images/generations` を直接叩く
- [x] `src/x_hermes_mcp/tools/generate_image.py` — 上記の薄い MCP 用ラッパ
- [x] `server.py` に `generate_image` を 7 番目のツールとして登録、tool selection guide も更新
- [x] サーバ側 (OAuth 経路) を強制: `provider != 'xai-oauth'` の時は exit 3 で拒否 (pay-per-use への意図せぬフォールバックを防ぐ)
- [x] container rebuild → `get_tool("generate_image")` で登録確認、スモーク呼び出しで実 URL 取得

### スキーマ

```
{
  "url": "https://imgen.x.ai/xai-imgen/xai-tmp-imgen-<uuid>.jpeg|.png",
  "mime_type": "image/jpeg" | "image/png",
  "model": "grok-imagine-image" | "grok-imagine-image-quality",
  "prompt": str,
  "aspect_ratio": "1:1" | "16:9" | "9:16" | "4:3" | "3:4" | "21:9",
  "resolution": "1k" | "2k",
  "cost_in_usd_ticks": int,   # 参考表示、サブスク経路では課金されない想定
  "source": "xai_imgen_raw_v1"
}
```

URL は `xai-tmp-` プレフィックスで時限有効 → 永続化したければクライアント側でダウンロード必要。

### 公開方針

- リポ全体を private 化済み (kitepon-rgb/HermesAgent)
- 第三者再現可能な情報を公開すると xAI が経路を塞ぐ可能性が高く、SuperGrok 全ユーザに副作用が出るため、知人共有レベルに留める

---

## 将来の拡張: 他領域の Hermes MCP (Phase 10 以降の候補)

Hermes Agent 本体は X 検索以外にも幅広く動く。Phase 2 で確立したパターン (構造化プロンプト → JSON 出力 → MCP 化) は他領域にも同形で転用可能。**Phase 4 までで X-HERMES-MCP の本番運用が安定してから着手**する想定。

### 想定 MCP 群

| 領域 | Hermes 側の道具 | 想定 MCP 名 |
|---|---|---|
| 一般 Web 調査 | `web_search` / `web_extract` | `WEB-HERMES-MCP` |
| 画像解析 | `vision_analyze` | `VISION-HERMES-MCP` |
| 画像生成 | `image_generate` (Grok Imagine) | `IMAGE-HERMES-MCP` |
| 音声合成 | `text_to_speech` (Grok Voice) | `TTS-HERMES-MCP` |
| 多段推論 | `mixture_of_agents` | `MOA-HERMES-MCP` |
| ブラウザ操作 | Playwright 系 | `BROWSER-HERMES-MCP` |

いずれも X Premium Plus サブスクの quota プール内で動く想定 (xAI 側で完結、追加課金経路なし)。

### 同一コンテナでの共存構成

```text
[192.168.1.2 コンテナ 1 個]
 ├── ~/.hermes/                  共有: 本体・OAuth・quota プール
 ├── X-HERMES-MCP        port 9201  ← Phase 4 で着手
 ├── WEB-HERMES-MCP      port 9202
 ├── VISION-HERMES-MCP   port 9203
 ├── IMAGE-HERMES-MCP    port 9204
 ├── TTS-HERMES-MCP      port 9205
 ├── MOA-HERMES-MCP      port 9206
 ├── BROWSER-HERMES-MCP  port 9207
 └── 共通認証ゲート       port 9200 (nginx + bearer)
```

利点:

- OAuth は 1 回 (xai-oauth credentials を全 MCP で共有)
- quota プールも共有
- MCP 単位で起動 / 停止・クライアント側登録解除が独立
- 共通認証層を前段に置くだけで全 MCP に効く

### 着手判断

早すぎる一般化を避けるため、Phase 4 完了まで他領域 MCP には手を出さない。**X-HERMES-MCP を完成させる → そこで固まった「構造化プロンプト → MCP ラッパ → 認証 → 公開」の汎用パターンを、他領域に同形で複製する** の順で進める。

各領域の必要性が出てきた時点で、上記表から該当行をピックして Phase 5+ として扱う。

---

## 既知の不明点 (要調査 or 要決定)

| トピック | 内容 | 影響範囲 |
|---|---|---|
| Grok quota | SuperGrok 経路の quota 上限が xAI 公式に明記されていない。重い用途で当たるか | Phase 2 以降 |
| `hermes mcp` の HTTP 対応 | 内蔵 MCP モードが stdio のみか、HTTP/SSE も話せるか | Phase 3, Phase 4 |
| 外部到達の認証強度 | LAN 越し → 外出先のチェーンでどこまでガチに認証するか | Phase 4 |
| ホームサーバ既存サービスとの共存 | ConnectC2X 本番との同居時のポート/リソース競合 | Phase 4 |
| ConnectC2X 自己認証経路 | 自分が ConnectC2X 利用者として認証する経路 (商用利用者と同じ OAuth か、内部優遇か) | Phase 3 以降 |
| 同一 X アカウントでの xAI OAuth 多重ログイン | ローカル機と 192.168.1.2 から同時に xai-oauth を貼った時の挙動 (相互失効しないか) | Phase 4 |

## メモ

- 「Hermes 経由 X 検索は Claude のトークンを食わずに Grok の重い推論を借りられる」というコスト構造が、本プロジェクトの経済合理性の根拠
- 設計の経緯: 当初「Hermes 単体で ConnectC2X を完全置き換え」の枠組みで進めたが、Hermes Agent v0.14.0 の `xurl` スキル発見 → X 開発者 pay-per-use 課金発見 を経て、最終的に **「Hermes は無料の検索 5 機能専業、ConnectC2X は有料の構造化 3 機能専業」の併用構成** に着地
- ConnectC2X は他者向け商用として継続。本プロジェクトはあくまで「自分用の経路を Premium Plus に寄せる」のが目的。ConnectC2X 廃止が目的ではない
- 重複ツールの選択誘導は ConnectC2X コード本体ではなく、各 MCP クライアントの設定 (`permissions.deny` / `tools_deny` / Connectors UI トグル) で行う
