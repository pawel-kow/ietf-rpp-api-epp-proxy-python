from core.capabilities.backend_profile import BackendProfile
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contacts import ContactType


def check_contact(contact, *, profile: BackendProfile):
    """Refuses what the backend cannot hold of a contact (`profile`): a fax number, a localized form, a region, more
    voice numbers than it holds, an organisation on an individual, the name of a person on an organisation, an authInfo, a
    client status. `contact` is a `Contact` or a `ContactReplacement`; None passes."""
    if contact is None:
        return contact
    if not profile.contact.fax.supported and any(contact.fax or []):
        raise NotSupportedByBackend("A fax number")
    if not profile.contact.localization.supported and contact.localizedPostalInfo is not None:
        raise NotSupportedByBackend("A localized form of a contact")
    if not profile.contact.region.supported and contact.address is not None and contact.address.stateProvince:
        raise NotSupportedByBackend("The region of an address")
    if len([phone for phone in contact.phone or [] if phone]) > profile.contact.phone.max_count:
        raise NotSupportedByBackend(f"More than {profile.contact.phone.max_count} voice numbers")
    localized = contact.localizedPostalInfo
    if not profile.contact.kind.supported and getattr(contact, "type", None) == ContactType.PERSON \
            and (contact.organisationName or (localized is not None and localized.organisationName)):
        raise NotSupportedByBackend("'organizations' on an individual")
    if not profile.contact.org.person_name_supported and getattr(contact, "type", None) == ContactType.ORG \
            and contact.name and contact.organisationName and contact.name != contact.organisationName:
        raise NotSupportedByBackend("The name of a person in the contact of an organisation")
    if not profile.contact.authInfo.supported and contact.authInfo is not None and (contact.authInfo.pw or contact.authInfo.hash):
        raise NotSupportedByBackend("The authInfo of a contact")
    if not profile.contact.status.client_supported and any(label != "ok" for label in contact.status or []):
        raise NotSupportedByBackend("A client status")
    return contact


def check_contact_update(update: ContactUpdate | None, *, profile: BackendProfile):
    """The same for a partial update, which names only its changes."""
    if update is None:
        return update
    if not isinstance(update, ContactUpdate):  # a patch the mapper turned into a replacement
        return check_contact(update, profile=profile)
    change = update.change
    if change is not None:
        if not profile.contact.authInfo.supported and change.authInfo:
            raise NotSupportedByBackend("The authInfo of a contact")
        if not profile.contact.fax.supported and change.fax:
            raise NotSupportedByBackend("A fax number")
        for form in change.postal_info:
            if not profile.contact.localization.supported and form.form == "loc":
                raise NotSupportedByBackend("A localized form of a contact")
            if not profile.contact.region.supported and form.address is not None and form.address.stateProvince:
                raise NotSupportedByBackend("The region of an address")
    if not profile.contact.status.client_supported and ((update.add and update.add.status) or (update.remove and update.remove.status)):
        raise NotSupportedByBackend("A client status")
    return update
