"""Base interface for email providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class EmailAccount:
    email: str
    # Callable that blocks until a 6-digit code is received
    wait_for_code: Callable[[int], Optional[str]]


class BaseEmailProvider(ABC):
    """Abstract email provider.

    Each implementation must provide create() which returns an
    EmailAccount with a ready-to-use email address and a code fetcher.
    """

    name: str = "base"

    @abstractmethod
    def create(self) -> EmailAccount:
        """Create a new email address and return it with a code fetcher."""
        ...

    def validate(self) -> bool:
        """Check that the provider is properly configured."""
        return True
