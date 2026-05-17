"""`hermes -z PROMPT` を subprocess で呼び、JSON を返すラッパ。"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any


# `hermes` バイナリのパス。
# ローカル開発: PATH 上の `hermes` を使う (既定 `hermes`)。
# Phase 4 のコンテナ運用: host の `~/.hermes/` を bind mount するので、
# `HERMES_BIN=/home/kite/.hermes/hermes-agent/venv/bin/hermes` のように指定する。
HERMES_BIN = os.getenv("HERMES_BIN", "hermes")
DEFAULT_TIMEOUT = 300.0


class HermesError(RuntimeError):
    """hermes の起動失敗・タイムアウト・JSON パース失敗を表す例外。"""


def _clean_env() -> dict[str, str]:
    """host の `~/.local/bin/hermes` shim 相当: PYTHONPATH/PYTHONHOME を除いた env。"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def run_oneshot(prompt: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """`hermes -z PROMPT` を実行して標準出力を返す。"""
    try:
        result = subprocess.run(
            [HERMES_BIN, "-z", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_clean_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise HermesError(f"hermes timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise HermesError(f"hermes binary not found on PATH: {exc}") from exc

    if result.returncode != 0:
        raise HermesError(
            f"hermes exited with code {result.returncode}: "
            f"{result.stderr.strip()[:500]}"
        )
    return result.stdout


def run_json(prompt: str, timeout: float = DEFAULT_TIMEOUT) -> Any:
    """hermes を実行して標準出力を JSON としてパースして返す。"""
    raw = run_oneshot(prompt, timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HermesError(
            f"hermes stdout was not valid JSON: {exc}. "
            f"Raw output (first 500 chars): {raw[:500]!r}"
        ) from exc
