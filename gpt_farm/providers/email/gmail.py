"""Gmail IMAP provider — uses plus-aliases (user+tag@gmail.com)."""

import imaplib
import email as em
import re
import time
import random
import string
from typing import Optional

from .base import BaseEmailProvider, EmailAccount


class GmailProvider(BaseEmailProvider):
    name = "gmail"

    def __init__(self, gmail_user: str = "", gmail_pass: str = ""):
        if not gmail_user or not gmail_pass:
            raise ValueError("gmail_user and gmail_pass are required")
        self.user = str(gmail_user).strip()
        self.password = str(gmail_pass)
        local, domain = self.user.split("@", 1)
        self._local = local
        self._domain = domain

    def create(self) -> EmailAccount:
        tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        addr = f"{self._local}+{tag}@{self._domain}"
        return EmailAccount(email=addr, wait_for_code=lambda t=180: self._wait_code(addr, t))

    def validate(self) -> bool:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.user, self.password)
            mail.logout()
            return True
        except Exception:
            return False

    def _wait_code(self, target: str, timeout: int = 180) -> Optional[str]:
        deadline = time.time() + timeout
        seen: set[bytes] = set()
        while time.time() < deadline:
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(self.user, self.password)
                mail.select("INBOX")
                status, msgs = mail.search(None, f'TO "{target}"')
                if status == "OK" and msgs[0]:
                    for mid in reversed(msgs[0].split()):
                        if mid in seen:
                            continue
                        seen.add(mid)
                        st, data = mail.fetch(mid, "(RFC822)")
                        if st != "OK":
                            continue
                        msg = em.message_from_bytes(data[0][1])
                        body = str(msg)
                        m = re.search(r"\b(\d{6})\b", body)
                        if m:
                            mail.logout()
                            return m.group(1)
                mail.logout()
            except Exception:
                pass
            time.sleep(5)
        return None
