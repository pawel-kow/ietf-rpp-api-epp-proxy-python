from models import (
    Contact, ContactUpdate, ContactUpdateChange, ContactUpdateChanges, LocalizedPostalInfo, PostalInfoChange,
)
from .not_supported_by_epp import NotSupportedByEpp
from .patch_statuses import is_client_label

INT = "int"
LOC = "loc"
CLEAR = ""  # an empty element clears what EPP lets a client clear (RFC 5733 chgPostalInfoType, e164Type)


def _client_statuses(contact: Contact) -> dict[str, str | None]:
    return {
        label: (contact.status_reasons.get(label) or None)
        for label in contact.status or [] if is_client_label(label)
    }


def _status_changes(current: Contact, wanted: Contact) -> tuple[ContactUpdateChanges | None, ContactUpdateChanges | None]:
    """The client statuses are a set, compared by label. EPP cannot change a reason, so it is removed and added again."""
    before, after = _client_statuses(current), _client_statuses(wanted)
    new_reason = {label for label in before.keys() & after.keys() if before[label] != after[label]}
    add = sorted(after.keys() - before.keys() | new_reason)
    remove = sorted(before.keys() - after.keys() | new_reason)
    added = ContactUpdateChanges(status=add, status_reasons={label: after[label] for label in add if after[label]})
    return added or None, ContactUpdateChanges(status=remove) or None


def _form(current: Contact) -> tuple:
    return current.name, current.organisationName, current.address


def loc_matches_card(current: Contact) -> bool:
    """A localization equal to the card reads back as none, see `contacts._localizations_to_rpp`."""
    return current.localizedPostalInfo == LocalizedPostalInfo(
        name=current.name, organisationName=current.organisationName, address=current.address,
    )


def _int_change(current: Contact, wanted: Contact) -> PostalInfoChange | None:
    if current.name and not wanted.name:
        raise NotSupportedByEpp("Removing the name")
    if current.address and not wanted.address:
        raise NotSupportedByEpp("Removing the address")
    if _form(current) == _form(wanted):
        return None
    organisation = wanted.organisationName or (CLEAR if current.organisationName else None)
    return PostalInfoChange(form=INT, name=wanted.name, organisationName=organisation, address=wanted.address)


def _loc_change(current: Contact, wanted: Contact) -> PostalInfoChange | None:
    before, after = current.localizedPostalInfo, wanted.localizedPostalInfo
    if after is None and before is not None:
        if not loc_matches_card(current):
            raise NotSupportedByEpp("Removing the localization")
        # Nothing reads back for it, so it follows the card and EPP is not asked to remove it.
        after = LocalizedPostalInfo(name=wanted.name, organisationName=wanted.organisationName, address=wanted.address)
    if after is None or after == before:
        return None
    organisation = after.organisationName or (CLEAR if before and before.organisationName else None)
    return PostalInfoChange(form=LOC, name=after.name, organisationName=organisation, address=after.address)


def _number(current: list[str] | None, wanted: list[str] | None) -> str | None:
    before, after = (current or [None])[0], (wanted or [None])[0]
    if before == after:
        return None
    return after if after else CLEAR


def _email(current: Contact, wanted: Contact) -> str | None:
    before, after = (current.email or [None])[0], (wanted.email or [None])[0]
    if before and not after:
        raise NotSupportedByEpp("Removing the email")
    return after if after != before else None


def difference(contact_id: str, current: Contact, wanted: Contact) -> ContactUpdate:
    """The update that turns the current contact into the wanted one. A `None` that EPP cannot clear is refused.

    Every form that differs is sent complete. `authInfo` is sent whenever the wanted contact has one.
    """
    forms = [form for form in (_int_change(current, wanted), _loc_change(current, wanted)) if form]
    change = ContactUpdateChange(
        postal_info=forms,
        voice=_number(current.phone, wanted.phone),
        fax=_number(current.fax, wanted.fax),
        email=_email(current, wanted),
        authInfo=wanted.authInfo,
    )
    add, remove = _status_changes(current, wanted)
    return ContactUpdate(id=contact_id, add=add, remove=remove, change=change or None)
