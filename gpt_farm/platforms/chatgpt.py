"""ChatGPT registration — pure HTTP protocol via Codex OAuth flow."""

import json
import os
import re
import time
import random
import string
import hashlib
import base64
from typing import Any, Optional
from dataclasses import dataclass, field

from curl_cffi import requests as curl_requests

from ..providers.email.base import BaseEmailProvider, EmailAccount

CLIENT_ID = "pdlLIX2Y72MIl2rhLhTE9VV9bN905kBh"
AUTH_URL = "https://auth.openai.com/authorize"
TOKEN_URL = "https://auth0.openai.com/oauth/token"
REDIRECT_URI = "com.openai.chat://auth0.openai.com/ios/com.openai.chat/callback"
SCOPE = "openid profile email offline_access"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class RegistrationResult:
    email: str
    password: str
    access_token: str = ""
    refresh_token: str = ""
    id_token: str = ""
    account_id: str = ""
    extra: dict = field(default_factory=dict)


def _gen_password() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$", k=16)) + "Aa1!"


def _random_name() -> str:
    fn = "".join(random.choices(string.ascii_lowercase, k=5)).capitalize()
    ln = "".join(random.choices(string.ascii_lowercase, k=6)).capitalize()
    return f"{fn} {ln}"


def _random_birthdate() -> str:
    return f"{random.randint(1980, 2002):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"


def _random_state() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()


def _pkce_verifier() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()


def _sha256_b64url(data: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data.encode()).digest()).rstrip(b"=").decode()


def _fetch_sentinel(flow: str, did: str, proxies: Optional[dict]) -> Optional[str]:
    try:
        r = curl_requests.post(
            "https://sentinel.openai.com/backend-api/sentinel/req",
            headers={
                "origin": "https://sentinel.openai.com",
                "referer": "https://sentinel.openai.com/backend-api/sentinel/frame.html?sv=20260219f9f6",
                "content-type": "text/plain;charset=UTF-8",
                "user-agent": UA,
            },
            data=json.dumps({"p": "", "id": did, "flow": flow}),
            proxies=proxies,
            impersonate="chrome120",
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("token")
    except Exception:
        pass
    return None


def register(
    email_provider: BaseEmailProvider,
    *,
    proxy: str = "",
    mode: str = "at",
) -> RegistrationResult:
    """Register a ChatGPT account.

    Args:
        email_provider: Any BaseEmailProvider instance.
        proxy: HTTP proxy URL (e.g. http://127.0.0.1:7890).
        mode: "at" for access_token_only, "rt" for refresh_token.

    Returns:
        RegistrationResult with credentials.
    """
    proxies = {"http": proxy, "https": proxy} if proxy else None
    account: EmailAccount = email_provider.create()
    password = _gen_password()

    s = curl_requests.Session(proxies=proxies, impersonate="chrome120")
    s.headers.update({"user-agent": UA})

    state = _random_state()
    code_verifier = _pkce_verifier()
    code_challenge = _sha256_b64url(code_verifier)

    # 1. OAuth authorize
    import urllib.parse as up
    params = {
        "client_id": CLIENT_ID, "response_type": "code",
        "redirect_uri": REDIRECT_URI, "scope": SCOPE,
        "state": state, "code_challenge": code_challenge,
        "code_challenge_method": "S256", "prompt": "login",
        "id_token_add_organizations": "true",
    }
    r = s.get(f"{AUTH_URL}?{up.urlencode(params)}", timeout=15)
    did = s.cookies.get("oai-did")
    if not did:
        raise RuntimeError("OAuth authorize failed — IP may be blocked")

    # 2. Sentinel tokens
    sen1 = _fetch_sentinel("authorize_continue", did, proxies)
    sentinel = (
        json.dumps({"p": "", "t": "", "c": sen1, "id": did, "flow": "authorize_continue"})
        if sen1 else None
    )
    sen2 = _fetch_sentinel("oauth_create_account", did, proxies)

    # 3. Submit email
    h = {"referer": "https://auth.openai.com/create-account", "accept": "application/json", "content-type": "application/json"}
    if sentinel:
        h["openai-sentinel-token"] = sentinel
    r = s.post(
        "https://auth.openai.com/api/accounts/authorize/continue",
        headers=h,
        json={"username": {"value": account.email, "kind": "email"}, "screen_hint": "signup"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Email submit failed: {r.status_code}")

    # 4. Password
    h["referer"] = "https://auth.openai.com/create-account/password"
    r = s.post(
        "https://auth.openai.com/api/accounts/user/register",
        headers=h,
        json={"password": password, "username": account.email},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Password failed ({r.status_code}): {r.text[:100]}")

    # 5. OTP
    s.get("https://auth.openai.com/api/accounts/email-otp/send", headers=h, timeout=15)
    code = account.wait_for_code(180)
    if not code:
        raise RuntimeError("OTP timeout — email not received")

    # 6. Validate OTP
    h["referer"] = "https://auth.openai.com/email-verification"
    r = s.post("https://auth.openai.com/api/accounts/email-otp/validate", headers=h, json={"code": code})
    if r.status_code != 200:
        raise RuntimeError(f"OTP validation failed: {r.status_code}")

    # 7. Create account (about_you)
    h["referer"] = "https://auth.openai.com/about-you"
    if sen2:
        h["openai-sentinel-so-token"] = sen2
    r = s.post(
        "https://auth.openai.com/api/accounts/create_account",
        headers=h,
        json={"name": _random_name(), "birthdate": _random_birthdate()},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Create account failed ({r.status_code}): {r.text[:100]}")

    # 8. Workspace
    ac = s.cookies.get("oai-client-auth-session")
    if not ac:
        raise RuntimeError("No auth session cookie")
    ws_data = json.loads(base64.urlsafe_b64decode(ac.split(".")[0] + "==="))
    ws_id = str((ws_data.get("workspaces") or [{}])[0].get("id", ""))
    r = s.post(
        "https://auth.openai.com/api/accounts/workspace/select",
        headers={"referer": "https://auth.openai.com/sign-in-with-chatgpt/codex/consent", "content-type": "application/json"},
        json={"workspace_id": ws_id},
    )
    if r.status_code != 200:
        raise RuntimeError("Workspace selection failed")

    result = RegistrationResult(
        email=account.email,
        password=password,
        access_token=s.cookies.get("oai-client-auth-session", ""),
    )

    # 9. Follow redirects for refresh_token
    if mode == "rt":
        import urllib.request as ur
        continue_url = str((r.json() or {}).get("continue_url") or "")
        current = continue_url
        for _ in range(6):
            r = s.get(current, allow_redirects=False, timeout=15)
            loc = r.headers.get("Location") or ""
            if r.status_code not in (301, 302, 303, 307, 308) or not loc:
                break
            next_url = up.urljoin(current, loc)
            if "code=" in next_url and "state=" in next_url:
                q = up.urlparse(next_url).query
                p = up.parse_qs(q)
                code_val = p.get("code", [None])[0]
                data = up.urlencode({
                    "grant_type": "authorization_code", "client_id": CLIENT_ID,
                    "code": code_val, "redirect_uri": REDIRECT_URI,
                    "code_verifier": code_verifier,
                }).encode()
                req = ur.Request(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
                with ur.urlopen(req, timeout=15) as resp:
                    tokens = json.loads(resp.read())
                result.access_token = tokens.get("access_token", "")
                result.refresh_token = tokens.get("refresh_token", "")
                result.id_token = tokens.get("id_token", "")
                # Decode email from id_token
                parts = result.id_token.split(".")
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==="))
                auth_info = payload.get("https://api.openai.com/auth", {})
                result.account_id = auth_info.get("chatgpt_account_id", "")
                break
            current = next_url

    return result
