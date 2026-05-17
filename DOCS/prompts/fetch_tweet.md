# fetch_tweet — Hermes 経路 (X-HERMES-MCP) のプロンプト

最終更新: 2026-05-17

## 目的

ConnectC2X の `fetch_tweet` MCP ツールが返す情報を、Hermes (`hermes -z` 経由の `x_search`) で構造化 JSON として再現する。

## 入力

- `url`: X (Twitter) の投稿 URL (例: `https://x.com/xai/status/2055745332919808181`)

## 採用プロンプト (V2)

```
You are a strict JSON extraction agent for X (Twitter) post data.

Task: Use the x_search tool — calling it as many times as needed — to fetch ALL available information about the post at the given URL. Then return a single JSON object matching the schema below. Output ONLY the JSON object — no commentary, no markdown fences, no preamble.

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
- media: if there is an attached image / video / GIF / link card, list each with type and any direct media URL Grok provides.

Rules:
1. Output must be valid JSON, parseable by JSON.parse without modification.
2. Do not invent IDs or URLs — only use ones x_search actually returned.
3. Your entire output must start with { and end with }. No text before or after.
4. Metrics: output as-is. Do NOT convert "5.2K" to 5200 or similar.

URL: {URL}
```

## 実測結果 (2026-05-17, `https://x.com/xai/status/2055745332919808181`)

応答時間: 約 2 分 (Grok が x_search を複数回呼び出すため)

| 項目 | 結果 |
|---|---|
| `tweet_id` | `"2055745332919808181"` ✓ |
| `url` | 正規 URL ✓ |
| `author.username` / `display_name` | `"xai"` / `"xAI"` ✓ |
| `created_at` | `"May 16, 2026"` (人間可読、ISO 8601 ではない) |
| `text` | t.co 展開済み (`https://x.ai/news/grok-hermes` が見える) ✓ |
| `referenced_tweets` | 1 階層 (`tweet_id` + `author_username` + `text` 全て埋まる) |
| `metrics.likes` | `"5585"` (正確な整数、文字列型) |
| `metrics.retweets` | `"872"` |
| `metrics.replies` | `"549"` |
| `metrics.quotes` | `"397"` |
| `metrics.bookmarks` | `"2439"` (ConnectC2X は通常返さない、Hermes 優位) |
| `metrics.views` | `"1869907"` |
| `media` | `[]` (画像付き投稿でも取得できず) |
| `notes` | 補足コメント (例: prior Grok subscription integration への follow-up) |

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

- **media**: x_search の戻りに添付メディア URL が含まれない。「画像付き投稿である」という言及はあるが、構造化された media 配列としては埋まらない。プロンプトでさらに押しても変わらず (V3 で確認済み)。この機能が必須の用途は ConnectC2X 直接利用
- **日時の機械可読化**: 「May 16, 2026」形式。下流で ISO 8601 にしたい場合はパース層を別途用意

## V3/V4 で失敗したこと (記録)

- V3「Follow chain up to 3 levels」「media must be listed」を盛る → metrics 全項目 null
- V4「PRIMARY OBJECTIVES priority order で metrics 最優先、追従を 2 位」 → 同じく metrics 全項目 null、しかも 5 階層命令しても深まらず 1 階層止まり
- 結論: プロンプトに注文を増やすほど Grok の x_search 集中度が落ちる。V2 の粒度が局所最適

## 使い方 (CLI 直)

プロンプトの末尾 `URL: {URL}` の `{URL}` を実際の URL に置換し、`hermes -z "..."` に渡す。Phase 3 で MCP 化されると、サーバ側がこのテンプレートを保持し、外部からは `tweet_url` 引数のみ受け取る形になる。
