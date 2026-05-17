# get_trends — Hermes 経路 (X-HERMES-MCP) のプロンプト

最終更新: 2026-05-17

## 目的

ConnectC2X の `get_trends` MCP ツールに相当する、地域別 X トレンド取得を Hermes (`hermes -z` 経由の `x_search`) で再現する。

## 設計意図

- ConnectC2X は WOEID 数値で地域指定するが、Hermes 側は Grok に渡せる **地域名 (文字列)** で受ける
- トレンド一覧と各トレンドの分類・関連エンティティ・代表ポスト URL を取得
- volume (投稿件数) は X 自体が一般公開していないため null 許容

## 入力

- `region`: 地域名 (例: `Japan`, `Tokyo`, `Global`, `United States`)
- `max_trends`: 取得件数 (1〜20 程度、既定 10)

## 採用プロンプト (V1)

```
You are a strict JSON extraction agent for X (Twitter) trending topics.

Task: Use the x_search tool — calling it multiple times if needed — to identify the current trending topics on X for the specified region (like the X "Trends for you" panel). For each trend, also identify one representative recent post URL via x_search to serve as evidence. Return a single JSON object matching the schema. Output ONLY the JSON object — no commentary, no markdown fences, no preamble.

Schema:
{
  "region": string,
  "fetched_at": string,
  "trends": [
    {
      "rank": number | null,
      "topic": string,
      "category": string | null,
      "related_to": string | null,
      "volume": string | null,
      "evidence_url": string | null,
      "note": string | null
    }
  ],
  "notes": string | null
}

EXTRACTION GUIDELINES:

- Aim for 8–15 trends, ordered by rank if available, else by rough prominence.
- topic: the trending word, phrase, or hashtag (verbatim).
- category: classify into one of: game / idol / music / news / politics / sports / entertainment / tv / tech / business / people / other.
- related_to: if the trend is about a specific entity (game title, celebrity, company), put its name here.
- evidence_url: pick one recent X post URL exemplifying this trend (use x_search per trend).
- volume: only fill if x_search surfaces a specific post count, else null.
- note: optional short context (e.g., event date, what is happening).

Rules:
1. Output must be valid JSON.
2. Do not invent topics or URLs — only use what x_search actually returned.
3. Your entire output must start with { and end with }. No text before or after.
4. fetched_at: use today's date in YYYY-MM-DD form.

Region: {REGION}
Max trends: {MAX_TRENDS}
```

## 実測結果 (2026-05-17, region=`Japan`, max_trends=`10`)

応答時間: 約 3 分 34 秒 (各トレンドの evidence_url を取りに行くため `fetch_tweet` より長い)

| 項目 | 結果 |
|---|---|
| 取得件数 | 9 件 (要求 10 にほぼ一致) |
| `rank` | 9/9 ✓ |
| `topic` | 9/9 ✓ |
| `category` | 9/9 ✓ (game/idol/music/news/politics/tv/entertainment) |
| `related_to` | 9/9 ✓ (関連エンティティを命名) |
| `evidence_url` | 9/9 ✓ (実在の投稿 URL) |
| `note` | 9/9 ✓ (イベント詳細・文脈) |
| `volume` | 0/9 (X が公開してない、構造的に取得不可) |

取得されたトレンド例:

- 高市早苗首相 / サナエショック (politics)
- 東北地方の地震 (news, 宮城県沖 M6.4)
- 俺の膝で万バズり (idol, なにわ男子 高橋恭平)
- ちびまる子ちゃん (tv)
- NIKKE アリーナ (game)
- かまいたちの掟感謝祭2026 (entertainment)
- 初心Letter (music, なにわ男子 ND5)
- #CoA1周年記念祭 (game, Crystal of Atlan)

→ 今日 2026-05-17 の実際のトレンドと整合 (地震は本日発生、政治・芸能イベントも当日)。

## ConnectC2X 比較

| 項目 | ConnectC2X | Hermes V1 | 評価 |
|---|---|---|---|
| 地域指定 | WOEID 数値 (Japan: 23424856) | 地域名文字列 ("Japan") | Hermes の方が直感的 |
| 件数 | 最大 50 (max_trends) | 8〜15 程度 | 件数で劣後 |
| `topic` | ✓ | ✓ | 同等 |
| `volume` (投稿件数) | X 提供時のみ | 取得不可 (常に null) | 欠落 |
| `category` 自動分類 | なし | あり (Grok 推定) | Hermes 優位 |
| `related_to` (関連エンティティ) | なし | あり | Hermes 優位 |
| `evidence_url` | なし | あり (代表ポスト 1 件) | Hermes 優位 |
| 応答時間 | 数秒 | 約 3.5 分 | Hermes 大幅劣後 |

## 既知の限界

- **`volume`**: X UI でトレンド横に表示される投稿件数 (例: 「12.3K Posts」) は xAI の x_search 経由で構造化されない。null 許容
- **件数の上限**: Grok が 1 応答で並べるのは 10〜15 件程度。それ以上は別ジャンルやサブカテゴリ指定で分割呼び出し
- **応答時間が長い**: 件数の N 倍の x_search 呼び出しが裏で走るため、件数を増やすほど線形に長くなる

## 用法

WOEID を地域名に変換するマッピングを Phase 3 の MCP ラッパに置く想定:

| WOEID | region |
|---|---|
| 23424856 | Japan |
| 1118370 | Tokyo |
| 1 | Worldwide / Global |
| 23424977 | United States |
