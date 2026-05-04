"""Email providers — each file is one provider implementation."""

from .base import BaseEmailProvider, EmailAccount
from .gmail import GmailProvider
from .luckmail import LuckMailProvider

__all__ = ["BaseEmailProvider", "EmailAccount", "GmailProvider", "LuckMailProvider"]

_registry: dict[str, type[BaseEmailProvider]] = {}


def register(name: str):
    """Decorator: register an email provider class by name."""
    def wrapper(cls):
        cls.name = name
        _registry[name] = cls
        return cls
    return wrapper


def get(name: str, **kwargs) -> BaseEmailProvider:
    """Factory: create an email provider by name."""
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(f"Unknown email provider: {name}")
    return cls(**kwargs)


def list_providers() -> list[str]:
    return sorted(_registry.keys())


# Auto-register built-in providers
register("gmail")(GmailProvider)
register("luckmail")(LuckMailProvider)
