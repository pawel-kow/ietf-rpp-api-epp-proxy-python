from core.capabilities.backend_profile import BackendProfile
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.contact.contact_update import ContactUpdate


def check_contact(contact, *, profile: BackendProfile):
    """Refuses what the backend cannot hold of a contact (`profile`): a fax number, a localized form, a region, more
    voice numbers than it holds, an authInfo, a client status. `contact` is a `Contact` or a `ContactReplacement`; None passes."""
    if contact is None:
        return contact
    if not profile.contact_fax and any(contact.fax or []):
        raise NotSupportedByBackend("A fax number")
    if not profile.contact_localization and contact.localizedPostalInfo is not None:
        raise NotSupportedByBackend("A localized form of a contact")
    if not profile.contact_region and contact.address is not None and contact.address.stateProvince:
        raise NotSupportedByBackend("The region of an address")
    if len([phone for phone in contact.phone or [] if phone]) > profile.contact_phones_max:
        raise NotSupportedByBackend(f"More than {profile.contact_phones_max} voice numbers")
    if not profile.contact_auth_info and contact.authInfo is not None and (contact.authInfo.pw or contact.authInfo.hash):
        raise NotSupportedByBackend("The authInfo of a contact")
    if not profile.client_statuses and any(label != "ok" for label in contact.status or []):
        raise NotSupportedByBackend("A client status")
    return contact


def check_contact_update(update: ContactUpdate | None, *, profile: BackendProfile):
    """The same for a partial update, which names only its changes."""
    if update is None:
        return update
    change = update.change
    if change is not None:
        if not profile.contact_auth_info and change.authInfo:
            raise NotSupportedByBackend("The authInfo of a contact")
        if not profile.contact_fax and change.fax:
            raise NotSupportedByBackend("A fax number")
        for form in change.postal_info:
            if not profile.contact_localization and form.form == "loc":
                raise NotSupportedByBackend("A localized form of a contact")
            if not profile.contact_region and form.address is not None and form.address.stateProvince:
                raise NotSupportedByBackend("The region of an address")
    if not profile.client_statuses and ((update.add and update.add.status) or (update.remove and update.remove.status)):
        raise NotSupportedByBackend("A client status")
    return update
