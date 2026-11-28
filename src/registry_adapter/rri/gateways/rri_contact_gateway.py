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


class RriContactGateway:
    """The contact commands of RRI. A contact is updated only by replacing it, and cannot be deleted or
    transferred."""

    def __init__(self, client, extension_parts=()):
        self.client = client
        # What the extensions add to the contact commands, by extension id (`RriExtensionPart.contact_members`).
        self._members = {part.extension_id: part.contact_members for part in extension_parts
                         if part.contact_members is not None}

    def check(self, id, client_transaction_id=None):
        return rri_contact_check(self.client, id, client_transaction_id)

    def info(self, id, client_transaction_id=None):
        return rri_contact_info(self.client, id, client_transaction_id, self._members)

    def _fields(self, extensions: dict) -> dict:
        """The fields of CREATE and UPDATE that the typed objects of the extensions state."""
        fields = {}
        for extension_id, members in self._members.items():
            if extension_id in extensions:
                fields.update(members.fields(extensions[extension_id]))
        return fields

    def _update_fields(self, wanted: ContactReplacement, stored: Contact) -> tuple[dict, dict | None]:
        """The fields an UPDATE sends and the form the stored contact is compared in. An extension the replacement does not
        state keeps what the registry holds (its INFO's blocks); one it states replaces it. The stored side is None where
        the registry's record cannot be put in the form of a request, so the UPDATE is sent."""
        sent = self._fields(wanted.extensions)
        if not sent:
            return {}, {}
        try:
            return sent, self._fields({key: value for key, value in stored.extensions.items() if key in wanted.extensions})
        except ValueError:
            return sent, None

    def create(self, contact: Contact, client_transaction_id=None):
        if contact.authInfo is not None and (contact.authInfo.pw or contact.authInfo.hash):
            return _no_auth_info(client_transaction_id)
        created = rri_contact_create(self.client, contact, client_transaction_id, self._fields(contact.extensions))
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
        # RPP cannot change a contact's kind, so the type RRI holds stays: an ORG is named by its organisation only.
        contact_type = stored.type
        if contact_type == ContactType.ORG and wanted.name and wanted.name != wanted.organisationName:
            return refused(ResultCode.UNIMPLEMENTED_OPTION,
                           "The name of a person in the contact of an organisation cannot be expressed in RRI",
                           client_transaction_id)
        sent, held = self._update_fields(wanted, stored)
        kept = list(stored.carried_over or [])
        if held is not None and same_contact(wanted.id, stored.type, wanted, stored, {"verification_information": kept, **sent},
                                             {"verification_information": kept, **held}):
            return ReplaceOutcome(current=current)
        mutation = rri_contact_update(self.client, wanted.id, contact_type, wanted, kept, client_transaction_id, sent)
        if isinstance(mutation, ErrorResponse):
            return mutation
        return ReplaceOutcome(current=current, update=wanted, mutation=mutation)

    def delete(self, id, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI cannot delete a contact", client_transaction_id)

    def transfer(self, transfer, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI has no contact transfer", client_transaction_id)
