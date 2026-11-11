from dataclasses import dataclass


@dataclass(kw_only=True)
class KeyData:
    """A DNSKEY record (RFC 5910 keyData)."""
    flags: int
    protocol: int
    algorithm: int
    publicKey: str
