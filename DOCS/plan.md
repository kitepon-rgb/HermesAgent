# Hermes Agent MCP ラッパー計画

最終更新: 2026-05-17

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

### 公開ツール一覧

低レイヤ (Phase 2 のプロンプトを直接ラップ、1 ツール = 1 hermes 呼び出し):

- `fetch_tweet` — URL → 単一ツイート構造化 (1 階層引用言及付き、深掘りなし)
- `search_tweets` — キーワード → ツイートリスト構造化 (Phase 2 未着手)
- `search_tweets_all` — 全期間キーワード検索 (Phase 2 未着手)
- `get_trends` — 地域 → トレンドリスト構造化 (Phase 2 未着手)
- `get_quote_tweets` — ツイート ID → 引用一覧構造化 (Phase 2 未着手)

上位レイヤ (低レイヤを内部で複数回呼び出して合成):

- `fetch_tweet_chain` — URL + `max_depth` (1〜2、既定 2、ハード上限 2) → ツリー状の構造化
  - 内部実装: root を `fetch_tweet` で取得 → `referenced_tweets[*].tweet_id` を URL 化 → 各 ID を並列で `fetch_tweet` 呼び出し → 結果を木構造に組み立て
  - 最大応答時間目安: ~4 分 (depth 2、ファンアウト並列処理)
  - ConnectC2X の 5 階層自動展開には合わせない (実時間の代償が大きすぎる)

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
| 認証 | Bearer トークン (env var、`Authorization: Bearer ...`) | ソロ運用なので OAuth 不要 |
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
- [ ] リポジトリを host (192.168.1.2) に同期 (`~/X-HERMES-MCP/`)
- [ ] host の `~/X-HERMES-MCP/.env` を生成し `X_HERMES_MCP_TOKEN` をセット
- [ ] `docker compose up -d --build` で起動
- [ ] `~/license-server/Caddyfile` に上記ブロックを追記、Caddy reload
- [ ] LAN マシン (WSL) の `/etc/hosts` に `192.168.1.2 hermes.kitepon.dynv6.net` 追記
- [ ] 疎通確認 (`curl -H "Authorization: Bearer $TOKEN" https://hermes.kitepon.dynv6.net/mcp`)
- [ ] Claude Code の `.mcp.json` を HTTP リモート版に書き換え、再起動して接続確認
- [ ] 既存 ConnectC2X (同マシン稼働中) との同居動作を確認 (ポート衝突なし、Caddy ルート衝突なし)

---

## 将来の拡張: 他領域の Hermes MCP (Phase 5 以降の候補)

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
