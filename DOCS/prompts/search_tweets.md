# search_tweets — Hermes 経路 (X-HERMES-MCP) のプロンプト

最終更新: 2026-05-17

## 目的

ConnectC2X の `search_tweets` MCP ツールに相当する、キーワード + 期間/言語/著者フィルタによる X 投稿リスト取得を Hermes (`hermes -z` 経由の `x_search`) で再現する。

## 設計意図

- 一覧取得に集中。各エントリは tweet_id / url / 著者ハンドル / 日付 / 本文の最小セットを埋める
- per-tweet の詳細データ (metrics 完全形、引用チェーン、メディアなど) が欲しい場合は、各 URL を `fetch_tweet` に投げる責務にする
- 1 回の `hermes -z` 呼び出しで完結 (内部で Grok が x_search を 1〜2 回叩く)

## 入力

- `query`: 検索キーワード
- `filters.lang`: 言語コード (例: `en`, `ja`) または null
- `filters.since`: 検索開始日 (`YYYY-MM-DD`) または null
- `filters.until`: 検索終了日 (`YYYY-MM-DD`) または null
- `filters.from_user`: 特定アカウントハンドル または null

## 採用プロンプト (V2)

```
You are a strict JSON extraction agent for X (Twitter) search results.

Task: Use the x_search tool to search X posts matching the query and filter constraints below. For each result, extract the post's identifier, author handle, brief text, and date — like an X search results page. Return a single JSON object matching the schema. Output ONLY the JSON object — no commentary, no markdown fences, no preamble.

Schema:
{
  "query": string,
  "filters": {
    "lang": string | null,
    "since": string | null,
    "until": string | null,
    "from_user": string | null
  },
  "results": [
    {
      "tweet_id": string,
      "url": string,
      "author_username": string,
      "author_display_name": string | null,
      "created_at": string,
      "text": string,
      "metrics": {
        "likes": string | null,
        "retweets": string | null,
        "replies": string | null
      } | null
    }
  ],
  "total_estimated": string | null,
  "notes": string | null
}

EXTRACTION GUIDELINES:

- Aim for 5–10 results, sorted by recency unless told otherwise.
- For EACH result, you MUST fill: tweet_id, url, author_username, text. These are visible on the X search results page — if x_search did not surface them on the first call, call x_search again specifically to identify each result's author handle and a one-line text snippet.
- created_at: capture whatever date Grok provides for the result ("May 16, 2026" or "2h ago" are both fine).
- metrics: best effort. null per-field is acceptable.
- tweet_id is the numeric string at the end of the post URL.
- An empty results array is only valid if x_search truly returned no matches.

Rules:
1. Output must be valid JSON.
2. Do not invent — only include posts x_search actually returned.
3. Your entire output must start with { and end with }. No text before or after.

Query: {QUERY}
Filters: lang={LANG}, since={SINCE}, until={UNTIL}, from_user={FROM_USER}
```

## 実測結果 (2026-05-17, query=`Hermes Agent`, lang=`en`, since=`2026-05-14`)

応答時間: 約 46 秒

| 項目 | 結果 |
|---|---|
| 結果数 | 6 件 (`total_estimated: "6"`) |
| `tweet_id` 埋まり | 6/6 ✓ |
| `url` 埋まり | 6/6 ✓ |
| `author_username` 埋まり | 6/6 ✓ |
| `created_at` 埋まり | 6/6 (`"May 16, 2026"` 形式) |
| `text` 埋まり | 6/6 (短いスニペット) |
| `author_display_name` | 0/6 (Grok が深追いせず) |
| `metrics.*` | 0/6 (X 検索結果ページに表示なし、構造的に取得不可) |

例:

- @nik1t7n: 「Hermes agent found apartments, contacted landlords, parsed pricing/terms...」 (May 16, 2026)
- @0xDataWolf: 「Several mentions of using /plan mode...」 (May 16, 2026)
- @gkisokay: 「Strong interest in connecting it to Grok...」 (May 16, 2026)

## ConnectC2X 比較

| 項目 | ConnectC2X | Hermes V2 | 評価 |
|---|---|---|---|
| 結果件数 | 最大 100 件 (max_results 指定可) | 5–10 件程度 | 件数で劣後 |
| tweet_id / url | ✓ | ✓ | 同等 |
| 本文 (`text`) | フル本文 + t.co 展開 | 短いスニペット | 部分 |
| `created_at` | ISO 8601 | 人間可読 | 要パース |
| metrics | 整数 | 取得不可 (検索ページに表示なし) | 欠落 |
| メディア | 構造化 | なし | 欠落 |
| 応答時間 | 数秒 | 約 46 秒 | Hermes 劣後 |

## 既知の限界

- **件数の上限**: Grok が 1 応答で並べるのは 5〜10 件程度。それ以上は別クエリで分割して呼ぶ必要あり (ページネーション概念なし)
- **`metrics` per-result**: X 検索結果ページに metrics が表示されないため Grok 経由では取得不可。各ツイートの metrics が欲しければ `fetch_tweet` を URL ごとに呼ぶ
- **本文がスニペット**: フル本文が欲しければ `fetch_tweet` を呼ぶ
- **`author_display_name`**: ハンドル名から推測可能だが Grok は埋めない

## `search_tweets_all` (Pro 全期間検索) との関係

ConnectC2X では `search_tweets` (直近 7 日) と `search_tweets_all` (全期間) が別ツールとして登録されている。Hermes 側では `filters.since` / `filters.until` の値次第で同じプロンプトが両対応する想定。MCP 化時に別ツール名で公開するかは Phase 3 の設計判断。

## V1 で失敗したこと (記録)

V1 では「each result must fill ...」を明示せず、`results: []` 空配列で `notes` 欄に「citations あったが per-post 構造化データはなかった」と書かれて終了。V2 で「For EACH result, you MUST fill: ... — like an X search results page」と強制したところ、各エントリが揃った。
