"""SMS providers — phone verification for platform signup."""

from .base import BaseSmsProvider, SmsActivation
from .herosms import HeroSmsProvider

_registry: dict[str, type[BaseSmsProvider]] = {}


def register(name: str):
    def wrapper(cls):
        cls.name = name
        _registry[name] = cls
        return cls
    return wrapper


def get(name: str, **kwargs) -> BaseSmsProvider:
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(f"Unknown SMS provider: {name}")
    return cls(**kwargs)


def list_providers() -> list[str]:
    return sorted(_registry.keys())


register("herosms")(HeroSmsProvider)
