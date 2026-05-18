"""Direct call to xAI `/v1/images/generations` via Hermes' bundled venv.

Mirrors the `x_search_client.py` pattern: subprocess into the Hermes Python
interpreter, borrow only `tools.xai_http.resolve_xai_http_credentials` to get
the SuperGrok / Premium Plus OAuth bearer, then POST to the image endpoint
directly. We never touch `hermes -z`, `image_generate_tool`, or any FAL.ai
path — those would add a separate billing channel.
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
DEFAULT_TIMEOUT = 120.0


class ImageGenError(RuntimeError):
    """image_generate subprocess failure (auth / timeout / upstream HTTP / parse)."""


# Inline runner: resolves OAuth bearer via Hermes, posts to /images/generations,
# emits the response as a single JSON line on stdout. Errors propagate via
# non-zero exit + stderr (no half-formed JSON).
_RUNNER_SCRIPT = (
    "import json, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from tools.xai_http import resolve_xai_http_credentials, hermes_xai_user_agent\n"
    "import requests\n"
    "params = json.load(sys.stdin)\n"
    "creds = resolve_xai_http_credentials()\n"
    "token = (creds.get('api_key') or '').strip()\n"
    "if not token:\n"
    "    sys.stderr.write('no xAI credentials resolved')\n"
    "    sys.exit(2)\n"
    "if creds.get('provider') != 'xai-oauth':\n"
    "    sys.stderr.write(f\"credentials are not OAuth-based (got {creds.get('provider')!r}); refusing to avoid pay-per-use billing\")\n"
    "    sys.exit(3)\n"
    "base_url = creds.get('base_url') or 'https://api.x.ai/v1'\n"
    "r = requests.post(\n"
    "    f'{base_url}/images/generations',\n"
    "    headers={\n"
    "        'Authorization': f'Bearer {token}',\n"
    "        'Content-Type': 'application/json',\n"
    "        'User-Agent': hermes_xai_user_agent(),\n"
    "    },\n"
    "    json=params,\n"
    "    timeout=90,\n"
    ")\n"
    "out = {'status': r.status_code, 'body': None}\n"
    "try:\n"
    "    out['body'] = r.json()\n"
    "except Exception:\n"
    "    out['body'] = {'raw': r.text[:1000]}\n"
    "sys.stdout.write(json.dumps(out))\n"
)


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return env


def call_image_generate(
    *,
    prompt: str,
    aspect_ratio: str = "1:1",
    resolution: str = "1k",
    quality: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Generate a single image via xAI OAuth and return a normalized dict.

    Args:
      prompt: text-to-image prompt
      aspect_ratio: one of "1:1", "16:9", "9:16", "4:3", "3:4", "21:9"
      resolution: "1k" or "2k" (xAI accepts lowercase only)
      quality: if True, use grok-imagine-image-quality (slower, more detail)
      timeout: subprocess timeout in seconds (default 120)

    Returns:
      {
        "url": "https://imgen.x.ai/...",
        "mime_type": "image/jpeg" | "image/png",
        "model": "grok-imagine-image" | "grok-imagine-image-quality",
        "prompt": str,
        "aspect_ratio": str,
        "resolution": str,
        "cost_in_usd_ticks": int | None,
        "source": "xai_imgen_raw_v1",
      }

    Raises:
      ImageGenError: subprocess failure, non-200 upstream, or malformed response.
    """
    model = "grok-imagine-image-quality" if quality else "grok-imagine-image"
    params = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
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
        raise ImageGenError(f"image_generate timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise ImageGenError(f"Hermes Python interpreter not found: {exc}") from exc

    if result.returncode != 0:
        raise ImageGenError(
            f"image_generate subprocess exited {result.returncode}: "
            f"{result.stderr.strip()[:500]}"
        )

    try:
        wrapped = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ImageGenError(
            f"image_generate output not valid JSON: {exc}. "
            f"Raw stdout (first 500): {result.stdout[:500]!r}"
        ) from exc

    status = wrapped.get("status")
    body = wrapped.get("body") or {}
    if status != 200:
        raise ImageGenError(
            f"xAI image generation failed: HTTP {status}, body={json.dumps(body)[:300]}"
        )

    data_list = body.get("data") or []
    if not data_list or not isinstance(data_list, list):
        raise ImageGenError(f"xAI response missing data[]: {json.dumps(body)[:300]}")

    first = data_list[0]
    url = first.get("url")
    if not url:
        raise ImageGenError(f"xAI response missing data[0].url: {json.dumps(first)[:300]}")

    usage = body.get("usage") or {}
    return {
        "url": url,
        "mime_type": first.get("mime_type"),
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "cost_in_usd_ticks": usage.get("cost_in_usd_ticks"),
        "source": "xai_imgen_raw_v1",
    }
