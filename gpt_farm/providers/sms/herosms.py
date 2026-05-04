"""HeroSMS provider — SMS activation via hero-sms.com."""

import time
from typing import Optional

import requests

from .base import BaseSmsProvider, SmsActivation


class HeroSmsProvider(BaseSmsProvider):
    name = "herosms"
    BASE_URL = "https://hero-sms.com/stubs/handler_api.php"

    def __init__(
        self,
        herosms_key: str = "",
        herosms_country: str = "187",
        herosms_service: str = "dr",
    ):
        if not herosms_key:
            raise ValueError("herosms_key is required")
        self.api_key = str(herosms_key).strip()
        self.default_country = str(herosms_country or "187").strip()
        self.default_service = str(herosms_service or "dr").strip()

    def _call(self, **params) -> str:
        params["api_key"] = self.api_key
        r = requests.get(self.BASE_URL, params=params, timeout=15)
        r.raise_for_status()
        return r.text.strip()

    def get_number(self, *, service: str = "", country: str = "") -> SmsActivation:
        svc = service or self.default_service
        ctry = country or self.default_country
        result = self._call(action="getNumber", service=svc, country=ctry)
        if not result.startswith("ACCESS_NUMBER:"):
            raise RuntimeError(f"HeroSMS getNumber failed: {result}")
        parts = result.split(":")
        return SmsActivation(
            activation_id=parts[1],
            phone_number=parts[2],
            country=ctry,
        )

    def wait_for_code(self, activation_id: str, *, timeout: int = 120) -> Optional[str]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self._call(action="getStatus", id=activation_id)
            if result.startswith("STATUS_OK:"):
                return result.split(":", 1)[1]
            if "STATUS_CANCEL" in result or "NO_ACTIVATION" in result:
                return None
            time.sleep(5)
        return None

    def cancel(self, activation_id: str) -> bool:
        try:
            self._call(action="setStatus", id=activation_id, status=8)
            return True
        except Exception:
            return False

    def validate(self) -> bool:
        try:
            result = self._call(action="getBalance")
            return result.startswith("ACCESS_BALANCE:")
        except Exception:
            return False
