"""`DOCS/prompts/*.md` から「採用プロンプト」セクションの本文を抽出して使う。"""

from __future__ import annotations

import re
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = _PROJECT_ROOT / "DOCS" / "prompts"

_PROMPT_RE = re.compile(
    r"##\s*採用プロンプト[^\n]*\n+```[a-zA-Z0-9]*\n(.*?)\n```",
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
