from core.model.contact.contact_transfer import ContactTransfer
from rpp.handlers.shared.transfer_handlers import TransferHandlers
from rpp.http.operation import rpp_operation
from rpp.mapping.contact import contact_transfer_approve, contact_transfer_process, contact_transfer_reject

_handlers = TransferHandlers(
    gateway_of=lambda backend: backend.contacts,
    operations_of=lambda profile: profile.contact.processes.transfer.operations,
    create_mapper=contact_transfer_process.rpp_to_model,
    approve_mapper=contact_transfer_approve.rpp_to_model,
    reject_mapper=contact_transfer_reject.rpp_to_model,
    response_mapper=contact_transfer_process.model_to_rpp,
    make_transfer=lambda id, operation, auth_info: ContactTransfer(id=id, operation=operation, authInfo=auth_info),
)


@rpp_operation
def contactTransferProcesses_transferCreate(id, body):
    return _handlers.create(id, body)


@rpp_operation
def contactTransferProcesses_transferRead(id):
    return _handlers.read(id)


@rpp_operation
def contactTransferProcesses_transferDelete(id):
    return _handlers.delete(id)


@rpp_operation
def contactTransferProcesses_transferApprove(id):
    return _handlers.approve(id)


@rpp_operation
def contactTransferProcesses_transferReject(id, body=None):
    return _handlers.reject(id, body)
