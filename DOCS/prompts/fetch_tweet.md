# fetch_tweet — Hermes 経路 (X-HERMES-MCP) のプロンプト

> ⚠️ **2026-05-18: V4 (raw + Python パーサ) で上書きされたため、本ファイルの V3 プロンプトは非アクティブ**。`src/x_hermes_mcp/tools/fetch_tweet.py` の実装が「`x_search` を 1 回直接呼び出して JSON 応答を引き出し Python でパース」に変わった (P7 P2)。本ファイルは歴史記録 / 同等動作を再現したい時の参考として残す。

最終更新: 2026-05-17 (V3 内容のまま、V4 に置き換え済み)

## 目的

ConnectC2X の `fetch_tweet` MCP ツールが返す情報を、Hermes (`hermes -z` 経由の `x_search`) で構造化 JSON として再現する。

## 入力

- `url`: X (Twitter) の投稿 URL (例: `https://x.com/xai/status/2055745332919808181`)

## 採用プロンプト (V3)

V3 の変更点: x_search のパラメータ `enable_image_understanding=true` `enable_video_understanding=true` を明示的に渡すよう指示。これで media 配列の `alt_text` に Grok の画像/動画解釈が入る (V2 では常に空だった)。

```
You are a strict JSON extraction agent for X (Twitter) post data.

Task: Use the x_search tool — calling it as many times as needed — to fetch ALL available information about the post at the given URL. Then return a single JSON object matching the schema below. Output ONLY the JSON object — no commentary, no markdown fences, no preamble.

When invoking x_search, ALWAYS set these parameters:
- enable_image_understanding: true
- enable_video_understanding: true
These let Grok describe attached photos / videos / GIFs so the `media[].alt_text` field can be populated. Skipping them leaves media descriptions empty.

Schema:
{
  "tweet_id": string,
  "url": string,
  "author": { "username": string, "display_name": string | null },
  "created_at": string,
  "text": string,
  "referenced_tweets": [
    { "type": "quoted" | "retweeted" | "replied_to", "tweet_id": string | null, "author_username": string | null, "text": string | null }
  ],
  "metrics": {
    "likes": string | null,
    "retweets": string | null,
    "replies": string | null,
    "quotes": string | null,
    "bookmarks": string | null,
    "views": string | null
  },
  "media": [
    { "type": "photo" | "video" | "animated_gif" | "link_card", "url": string | null, "alt_text": string | null }
  ],
  "notes": string | null
}

EXTRACTION GUIDELINES — make a determined effort to fill every field. null is a last resort:

- created_at: even if no exact ISO timestamp is available, capture the date string Grok provides (e.g., "May 16, 2026").
- metrics: engagement counts are visible on x.com — likes, reposts, replies, quotes, bookmarks, views/impressions. Call x_search specifically asking for engagement metrics if not present on the first pass. Output values as-is, including rounded display forms like "5.2K" or "1.58M".
- referenced_tweets: if the post quotes / replies to / reposts another, identify the other post's tweet ID and author username via a second x_search call.
- media: if there is an attached image / video / GIF / link card, list each entry. Fill `alt_text` with a concise description of what is shown (one short sentence). Direct media URLs may or may not be available — null is OK there, but `alt_text` should be filled whenever there is any visual content.

Rules:
1. Output must be valid JSON, parseable by JSON.parse without modification.
2. Do not invent IDs or URLs — only use ones x_search actually returned.
3. Your entire output must start with { and end with }. No text before or after.
4. Metrics: output as-is. Do NOT convert "5.2K" to 5200 or similar.

URL: {URL}
```

## 実測結果 (V3, 2026-05-18, `https://x.com/xai/status/2055745332919808181`)

応答時間: 約 2 分 (Grok が x_search を複数回呼び出すため)

| 項目 | 結果 |
|---|---|
| `tweet_id` | `"2055745332919808181"` ✓ |
| `url` | 正規 URL ✓ |
| `author.username` | `"xai"` ✓ |
| `author.display_name` | null (V2 で取れていた `"xAI"` が空になる時もある、Grok 任意) |
| `created_at` | `"May 16, 2026"` (人間可読、ISO 8601 ではない) |
| `text` | t.co 展開済み (`https://x.ai/news/grok-hermes` が見える) ✓ |
| `referenced_tweets` | 1 階層、`author_username` + `text` 取得、`tweet_id` は空になる場合あり |
| `metrics.likes` | `"6356"` (正確な整数、文字列型) |
| `metrics.retweets` | `"1078"` |
| `metrics.replies` | `"596"` |
| `metrics.quotes` | `"455"` |
| `metrics.bookmarks` | `"2878"` (ConnectC2X は通常返さない、Hermes 優位) |
| `metrics.views` | `"2403891"` |
| **`media[0].type`** | **`"photo"` ✓** |
| **`media[0].alt_text`** | **`"The image shows the Grok/xAI logo on the left and the dotted Hermes caduceus-style logo on the right against a dark background."`** ← V3 で取れた、V2 では常に空 |
| `notes` | null になる場合あり (V2 では文脈コメントが出ていた) |

## ConnectC2X 比較

| 項目 | ConnectC2X | Hermes V2 | 評価 |
|---|---|---|---|
| metrics 正確値 | 整数 | 整数 (文字列型) | 同等 |
| 引用チェーン深度 | 最大 5 階層 | 1 階層 | 部分 |
| 日時形式 | ISO 8601 | 人間可読 | 要パース |
| `media` 配列 | 構造化 + `alt_text` | 取得不可 | 欠落 |
| `bookmarks` | 未提供 | 提供 | Hermes 優位 |
| 応答時間 | 数秒 | 1〜2 分 | Hermes 大幅劣後 |

## 設計判断: 単一ツイート限定

このプロンプトは **意図的に 1 ツイートだけを構造化** する。`referenced_tweets[*].tweet_id` は埋めるが、その先 (引用の引用、リンクされたツイートの中身) には踏み込まない。

理由 (実測ベース):

- V3/V4 で「最大 3〜5 階層追従」を指示したところ、metrics が全項目 null に退化することが再現した。Grok の 1 応答内の x_search 呼び出し集中度には実用的な上限があり、追従と metrics 抽出が競合する
- 5 階層追従はラッパ層で `fetch_tweet` を再帰呼び出しする上位ツール (`fetch_tweet_chain`、Phase 3 実装) の責任とする
- 1 ツイートを完全に取りきる責務をこのプロンプトに集中させた方が、合成性も再利用性も高い

## 既知の限界 (アーキテクチャ外)

- **media 直接 URL**: x_search の戻りに添付メディアの直接 URL は含まれない (`media[].url` は null)。`alt_text` に Grok の視覚解釈は入る (V3 で実証)
- **日時の機械可読化**: 「May 16, 2026」形式。下流で ISO 8601 にしたい場合はパース層を別途用意

## 過去 V3/V4 (異なる方向) で失敗したこと (記録)

過去に試した別の V3 (深さ追従強要) や V4 (priority 並び替え) では、プロンプトに注文を増やすと Grok の x_search 集中度が落ちて metrics が全 null に退化した。**注文を増やす方向ではダメ**、しかし **x_search パラメータを明示する方向**は機能を引き出せると今回 (現 V3) 実証。

## x_search 明示パラメータ (現 V3 の鍵)

x_search は以下のパラメータを受け取れる (xAI ドキュメント由来):

- `query` (必須) — 自然言語クエリ
- `allowed_x_handles` — 含めるアカウント (max 10)
- `excluded_x_handles` — 除外するアカウント (max 10)
- `from_date` / `to_date` — YYYY-MM-DD
- `enable_image_understanding` — 画像内容理解
- `enable_video_understanding` — 動画内容理解

現 V3 では `enable_image_understanding=true` と `enable_video_understanding=true` を明示することで media の alt_text を埋めるよう Grok に依頼している。

## 使い方 (CLI 直)

プロンプトの末尾 `URL: {URL}` の `{URL}` を実際の URL に置換し、`hermes -z "..."` に渡す。Phase 3 で MCP 化されると、サーバ側がこのテンプレートを保持し、外部からは `tweet_url` 引数のみ受け取る形になる。
