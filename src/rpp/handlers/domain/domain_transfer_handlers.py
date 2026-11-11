from core.model.domain.domain_transfer import DomainTransfer
from rpp.handlers.shared.transfer_handlers import TransferHandlers
from rpp.http.operation import rpp_operation
from rpp.mapping.domain import domain_transfer_approve, domain_transfer_process, domain_transfer_reject

_handlers = TransferHandlers(
    gateway_of=lambda backend: backend.domains,
    create_mapper=domain_transfer_process.rpp_to_model,
    approve_mapper=domain_transfer_approve.rpp_to_model,
    reject_mapper=domain_transfer_reject.rpp_to_model,
    response_mapper=domain_transfer_process.model_to_rpp,
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
