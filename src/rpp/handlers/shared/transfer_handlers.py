import json

from connexion import request
from flask import request as flask_request

from core.model.shared.transfer_operation import TransferOperation
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from rpp.http.context import backend_profile, get_backend
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers
from rpp.http.operation import map_request, request_has_content, require_empty_body
from rpp.http.problem import raise_registry_error
from rpp.mapping.shared import rpp_authorization

LATEST = "latest"


class TransferHandlers:
    """The operations on the transfer of one kind of object, which the backend runs with one command.

    `gateway_of(backend)` is the gateway of the object, whose `transfer` runs a transfer, `create_mapper`,
    `approve_mapper` and `reject_mapper` convert a request, `response_mapper` a process, and `make_transfer(id, operation,
    auth_info)` builds a transfer without content.
    """

    def __init__(self, gateway_of, create_mapper, approve_mapper, reject_mapper, response_mapper, make_transfer):
        self._gateway_of = gateway_of
        self._create_mapper = create_mapper
        self._approve_mapper = approve_mapper
        self._reject_mapper = reject_mapper
        self._response_mapper = response_mapper
        self._make_transfer = make_transfer

    @staticmethod
    def _authorization():
        return request.headers.get("RPP-Authorization")

    def _run(self, transfer):
        resp = self._gateway_of(get_backend()).transfer(transfer, client_transaction_id=client_transaction_id())
        if isinstance(resp, ErrorResponse):
            raise_registry_error(resp)
        return resp

    def _process(self, transfer):
        resp = self._run(transfer)
        if resp.payload is None:
            if transfer.operation == TransferOperation.QUERY:  # nothing was applied, so there is nothing to confirm
                raise_registry_error(ErrorResponse(
                    code=ResultCode.COMMAND_FAILED,
                    msg=f"The {backend_profile().name} server gave no transfer state",
                    server_transaction_id=resp.server_transaction_id,
                    client_transaction_id=resp.client_transaction_id,
                ))
            return None, 202, generate_rpp_response_headers(resp)  # applied, but the backend gave no state to show
        return self._response_mapper(resp.payload), 200, generate_rpp_response_headers(resp)

    def _operation(self, id, operation):
        auth_info = map_request(rpp_authorization.rpp_to_model, self._authorization())
        return self._process(self._make_transfer(id, operation, auth_info))

    def create(self, id, body):
        resp = self._run(map_request(self._create_mapper, id, body, self._authorization()))
        headers = generate_rpp_response_headers(resp)
        if resp.payload is None:  # applied, but the backend gave no state to show
            return None, 202, headers
        process = self._response_mapper(resp.payload)
        if resp.code != ResultCode.COMMAND_COMPLETED_ACTION_PENDING:
            return process, 200, headers  # completed at once: the backend exposes no process (core §16.1.4)
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
