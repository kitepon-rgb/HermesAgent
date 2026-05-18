"""Smoke test: refresh-token rotation grace period.

Run from repo root:
    uv run python -m tests.test_refresh_grace

What this verifies:
  1. Fresh rotation issues a new access + refresh pair and stores them.
  2. Replaying the old refresh token within the grace window returns the
     SAME OAuthToken response (idempotent — no double-issuance).
  3. After REFRESH_TOKEN_GRACE_SECONDS elapses, the old refresh is rejected.
  4. The successor refresh token rotates normally.

Exit code 0 on success, non-zero on any failure.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from x_hermes_mcp.auth import provider as provider_mod
from x_hermes_mcp.auth.provider import SqliteOAuthProvider


def _make_client(client_id: str = "test-client") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_id_issued_at=int(time.time()),
        redirect_uris=[AnyUrl("http://localhost/callback")],
    )


async def _bootstrap_refresh_token(p: SqliteOAuthProvider, client_id: str) -> str:
    """Mint an initial refresh token by simulating the auth-code exchange."""
    from mcp.server.auth.provider import AuthorizationCode

    code = AuthorizationCode(
        code="bootstrap-code",
        scopes=[],
        expires_at=time.time() + 600,
        client_id=client_id,
        code_challenge="x" * 43,
        redirect_uri=AnyUrl("http://localhost/callback"),
        redirect_uri_provided_explicitly=True,
        resource=None,
    )
    token = await p.exchange_authorization_code(_make_client(client_id), code)
    assert token.refresh_token is not None
    return token.refresh_token


async def run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "oauth.db"
        p = SqliteOAuthProvider(
            base_url="http://localhost",
            master_password="dummy",
            db_path=db_path,
        )
        client = _make_client("test-client")

        rt1_str = await _bootstrap_refresh_token(p, "test-client")
        rt1 = await p.load_refresh_token(client, rt1_str)
        assert rt1 is not None, "bootstrap refresh token should load"

        resp1 = await p.exchange_refresh_token(client, rt1, [])
        assert resp1.refresh_token != rt1_str, "rotation must mint new refresh"
        assert resp1.access_token, "must return access token"
        print(f"[1/4] fresh rotation OK   access={resp1.access_token[:8]}...")

        rt1_reload = await p.load_refresh_token(client, rt1_str)
        assert rt1_reload is not None, "old refresh must still load within grace"
        resp2 = await p.exchange_refresh_token(client, rt1_reload, [])
        assert resp2.access_token == resp1.access_token, (
            f"grace replay must be idempotent: {resp2.access_token=} != {resp1.access_token=}"
        )
        assert resp2.refresh_token == resp1.refresh_token
        print(f"[2/4] grace replay OK     same access={resp2.access_token[:8]}...")

        original_grace = provider_mod.REFRESH_TOKEN_GRACE_SECONDS
        provider_mod.REFRESH_TOKEN_GRACE_SECONDS = -1
        try:
            rt1_post_grace = await p.load_refresh_token(client, rt1_str)
            assert rt1_post_grace is None, "past-grace refresh must be rejected"
        finally:
            provider_mod.REFRESH_TOKEN_GRACE_SECONDS = original_grace
        print("[3/4] past-grace reject OK")

        rt2 = await p.load_refresh_token(client, resp1.refresh_token)
        assert rt2 is not None, "successor refresh token must load"
        resp3 = await p.exchange_refresh_token(client, rt2, [])
        assert resp3.refresh_token != resp1.refresh_token
        assert resp3.access_token != resp1.access_token
        print(f"[4/4] successor rotation OK new access={resp3.access_token[:8]}...")

        print("\nAll 4 cases passed.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
