from core.model.contact import contact_application
from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contacts import Contact, ContactType
from core.ports import derived_update
from core.ports.replace_outcome import ReplaceOutcome
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.contact.check import rri_contact_check
from registry_adapter.rri.commands.contact.create import rri_contact_create
from registry_adapter.rri.commands.contact.info import rri_contact_info
from registry_adapter.rri.commands.contact.update import rri_contact_update, same_contact
from registry_adapter.rri.commands.shared.rri_command import refused

AUTH_INFO = "authInfo"


def _no_auth_info(client_transaction_id) -> ErrorResponse:
    return refused(ResultCode.UNIMPLEMENTED_OPTION, "RRI holds no authInfo for a contact", client_transaction_id)


def _cleared(stored: Contact, wanted: ContactReplacement) -> str | None:
    """What RRI requires of a PERSON or ORG and so cannot clear: the name, the address, the email and the phone."""
    for member, label in (("name", "the name"), ("address", "the address"), ("email", "the email"),
                          ("phone", "the phone number")):
        if getattr(stored, member) and not getattr(wanted, member):
            return f"Removing {label} cannot be expressed in RRI"
    return None


def _name(stored: Contact, contact_type: ContactType) -> str:
    """The name RRI holds: an ORG's is its organisation's."""
    return stored.organisationName or stored.name if contact_type == ContactType.ORG else stored.name


class RriContactGateway:
    """The contact commands of RRI. A contact is updated only by replacing it, and cannot be deleted or
    transferred."""

    def __init__(self, client):
        self.client = client

    def check(self, id, client_transaction_id=None):
        return rri_contact_check(self.client, id, client_transaction_id)

    def info(self, id, client_transaction_id=None):
        return rri_contact_info(self.client, id, client_transaction_id)

    def create(self, contact: Contact, client_transaction_id=None):
        if contact.authInfo is not None and (contact.authInfo.pw or contact.authInfo.hash):
            return _no_auth_info(client_transaction_id)
        created = rri_contact_create(self.client, contact, client_transaction_id)
        if isinstance(created, ErrorResponse):
            return created
        return OperationResponse(code=created.code, msg=created.msg,
                                 server_transaction_id=created.server_transaction_id,
                                 client_transaction_id=created.client_transaction_id, payload=Contact(id=contact.id))

    def update(self, update: ContactUpdate, client_transaction_id=None):
        return derived_update.update(self.info, contact_application.apply, self.replace, update.id, update,
                                     client_transaction_id, self.client.regacc_id)

    def replace(self, wanted: ContactReplacement, current: OperationResponse | None = None, client_transaction_id=None):
        """The native full update: one UPDATE with the verification data of the stored contact."""
        if AUTH_INFO not in wanted.unchanged and wanted.authInfo is not None and wanted.authInfo.pw:
            return _no_auth_info(client_transaction_id)
        if current is None:
            current = self.info(wanted.id)
            if isinstance(current, ErrorResponse):
                return current
        stored: Contact = current.payload
        # An RPP contact with an organisation is an ORG, which RRI names by the organisation only.
        contact_type = ContactType.ORG if wanted.organisationName else ContactType.PERSON
        if contact_type == ContactType.ORG and wanted.name and wanted.name != wanted.organisationName:
            return refused(ResultCode.UNIMPLEMENTED_OPTION,
                           "The name of a person in the contact of an organisation cannot be expressed in RRI",
                           client_transaction_id)
        if stored.name and wanted.name and _name(stored, contact_type) != wanted.name:
            return refused(ResultCode.UNIMPLEMENTED_OPTION, "Changing the name of a contact cannot be expressed in RRI",
                           client_transaction_id)
        cleared = _cleared(stored, wanted)
        if cleared:
            return refused(ResultCode.UNIMPLEMENTED_OPTION, cleared, client_transaction_id)
        if contact_type == stored.type and same_contact(wanted.id, stored.type, wanted, stored):
            return ReplaceOutcome(current=current)
        mutation = rri_contact_update(self.client, wanted.id, contact_type, wanted, stored.carried_over,
                                      client_transaction_id)
        if isinstance(mutation, ErrorResponse):
            return mutation
        return ReplaceOutcome(current=current, update=wanted, mutation=mutation)

    def delete(self, id, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI cannot delete a contact", client_transaction_id)

    def transfer(self, transfer, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI has no contact transfer", client_transaction_id)
