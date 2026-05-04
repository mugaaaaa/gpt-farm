"""Configuration management.

Loads from (in priority order):
  1. Environment variables (GPT_FARM_<KEY>)
  2. Config file (default: ~/.gpt-farm/config.json)
  3. Built-in defaults
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

DEFAULT_CONFIG_DIR = Path(os.environ.get("GPT_FARM_CONFIG_DIR", Path.home() / ".gpt-farm"))
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    # ---- Email providers ----
    "email_provider": "luckmail",
    # LuckMail
    "luckmail_key": "",
    "luckmail_url": "https://mails.luckyous.com/",
    "luckmail_email_type": "ms_imap",
    # Gmail
    "gmail_user": "",
    "gmail_pass": "",
    # ---- SMS providers ----
    "sms_provider": "",
    "herosms_key": "",
    "herosms_country": "187",
    "herosms_service": "dr",
    # ---- Captcha ----
    "yescaptcha_key": "",
    # ---- Proxy ----
    "proxy_url": "",
    # ---- CPA / API aggregation ----
    "cpa_url": "",
    "cpa_key": "",
    # ---- Registration ----
    "default_platform": "chatgpt",
    "registration_mode": "at",  # "at" or "rt"
    "account_count": 1,
    "concurrency": 1,
}


class Config:
    """Typed access to configuration with env var override."""

    def __init__(self, path: Optional[Path] = None):
        self._file = path or DEFAULT_CONFIG_FILE
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load_file()
        self._apply_env()

    def _load_file(self) -> None:
        if self._file.exists():
            try:
                self._data.update(json.loads(self._file.read_text(encoding="utf-8")))
            except Exception:
                pass

    def _apply_env(self) -> None:
        prefix = "GPT_FARM_"
        for key in list(self._data.keys()):
            env_key = prefix + key.upper()
            if env_key in os.environ:
                val = os.environ[env_key]
                # Coerce booleans/ints
                if val.lower() in ("true", "false"):
                    self._data[key] = val.lower() == "true"
                elif val.isdigit():
                    self._data[key] = int(val)
                else:
                    self._data[key] = val

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        # Only save non-default values
        to_save = {k: v for k, v in self._data.items() if v and v != DEFAULTS.get(k)}
        self._file.write_text(json.dumps(to_save, indent=2, ensure_ascii=False), encoding="utf-8")

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def dump(self) -> dict[str, Any]:
        """Return full config dict (mask secrets for display)."""
        masked = dict(self._data)
        for k in masked:
            val = masked[k]
            if isinstance(val, str) and len(val) > 8 and any(
                secret in k.lower()
                for secret in ("key", "pass", "password", "secret", "token")
            ):
                masked[k] = val[:4] + "****" + val[-4:]
        return masked


# Global config instance — init on first import
config = Config()
