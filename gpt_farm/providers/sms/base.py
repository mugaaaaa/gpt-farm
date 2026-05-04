"""Base interface for SMS providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SmsActivation:
    activation_id: str
    phone_number: str
    country: str = ""
    metadata: dict = field(default_factory=dict)


class BaseSmsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_number(self, *, service: str = "dr", country: str = "187") -> SmsActivation:
        """Rent a phone number for the given service."""
        ...

    @abstractmethod
    def wait_for_code(self, activation_id: str, *, timeout: int = 120) -> Optional[str]:
        """Wait for and return the SMS verification code."""
        ...

    def cancel(self, activation_id: str) -> bool:
        """Release the phone number."""
        return True

    def validate(self) -> bool:
        return True
