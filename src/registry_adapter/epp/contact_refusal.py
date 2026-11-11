from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contacts import Contact
from core.model.shared import stated_members
from core.model.shared.common import password_of
from core.result.error_response import ErrorResponse
from registry_adapter.epp.refusals import not_supported_by_epp


def _removed(before, after) -> bool:
    return bool(before) and not after


def _localization_refusal(current: Contact, wanted: ContactReplacement) -> str | None:
    before, after = current.localizedPostalInfo, wanted.localizedPostalInfo
    if before is not None and after is None:
        return "Removing the localization"
    if before is None or after is None or after == before:
        return None
    if _removed(before.name, after.name):
        return "Removing the name of the localization"
    if _removed(before.address, after.address):
        return "Removing the address of the localization"
    return None


def refuse(current: Contact, wanted: ContactReplacement) -> ErrorResponse | None:
    """What RFC 5733 cannot clear: the name, the address, the email, a `postalInfo` form, and the `authInfo`."""
    wanted = stated_members.stated(wanted, current)
    if _removed(current.name, wanted.name):
        refusal = "Removing the name"
    elif _removed(current.address, wanted.address):
        refusal = "Removing the address"
    else:
        refusal = _localization_refusal(current, wanted)
    if refusal is None and _removed((current.email or [None])[0], (wanted.email or [None])[0]):
        refusal = "Removing the email"
    if refusal is None and _removed(password_of(current), password_of(wanted)):
        refusal = "Removing the 'authInfo'"
    return not_supported_by_epp(refusal) if refusal else None
