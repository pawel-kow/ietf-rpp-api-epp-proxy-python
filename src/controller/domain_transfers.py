from eppclient.epp_domains import epp_domains_Transfer
from models import DomainTransfer
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import rpp_operation
from .transfer_handlers import TransferHandlers

_handlers = TransferHandlers(
    run=epp_domains_Transfer,
    create_mapper=rpp_mapper.domain_transfer_process.rpp_to_model,
    reject_mapper=rpp_mapper.domain_transfer_reject.rpp_to_model,
    response_mapper=rpp_mapper.domain_transfer_process.model_to_rpp,
    make_transfer=lambda name, operation, auth_info: DomainTransfer(name=name, operation=operation, authInfo=auth_info),
)


@rpp_operation
def domainNameTransferProcesses_transferCreate(name, body):
    return _handlers.create(name, body)


@rpp_operation
def domainNameTransferProcesses_transferRead(name):
    return _handlers.read(name)


@rpp_operation
def domainNameTransferProcesses_transferDelete(name):
    return _handlers.delete(name)


@rpp_operation
def domainNameTransferProcesses_transferApprove(name):
    return _handlers.approve(name)


@rpp_operation
def domainNameTransferProcesses_transferReject(name, body=None):
    return _handlers.reject(name, body)
