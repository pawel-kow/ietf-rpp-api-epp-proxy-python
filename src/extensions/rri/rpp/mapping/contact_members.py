"""The verification information of a contact: the member the rri extension adds to it (`verifications`,
docs/rri/rri-extension.md). The model holds it as the `ContactVerifications` of the extension's entry of `Contact.extensions`."""
from core.model.contact.contacts import Contact
from extensions.rri.core.model.contact_verifications import ContactVerifications
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from extensions.rri.rpp.mapping import verification_information

MEMBER = "verifications"


class ContactVerificationMembers:
    """The mapper of the rri extension for the members of a contact (`CONTACT_MEMBERS`)."""
    extension_id = EXTENSION_ID
    members = (MEMBER,)
    array_members = (MEMBER,)

    def to_model(self, present: dict) -> dict:
        """The records a request states; a request without the member states none, which removes the stored ones."""
        records = [verification_information.rpp_to_model(entry) for entry in present.get(MEMBER) or []]
        return {EXTENSION_ID: ContactVerifications(blocks=records)}

    def to_rpp(self, contact: Contact) -> dict:
        """The records a contact has (none: no member)."""
        held = contact.extensions.get(EXTENSION_ID)
        if not isinstance(held, ContactVerifications) or not held.blocks:
            return {}
        return {MEMBER: [verification_information.model_to_dto(record).to_rpp() for record in held.blocks]}
