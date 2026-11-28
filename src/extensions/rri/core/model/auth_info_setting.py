from dataclasses import dataclass
from datetime import date


@dataclass(kw_only=True)
class AuthInfoSetting:
    """A request to set the authorisation information of a domain name. The password is a secret: it is never logged
    and never read back."""
    name: str
    password: str
    expiry_date: date | None = None

    def __repr__(self) -> str:
        return f"AuthInfoSetting(name={self.name!r}, expiry_date={self.expiry_date!r})"
