from dataclasses import dataclass
from datetime import date


@dataclass(kw_only=True)
class AuthInfoProcess:
    """The authorisation information a registrar set for a domain name, as the registry reports it: the last day it is
    valid (None where the registry does not say) and the sponsor of the domain, which a read checks."""
    sponsor_id: str | None = None
    expiry_date: date | None = None
