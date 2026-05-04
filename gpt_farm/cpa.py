"""CPA integration — push accounts to the auth pool."""

import json
import time
from typing import Any

import requests

from .platforms.chatgpt import CLIENT_ID, TOKEN_URL


def push_account(
    account: dict[str, Any],
    cpa_url: str,
    cpa_key: str,
    *,
    proxy: str = "",
) -> bool:
    """Upload a single account to CPA/CLIProxyAPI.

    Args:
        account: Dict with email, access_token, refresh_token, id_token.
        cpa_url: CLIProxyAPI base URL.
        cpa_key: Management API key.

    Returns:
        True on success.
    """
    at = account.get("access_token", "")
    rt = account.get("refresh_token", "")

    # Try refreshing the token if we have RT but no AT
    if not at and rt:
        try:
            import urllib.request as ur
            data = ur.urlencode({
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": rt,
            }).encode()
            req = ur.Request(TOKEN_URL, data=data,
                           headers={"Content-Type": "application/x-www-form-urlencoded"})
            with ur.urlopen(req, timeout=15) as r:
                tokens = json.loads(r.read())
            at = tokens.get("access_token", "")
        except Exception:
            pass

    payload = {
        "access_token": at,
        "refresh_token": rt,
        "id_token": account.get("id_token", ""),
        "email": account["email"],
        "type": "codex",
        "disabled": False,
    }

    fname = account["email"].replace("@", "_") + ".json"
    try:
        r = requests.post(
            f"{cpa_url}/v0/management/auth-files",
            headers={"Authorization": f"Bearer {cpa_key}"},
            files={"file": (fname, json.dumps(payload), "application/json")},
            timeout=15,
        )
        return r.status_code in (200, 201)
    except Exception:
        return False


def push_accounts(
    accounts: list[dict[str, Any]],
    cpa_url: str,
    cpa_key: str,
    *,
    proxy: str = "",
    delay: float = 0.5,
) -> tuple[int, int]:
    """Push multiple accounts. Returns (ok_count, fail_count)."""
    ok = fail = 0
    for acct in accounts:
        if push_account(acct, cpa_url, cpa_key, proxy=proxy):
            ok += 1
        else:
            fail += 1
        time.sleep(delay)
    return ok, fail


def get_pool_status(cpa_url: str, cpa_key: str) -> dict[str, Any]:
    """Query CPA auth pool status."""
    try:
        r = requests.get(
            f"{cpa_url}/v0/management/auth-files",
            headers={"Authorization": f"Bearer {cpa_key}"},
            timeout=10,
        )
        files = r.json().get("files", [])
    except Exception:
        files = []

    total = len(files)
    active = sum(1 for f in files if not f.get("disabled", False))
    total_success = sum(f.get("success", 0) for f in files)
    total_failed = sum(f.get("failed", 0) for f in files)

    return {
        "total": total,
        "active": active,
        "success": total_success,
        "failed": total_failed,
        "files": files,
    }
