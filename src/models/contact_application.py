from .auth_info_intent import AuthInfoIntent
from .client_statuses import client_statuses
from .contact_difference import INT, LOC
from .contact_replacement import ContactReplacement
from .contact_update import ContactUpdate
from .contacts import Contact
from .localized_postal_info import LocalizedPostalInfo


def _value(current: list[str] | None, change: str | None) -> list[str] | None:
    """A changed value replaces the current one, "" clears it, None leaves it."""
    if change is None:
        return current
    return [change] if change else None


def apply(current: Contact, delta: ContactUpdate) -> ContactReplacement:
    """The contact the update asks for: the current contact with the changes of the update. A form in the update
    replaces the stored one, and an organisation "" clears it."""
    change = delta.change
    wanted = ContactReplacement(
        id=delta.id,
        name=current.name,
        organisationName=current.organisationName,
        email=current.email,
        phone=current.phone,
        fax=current.fax,
        address=current.address,
        localizedPostalInfo=current.localizedPostalInfo,
    )
    for form in change.postal_info if change else []:
        if form.form == INT:
            wanted.name, wanted.organisationName, wanted.address = form.name, form.organisationName or None, form.address
        elif form.form == LOC:
            wanted.localizedPostalInfo = LocalizedPostalInfo(
                name=form.name, organisationName=form.organisationName or None, address=form.address,
            )
    if change:
        wanted.phone, wanted.fax = _value(current.phone, change.voice), _value(current.fax, change.fax)
        wanted.email = _value(current.email, change.email)
        if change.authInfo:
            wanted.auth_info = AuthInfoIntent.set(change.authInfo)
    statuses = client_statuses(current.status, current.status_reasons)
    for label in delta.remove.status if delta.remove else []:
        statuses.pop(label, None)
    for label in delta.add.status if delta.add else []:
        statuses[label] = delta.add.status_reasons.get(label) or None
    wanted.status = list(statuses)
    wanted.status_reasons = {label: reason for label, reason in statuses.items() if reason}
    return wanted
