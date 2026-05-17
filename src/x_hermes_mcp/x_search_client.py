"""Direct call to xAI `x_search` via Hermes' Python venv, bypassing Grok-4.3.

Subprocess pattern: run Hermes' bundled venv interpreter with `HERMES_ROOT` on
`sys.path` so the `tools.x_search_tool` module imports cleanly. Parameters in
via JSON stdin, result out via JSON stdout (already a JSON string from
`x_search_tool`).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any


HERMES_ROOT = os.getenv("HERMES_ROOT", "/home/kite/.hermes/hermes-agent")
HERMES_PYTHON = os.getenv(
    "HERMES_PYTHON",
    "/home/kite/.hermes/hermes-agent/venv/bin/python",
)
DEFAULT_TIMEOUT = 180.0


class XSearchError(RuntimeError):
    """x_search subprocess failure (auth / timeout / upstream HTTP / parse)."""


# Hermes 側で実行する薄いランナー。`tools.x_search_tool` の戻り値は JSON 文字列
# なので、stdin から渡されたパラメータを **kwargs で展開して呼び、結果をそのまま
# stdout に流すだけ。
_RUNNER_SCRIPT = (
    "import json, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from tools.x_search_tool import x_search_tool\n"
    "params = json.load(sys.stdin)\n"
    "sys.stdout.write(x_search_tool(**params))\n"
)


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def call_x_search(
    *,
    query: str,
    allowed_x_handles: list[str] | None = None,
    excluded_x_handles: list[str] | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    enable_image_understanding: bool = False,
    enable_video_understanding: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Call xAI x_search directly through Hermes' bundled Python interpreter.

    Returns the parsed dict from x_search_tool's JSON output, e.g.:
    `{success, provider, credential_source, tool, model, query, answer,
    citations, inline_citations}`.
    """
    params: dict[str, Any] = {"query": query}
    if allowed_x_handles:
        params["allowed_x_handles"] = allowed_x_handles
    if excluded_x_handles:
        params["excluded_x_handles"] = excluded_x_handles
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    if enable_image_understanding:
        params["enable_image_understanding"] = True
    if enable_video_understanding:
        params["enable_video_understanding"] = True

    try:
        result = subprocess.run(
            [HERMES_PYTHON, "-c", _RUNNER_SCRIPT, HERMES_ROOT],
            input=json.dumps(params),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=_clean_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise XSearchError(f"x_search timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise XSearchError(f"Hermes Python interpreter not found: {exc}") from exc

    if result.returncode != 0:
        raise XSearchError(
            f"x_search subprocess exited {result.returncode}: "
            f"{result.stderr.strip()[:500]}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise XSearchError(
            f"x_search output not valid JSON: {exc}. "
            f"Raw stdout (first 500): {result.stdout[:500]!r}"
        ) from exc
