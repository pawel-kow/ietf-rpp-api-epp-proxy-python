from extensions.rri.core.model.request_contact import RequestContact
from core.ports.replace_outcome import ReplaceOutcome
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.contact.check import rri_contact_check
from registry_adapter.rri.extensions.rri.commands.request_contact.create import rri_request_contact_create
from registry_adapter.rri.extensions.rri.commands.request_contact.info import rri_request_contact_info
from registry_adapter.rri.extensions.rri.commands.request_contact.update import rri_request_contact_update
from registry_adapter.rri.commands.shared.rri_command import refused


class RriRequestContactGateway:
    """The request contacts of RRI: contacts of type REQUEST, the General Request and Abuse contacts of a domain. They
    share their handles with the other contacts, so a check of one is a contact CHECK. RRI updates one only by
    replacing it, and cannot delete one."""

    def __init__(self, client):
        self.client = client

    def check(self, id, client_transaction_id=None):
        return rri_contact_check(self.client, id, client_transaction_id)

    def info(self, id, client_transaction_id=None):
        return rri_request_contact_info(self.client, id, client_transaction_id)

    def create(self, contact: RequestContact, client_transaction_id=None):
        created = rri_request_contact_create(self.client, contact, client_transaction_id)
        if isinstance(created, ErrorResponse):
            return created
        return OperationResponse(code=created.code, msg=created.msg,
                                 server_transaction_id=created.server_transaction_id,
                                 client_transaction_id=created.client_transaction_id,
                                 payload=RequestContact(id=contact.id))

    def replace(self, wanted: RequestContact, current: OperationResponse | None = None, client_transaction_id=None):
        """The native full update: one UPDATE, none when the template is the stored one."""
        if current is None:
            current = self.info(wanted.id)
            if isinstance(current, ErrorResponse):
                return current
        if wanted.uriTemplate == current.payload.uriTemplate:
            return ReplaceOutcome(current=current)
        mutation = rri_request_contact_update(self.client, wanted, client_transaction_id)
        if isinstance(mutation, ErrorResponse):
            return mutation
        return ReplaceOutcome(current=current, update=wanted, mutation=mutation)

    def delete(self, id, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI cannot delete a contact", client_transaction_id)
