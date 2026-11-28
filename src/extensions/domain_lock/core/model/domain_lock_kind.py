from enum import Enum


class DomainLockKind(Enum):
    """What happened to the lock of a domain name, with the identifier of the message type that reports it."""
    LOCKED = "domainLockMessage"
    UNLOCKED = "domainUnlockMessage"
