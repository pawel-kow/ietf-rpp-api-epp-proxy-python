from connexion import request
from eppclient.epp_domains import *
from models import *
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import *
from .auth import get_epp_client

LATEST = "latest"


def _authorization():
    return request.headers.get("RPP-Authorization")


def _run(transfer):
    resp = epp_domains_Transfer(get_epp_client(), transfer, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_epp_error(resp)
    return resp


def _process(transfer):
    resp = _run(transfer)
    return rpp_mapper.domain_transfer_process.model_to_rpp(resp.transfer), 200, generate_rpp_response_headers(resp)


def _operation(name, operation):
    auth_info = map_request(rpp_mapper.rpp_authorization.rpp_to_model, _authorization())
    return _process(DomainTransfer(name=name, operation=operation, authInfo=auth_info))


@rpp_operation
def domainNameTransferProcesses_transferCreate(name, body):
    resp = _run(map_request(rpp_mapper.domain_transfer_process.rpp_to_model, name, body, _authorization()))
    process = rpp_mapper.domain_transfer_process.model_to_rpp(resp.transfer)
    headers = generate_rpp_response_headers(resp)
    if resp.code != ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
        return process, 200, headers  # completed at once: EPP exposes no process (core §16.1.4)
    return process, 201, {**headers, "Location": f"{str(request.url).rstrip('/')}/{LATEST}"}


@rpp_operation
def domainNameTransferProcesses_transferRead(name):
    return _operation(name, TransferOperation.QUERY)


@rpp_operation
def domainNameTransferProcesses_transferDelete(name):
    require_empty_body()
    return _operation(name, TransferOperation.CANCEL)


@rpp_operation
def domainNameTransferProcesses_transferApprove(name):
    return _operation(name, TransferOperation.APPROVE)


@rpp_operation
def domainNameTransferProcesses_transferReject(name, body=None):
    return _process(map_request(rpp_mapper.domain_transfer_reject.rpp_to_model, name, body, _authorization()))
