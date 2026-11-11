from core.model.shared.client_statuses import client_statuses, status_changes
from core.model.shared.common import password_of
from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contact_update_change import ContactUpdateChange
from core.model.contact.contact_update_changes import ContactUpdateChanges
from core.model.contact.contacts import Contact
from core.model.contact.postal_info_change import PostalInfoChange
from core.model.shared.stated_members import stated

INT = "int"
LOC = "loc"
CLEAR = ""  # an empty value clears the organisation or a number (RFC 5733 chgPostalInfoType, e164Type)


def _status_changes(current: Contact, wanted: ContactReplacement) -> tuple[ContactUpdateChanges | None, ContactUpdateChanges | None]:
    after = client_statuses(wanted.status, wanted.status_reasons)
    add, remove = status_changes(client_statuses(current.status, current.status_reasons), after)
    added = ContactUpdateChanges(status=add, status_reasons={label: after[label] for label in add if after[label]})
    return added or None, ContactUpdateChanges(status=remove) or None


def _int_change(current: Contact, wanted: ContactReplacement) -> PostalInfoChange | None:
    if (current.name, current.organisationName, current.address) == (wanted.name, wanted.organisationName, wanted.address):
        return None
    organisation = wanted.organisationName or (CLEAR if current.organisationName else None)
    return PostalInfoChange(form=INT, name=wanted.name, organisationName=organisation, address=wanted.address)


def _loc_change(current: Contact, wanted: ContactReplacement) -> PostalInfoChange | None:
    before, after = current.localizedPostalInfo, wanted.localizedPostalInfo
    if after is None or after == before:
        return None
    organisation = after.organisationName or (CLEAR if before and before.organisationName else None)
    return PostalInfoChange(form=LOC, name=after.name, organisationName=organisation, address=after.address)


def _number(current: list[str] | None, wanted: list[str] | None) -> str | None:
    before, after = (current or [None])[0], (wanted or [None])[0]
    if before == after:
        return None
    return after if after else CLEAR


def _email(current: Contact, wanted: ContactReplacement) -> str | None:
    before, after = (current.email or [None])[0], (wanted.email or [None])[0]
    if before == after:
        return None
    return after if after else CLEAR


def difference(current: Contact, wanted: ContactReplacement) -> ContactUpdate:
    """The update that turns the current contact into the wanted one.

    Every form that differs is sent complete. A wanted localization of None leaves the stored one alone: removing a
    form is not an update, a backend that cannot do it refuses it before (`removes_the_localization`). The email ""
    clears it. A password that differs is sent; clearing one is not an update, a backend that cannot do it refuses it
    before.
    """
    wanted = stated(wanted, current)
    forms = [form for form in (_int_change(current, wanted), _loc_change(current, wanted)) if form]
    change = ContactUpdateChange(
        postal_info=forms,
        voice=_number(current.phone, wanted.phone),
        fax=_number(current.fax, wanted.fax),
        email=_email(current, wanted),
        authInfo=wanted.authInfo if wanted.authInfo and password_of(wanted) != password_of(current) else None,
    )
    add, remove = _status_changes(current, wanted)
    return ContactUpdate(id=wanted.id, add=add, remove=remove, change=change or None)


def changes_nothing(update: ContactUpdate) -> bool:
    return update.add is None and update.remove is None and update.change is None
