import json

from connexion import request
from flask import request as flask_request
from models import ErrorResponse, ResultCode, TransferOperation
import rpp_to_model_mapper as rpp_mapper
from .helper.rpp_response import (
    client_transaction_id, generate_rpp_response_headers, map_request, raise_epp_error, request_has_content,
    require_empty_body,
)
from .auth import get_epp_client

LATEST = "latest"


class TransferHandlers:
    """The operations on the transfer of one kind of object, which EPP runs with one command.

    `run(epp_client, transfer, client_transaction_id=...)` runs a transfer, `create_mapper`,
    `approve_mapper` and `reject_mapper` convert a request, `response_mapper` a process, and `make_transfer(id, operation,
    auth_info)` builds a transfer without content.
    """

    def __init__(self, run, create_mapper, approve_mapper, reject_mapper, response_mapper, make_transfer):
        self._run_epp = run
        self._create_mapper = create_mapper
        self._approve_mapper = approve_mapper
        self._reject_mapper = reject_mapper
        self._response_mapper = response_mapper
        self._make_transfer = make_transfer

    @staticmethod
    def _authorization():
        return request.headers.get("RPP-Authorization")

    def _run(self, transfer):
        resp = self._run_epp(get_epp_client(), transfer, client_transaction_id=client_transaction_id())
        if isinstance(resp, ErrorResponse):
            raise_epp_error(resp)
        return resp

    def _process(self, transfer):
        resp = self._run(transfer)
        if resp.transfer is None:
            if transfer.operation == TransferOperation.QUERY:  # nothing was applied, so there is nothing to confirm
                raise_epp_error(ErrorResponse(
                    code=ResultCode.COMMAND_FAILED,
                    msg="The EPP server gave no transfer state",
                    server_transaction_id=resp.server_transaction_id,
                    client_transaction_id=resp.client_transaction_id,
                ))
            return None, 202, generate_rpp_response_headers(resp)  # applied, but EPP gave no state to show
        return self._response_mapper(resp.transfer), 200, generate_rpp_response_headers(resp)

    def _operation(self, id, operation):
        auth_info = map_request(rpp_mapper.rpp_authorization.rpp_to_model, self._authorization())
        return self._process(self._make_transfer(id, operation, auth_info))

    def create(self, id, body):
        resp = self._run(map_request(self._create_mapper, id, body, self._authorization()))
        headers = generate_rpp_response_headers(resp)
        if resp.transfer is None:  # applied, but EPP gave no state to show
            return None, 202, headers
        process = self._response_mapper(resp.transfer)
        if resp.code != ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
            return process, 200, headers  # completed at once: EPP exposes no process (core §16.1.4)
        return process, 201, {**headers, "Location": f"{str(request.url).rstrip('/')}/{LATEST}"}

    def read(self, id):
        return self._operation(id, TransferOperation.QUERY)

    def delete(self, id):
        require_empty_body()
        return self._operation(id, TransferOperation.CANCEL)

    @staticmethod
    def _optional_body():
        """The OpenAPI declares no body for approve, so Connexion does not read it: None for none.

        Content is not none because it parses to nothing (`null`) or leaves no raw bytes (a form).
        """
        if not request_has_content():
            return None
        raw = flask_request.get_data()
        if not raw:
            raise ValueError("Request body must be JSON")
        body = json.loads(raw)
        if body is None:
            raise ValueError("Request body must be an object")
        return body

    def approve(self, id):
        body = map_request(self._optional_body)
        return self._process(map_request(self._approve_mapper, id, body, self._authorization()))

    def reject(self, id, body):
        return self._process(map_request(self._reject_mapper, id, body, self._authorization()))
