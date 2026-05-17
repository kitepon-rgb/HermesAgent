# get_quote_tweets — Hermes 経路 (X-HERMES-MCP) のプロンプト

最終更新: 2026-05-17

## 目的

ConnectC2X の `get_quote_tweets` MCP ツールに相当する、指定ツイートを引用しているポストの一覧取得を Hermes (`hermes -z` 経由の `x_search`) で再現する。

## 設計意図

- ソースツイートを引用する最近の投稿を最大 5〜10 件サンプル取得
- 各引用ツイートは `tweet_id` / `url` / 著者 / 日付 / 本文の最小セット + 言語ヒント
- 全件列挙ではなくサンプル取得 (ConnectC2X は最大 100 件、Hermes は Grok の自然な上限内)
- ソース側の引用総数 (`source_total_quotes`) もベストエフォートで取得

## 入力

- `source_tweet_url`: 引用元になるツイート URL
- `max_quotes`: 取得件数 (1〜10 程度、既定 8)

## 採用プロンプト (V1)

```
You are a strict JSON extraction agent for X (Twitter) quote tweets.

Task: Use the x_search tool — calling it multiple times if needed — to identify recent posts that quote-tweeted the specified source post. For each quote tweet, extract its identifier, author handle, brief text, and date. Return a single JSON object matching the schema. Output ONLY the JSON object — no commentary, no markdown fences, no preamble.

Schema:
{
  "source_tweet_url": string,
  "source_tweet_id": string,
  "source_total_quotes": string | null,
  "quotes": [
    {
      "tweet_id": string,
      "url": string,
      "author_username": string,
      "author_display_name": string | null,
      "created_at": string,
      "text": string,
      "language": string | null,
      "metrics": {
        "likes": string | null,
        "retweets": string | null,
        "replies": string | null
      } | null
    }
  ],
  "notes": string | null
}

EXTRACTION GUIDELINES:

- Aim for 5–10 recent quote tweets, sorted by recency.
- If x_search reports the total quote count for the source post, put it in source_total_quotes (e.g., "367").
- For EACH quote tweet, you MUST fill: tweet_id, url, author_username, text. These are visible on the quote-tweets view — call x_search again specifically for any quote whose data is incomplete.
- created_at: capture whatever date Grok provides ("May 16, 2026" or "2h ago" both OK).
- language: capture two-letter code if Grok identifies non-English quotes (e.g., "ja", "fr"), else null.
- metrics: best effort. null per-field acceptable.

Rules:
1. Output must be valid JSON.
2. Do not invent — only include posts x_search actually returned.
3. Your entire output must start with { and end with }. No text before or after.
4. source_tweet_id is the numeric ID at the end of the source URL.

Source tweet URL: {SOURCE_URL}
Max quotes: {MAX_QUOTES}
```

## 実測結果 (2026-05-17, source=`https://x.com/xai/status/2055745332919808181`, max_quotes=`8`)

応答時間: 約 2 分 44 秒

| 項目 | 結果 |
|---|---|
| `source_tweet_id` | `2055745332919808181` ✓ |
| `source_total_quotes` | `"405"` ✓ (本日朝の 367 から増えてる、リアルタイム性確認) |
| 引用ツイート取得数 | 5 件 (要求 8、Grok 自然上限) |
| `tweet_id` 埋まり | 5/5 ✓ |
| `url` 埋まり | 5/5 ✓ |
| `author_username` | 5/5 ✓ |
| `author_display_name` | 4/5 |
| `created_at` | 5/5 (`"May 17, 2026"` 形式) |
| `text` | 5/5 (短いスニペット〜中程度) |
| `language` | 2/5 (日本語 2 件検出) |
| `metrics.*` | 2/5 (部分的に埋まる) |

取得された引用ツイート例:

- @tetumemo (ja): 「You can now use X Premium subscriptions in Hermes Agent... finally got it working...」
- @_a_2_c_ (ja): 「I've been gradually switching from OC to HA, but I feel HA matches my preference...」
- @naviidtaheri: 「From now on, you no longer need to buy a separate API key to use Grok in Hermes...」
- @Thomas_AI_geek: 「Good move.」
- @imbsxone: 「Testing Thread. That's some great news that x data can be pulled...」

## ConnectC2X 比較

| 項目 | ConnectC2X | Hermes V1 | 評価 |
|---|---|---|---|
| 結果件数 | 最大 100 | 5–10 件 | 件数で劣後 |
| `tweet_id` / `url` | ✓ | ✓ | 同等 |
| `author_username` | ✓ | ✓ | 同等 |
| `author_display_name` | ✓ | 部分 (Grok 任意) | 部分 |
| 本文 | フル | スニペット〜中程度 | 部分 |
| `language` | 言語コード | 部分 (Grok 検出時のみ) | 部分 |
| metrics per-quote | 整数 | 部分 (Grok 任意) | 部分 |
| 応答時間 | 数秒 | 約 2.7 分 | Hermes 劣後 |
| 引用総数 (source) | 別取得が必要 | 1 呼び出しで取れる | Hermes 優位 |

## 既知の限界

- **件数の上限**: 5〜10 件のサンプル取得が現実的天井。全件列挙 (引用総数 400 件超の場合) は不可
- **網羅性**: 「Latest」順か「Top」順かの制御が明確でない。プロンプトで指定しても Grok 任意になる場合がある
- **per-quote metrics**: 各引用ツイート個別の metrics は薄い。必要なら各 `url` を `fetch_tweet` に再投入

## 用法

ソースツイート URL + 件数指定で呼ぶ想定。Phase 3 の MCP ラッパで `get_quote_tweets(source_tweet_url, max_quotes=8)` として公開。
