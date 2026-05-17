# HermesAgent プロジェクト

## 目的

Hermes Agent をラッパとして、ConnectC2X が提供している X 関連機能を **X Premium Plus サブスクリプションの範囲内** で実現する MCP サーバを構築する。

最終形:
- ホームサーバ (192.168.1.2) にデプロイ
- 外出先の Claude / Codex から呼び出せる
- ConnectC2X (商用、他人向け) とは独立に、自分用の経路として成立させる

詳細な現状・TODO は [DOCS/plan.md](DOCS/plan.md) を参照。これがこのプロジェクトの単一の状態管理ドキュメントを兼ねる。

## 隣接資産

- `/home/kite/projects/ConnectC2X/` — 自前の X API v2 MCP。商用サービスとして他者向けに維持。機能インベントリの参考元
- `/home/kite/.hermes/` — Hermes Agent v0.14.0 本体。OAuth 設定済み (`xai-oauth-oauth-1`)、既定モデル `grok-4.3`
- `/home/kite/.claude/plans/mcp-premium-swirling-bear.md` — 本プロジェクトの起点となった置き換え想像案

## 絶対ルール

### シークレット系
- `~/.xurl` を **読まない / 印字しない / 要約しない / 中身をプロンプトに混ぜない**。X 開発者シークレットが入る場所
- `XAI_API_KEY` を `~/.hermes/.env` に書かない。書いた瞬間に OAuth 経路ではなく従量課金経路に切り替わる
- `--bearer-token` `--consumer-key` `--consumer-secret` `--access-token` `--token-secret` `--client-id` `--client-secret` を `xurl` コマンドにインラインで渡さない。秘匿情報がログに残る
- `xurl` に `--verbose` / `-v` を付けない。認証ヘッダが出る
- 認証状態の確認は `xurl auth status` のみ

### 課金経路
- FlyHermes (マネージド版 $29.50→$59/月) は採用しない。self-host のみ
- Web 検索系の有料 API キー (Exa / Brave / Tavily / Firecrawl) を追加しない
- 他社 LLM プロバイダのキーを追加しない
- Modal / Daytona などのサーバーレスは使わない

### コーディング
- 起こり得ない状況の防御コードを書かない
- 依頼されてない機能・抽象化・柔軟性を足さない
- 識別子 (関数名・ファイル名・略語・カタカナ技術用語) を会話に出さず、役割と機能で説明する
- コメントは「なぜ」が非自明な時だけ書く。「何を」はコード自身で示す

## 進行ルール

1. 触る前に [DOCS/plan.md](DOCS/plan.md) のチェックボックスで現状を確認
2. 完了したら同じファイルのチェックを更新
3. 仮定が分かれる選択肢に当たったら、両方提示してユーザーに判断を仰ぐ
4. 「既知の不明点」セクションが膨れたら別ドキュメントに切り出す

## Hermes 動作確認の最小コマンド

```
hermes auth status xai-oauth          # OAuth 健在確認
hermes -z "What model are you?"       # Grok-4.3 疎通
xurl auth status                       # xurl 認証確認 (Phase 1 後)
```

## ダッシュボード

```
hermes dashboard --tui                # 起動
hermes dashboard --stop                # 停止
```

`http://127.0.0.1:9119` で Web UI、`--tui` 付きでブラウザ内チャット。
