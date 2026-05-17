"""`DOCS/prompts/*.md` から「採用プロンプト」セクションの本文を抽出して使う。"""

from __future__ import annotations

import os
import re
from pathlib import Path


# ローカル開発: パッケージから 2 つ上 (= プロジェクトルート) の DOCS/prompts を読む。
# Docker / インストール後: `X_HERMES_MCP_PROMPTS_DIR` 環境変数で絶対パス指定。
_DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "DOCS" / "prompts"
PROMPTS_DIR = Path(os.getenv("X_HERMES_MCP_PROMPTS_DIR") or _DEFAULT_PROMPTS_DIR)

_PROMPT_RE = re.compile(
    # `## 採用プロンプト` 見出しの後、最初に現れるコードフェンスの中身を取り出す。
    # 見出しとフェンスの間に説明段落 (V3 の変更点など) があっても許容する。
    r"##\s*採用プロンプト[^\n]*\n.*?```[a-zA-Z0-9]*\n(.*?)\n```",
    re.DOTALL,
)


class PromptLoadError(RuntimeError):
    """採用プロンプトの抽出に失敗した場合の例外。"""


def load(name: str) -> str:
    """`DOCS/prompts/<name>.md` から採用プロンプト本文を取り出す。"""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise PromptLoadError(f"prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    match = _PROMPT_RE.search(text)
    if not match:
        raise PromptLoadError(
            f"`## 採用プロンプト` の直後のコードフェンスが {path} に見つからない"
        )
    return match.group(1).rstrip()


def fill(template: str, **vars: object) -> str:
    """テンプレ中の `{VAR}` プレースホルダを実値で置換する (キー名は大文字に変換)。"""
    result = template
    for key, value in vars.items():
        placeholder = "{" + key.upper() + "}"
        result = result.replace(placeholder, str(value))
    return result
