import re

from core.model.contact.address import Address
from registry_adapter.epp.xml.generated.contact_1_0 import E164Type


def e164_of(value: str) -> E164Type:
    """Split an RPP phone string ('+1.7035555555x1234') into an EPP e164Type."""
    match = re.search(r"x(\d+)", value)
    if match:
        return E164Type(value=re.sub(r"x\d+", "", value).strip(), x=match.group(1))
    return E164Type(value=value)


def phone_of(e164):
    """Map an EPP e164Type back to the RPP phone string ('+1.703...x1234')."""
    if e164 is None or not e164.value:
        return None
    return [f"{e164.value}x{e164.x}" if e164.x else e164.value]


def address_of(postal) -> Address | None:
    if postal is None or postal.addr is None:
        return None
    a = postal.addr
    return Address(
        street=[line for line in a.street if line] or None,
        city=a.city or None,
        stateProvince=a.sp or None,
        postalCode=a.pc or None,
        country=a.cc or None,
    )
