import base64
import binascii

from models import AuthInfo
from .auth_info import AUTHINFO_METHOD
from .not_supported_by_backend import NotSupportedByBackend

MALFORMED = "Malformed RPP-Authorization header"


def _fields(text: str) -> dict[str, str]:
    fields = {}
    for field in text.split(","):
        name, separator, value = field.strip().partition("=")
        if not separator or name not in ("value", "roid") or name in fields:
            raise ValueError(MALFORMED)
        fields[name] = value
    return fields


def _password(value: str | None) -> str:
    """The messages leave the value out: it is a secret, even when malformed."""
    if not value:
        raise ValueError(MALFORMED)
    try:
        return base64.b64decode(value, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError(MALFORMED) from None


def rpp_to_model(header: str | None) -> AuthInfo | None:
    """Converts `authinfo value=<base64>, roid=<roid>` (core §6.1)."""
    if header is None:
        return None
    method, _, text = header.strip().partition(" ")
    if method != AUTHINFO_METHOD:
        raise NotSupportedByBackend(f"RPP-Authorization method '{method}'")
    fields = _fields(text)
    return AuthInfo(pw=_password(fields.get("value")), roid=fields.get("roid"))
