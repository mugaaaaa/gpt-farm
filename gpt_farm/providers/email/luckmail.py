"""LuckMail provider — purchased real mailboxes (outlook.it, etc.)."""

import re
import time
from typing import Optional

import requests

from .base import BaseEmailProvider, EmailAccount


class LuckMailProvider(BaseEmailProvider):
    name = "luckmail"

    def __init__(
        self,
        luckmail_key: str = "",
        luckmail_url: str = "https://mails.luckyous.com/",
        luckmail_email_type: str = "ms_imap",
        proxy: str = "",
    ):
        if not luckmail_key:
            raise ValueError("luckmail_key is required")
        self.api_key = str(luckmail_key).strip()
        self.base_url = str(luckmail_url).rstrip("/")
        self.email_type = str(luckmail_email_type or "ms_imap").strip()
        self.proxy = str(proxy or "").strip() or None
        self._token: Optional[str] = None
        self._email: Optional[str] = None

    def create(self) -> EmailAccount:
        sess = requests.Session()
        if self.proxy:
            sess.proxies = {"http": self.proxy, "https": self.proxy}
        sess.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        r = sess.post(
            f"{self.base_url}/api/v1/openapi/email/purchase",
            json={"project_code": "openai", "quantity": 1, "email_type": self.email_type},
            timeout=15,
        )
        data = r.json()
        inner = data.get("data", data)
        purchases = inner.get("purchases") or []
        if not purchases:
            raise RuntimeError(f"LuckMail purchase failed: {r.text[:200]}")
        item = purchases[0]
        self._email = item["email_address"]
        self._token = item["token"]
        return EmailAccount(email=self._email, wait_for_code=self._otp_fetcher)

    def _otp_fetcher(self, timeout: int = 180) -> Optional[str]:
        token = self._token
        sess = requests.Session()
        if self.proxy:
            sess.proxies = {"http": self.proxy, "https": self.proxy}
        sess.headers.update({"Authorization": f"Bearer {self.api_key}"})

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = sess.get(f"{self.base_url}/api/v1/openapi/email/token/{token}/mails", timeout=10)
                for m in r.json().get("mails", []):
                    mid = m.get("message_id", "")
                    r2 = sess.get(f"{self.base_url}/api/v1/openapi/email/token/{token}/mails/{mid}", timeout=10)
                    detail = r2.json()
                    code = detail.get("verification_code", "")
                    if code:
                        return code
                    text = f"{detail.get('subject','')} {detail.get('body_html','')}"
                    mt = re.search(r"\b(\d{6})\b", text)
                    if mt:
                        return mt.group(1)
            except Exception:
                pass
            time.sleep(8)
        return None

    def validate(self) -> bool:
        try:
            sess = requests.Session()
            sess.headers.update({"Authorization": f"Bearer {self.api_key}"})
            r = sess.get(f"{self.base_url}/api/v1/openapi/email/config", timeout=10)
            return r.status_code == 200
        except Exception:
            return False
