from eppclient.epp_contacts import epp_contacts_Transfer
from models import ContactTransfer
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import rpp_operation
from .transfer_handlers import TransferHandlers

_handlers = TransferHandlers(
    run=epp_contacts_Transfer,
    create_mapper=rpp_mapper.contact_transfer_process.rpp_to_model,
    approve_mapper=rpp_mapper.contact_transfer_approve.rpp_to_model,
    reject_mapper=rpp_mapper.contact_transfer_reject.rpp_to_model,
    response_mapper=rpp_mapper.contact_transfer_process.model_to_rpp,
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
