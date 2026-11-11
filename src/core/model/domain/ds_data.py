from dataclasses import dataclass


@dataclass(kw_only=True)
class DsData:
    """A delegation signer record (RFC 5910 dsData)."""
    keyTag: int
    algorithm: int
    digestType: int
    digest: str
