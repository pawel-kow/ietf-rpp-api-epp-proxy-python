"""regacc INFO ↔ the organisation model (docs/rri/rri-extension.md, "Mapping of regacc INFO")."""
import logging
import re

from core.model.contact.address import Address
from core.model.organisation.organisation import Organisation
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.xml.generated import regacc_5_0 as rri

logger = logging.getLogger(__name__)

# The status and the role of a RegAcc: RRI holds neither, so the registrar is `ok` (docs/rri/rri-extension.md).
STATUS = ["ok"]
REGISTRAR = "registrar"

SEPARATORS = re.compile(r"[/\-.\s]")
SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*:")

MAX_COUNTRY_DIGITS = 3
MAX_NUMBER_DIGITS = 14
MAX_DIGITS = 15


def dotted(number: str) -> str | None:
    """`+49 69 27 235 0` as `+49.69272350`, `+1 703 555 5555 x12` as `+1.7035555555x12`: the digits before the first separator
    are the country code, the other digits before an `x` the subscriber number, those after it the extension. None for a number
    that gives none of this."""
    number = number.strip()
    body, has_extension, extension = number.partition("x")
    if has_extension and not extension.strip().isdigit():
        return None
    code, *rest = SEPARATORS.split(body.strip(), maxsplit=1)
    if not code.startswith("+") or not code[1:].isdigit() or not rest:
        return None
    subscriber = "".join(c for c in rest[0] if c.isdigit())
    if not (1 <= len(code) - 1 <= MAX_COUNTRY_DIGITS) or not (1 <= len(subscriber) <= MAX_NUMBER_DIGITS):
        return None
    if len(code) - 1 + len(subscriber) > MAX_DIGITS:
        return None
    return f"{code}.{subscriber}" + (f"x{extension.strip()}" if extension else "")


def _numbers(values, field_name: str) -> list[str]:
    kept = []
    for value in values:
        converted = dotted(value.value)
        if converted is None:
            logger.warning("regacc INFO: a %s is left out, it gives no international number", field_name)
        else:
            kept.append(converted)
    return kept


def _urls(values) -> list[str]:
    kept = []
    for value in values:
        if SCHEME.match(value.value):
            kept.append(value.value)
        else:
            logger.warning("regacc INFO: a url is left out, it has no scheme")
    return kept


def _address(postal: rri.PostalType) -> Address:
    return Address(street=[line.value for line in postal.address] or None, city=postal.city.value,
                   postalCode=postal.postal_code.value, country=postal.country_code.value)


def organisation_from_rri(data: rri.InfoData, parts) -> Organisation:
    """The organisation of a RegAcc. `parts` are the extension parts whose `organisation_members` give the members an extension
    adds (the request templates)."""
    member = data.memberacc
    return Organisation(
        id=data.handle, sponsor_id=data.handle, status=list(STATUS), roles={REGISTRAR: list(STATUS)},
        up_date=utc_time(data.changed),
        parent=member if member and member.upper() != data.handle.upper() else None,
        name=data.name.value, address=_address(data.postal),
        phones=_numbers(data.phone, "phone"), faxes=_numbers(data.fax, "fax"),
        email=data.email.value, urls=_urls(data.url),
        extensions={part.extension_id: part.organisation_members(data) for part in parts if part.organisation_members is not None},
    )
