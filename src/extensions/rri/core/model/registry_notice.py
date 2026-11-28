from dataclasses import dataclass


@dataclass(kw_only=True)
class RegistryNotice:
    """A notice of the registry about the event a message reports: its code, human-readable text and the values that complete it."""
    code: str
    text: str
    arguments: tuple[str, ...] = ()
