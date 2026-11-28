from dataclasses import dataclass


@dataclass(kw_only=True)
class Release:
    """The release of a domain name to the registry: whether the name servers are kept (the registry otherwise replaces them)."""
    keep_nameservers: bool = True
