from connexion import ProblemException
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from connexion.problem import problem

from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from rpp.http.headers import problem_headers


RPP_ERROR_TYPE = "urn:ietf:params:rpp:error"

# Core §18.1 Table 9, for the codes the proxy can receive or produce.
STATUS_BY_RESULT = {
    ResultCode.COMMAND_USE_ERROR: 409,
    ResultCode.UNIMPLEMENTED_COMMAND: 501,
    ResultCode.UNIMPLEMENTED_OPTION: 501,
    ResultCode.UNIMPLEMENTED_EXTENSION: 501,
    ResultCode.BILLING_FAILURE: 402,
    ResultCode.OBJECT_NOT_ELIGIBLE_FOR_RENEWAL: 409,
    ResultCode.OBJECT_NOT_ELIGIBLE_FOR_TRANSFER: 409,
    ResultCode.AUTHENTICATION_ERROR: 401,
    ResultCode.AUTHORIZATION_ERROR: 403,
    ResultCode.INVALID_AUTHORIZATION_INFORMATION: 401,
    ResultCode.OBJECT_PENDING_TRANSFER: 409,
    ResultCode.OBJECT_NOT_PENDING_TRANSFER: 409,
    ResultCode.OBJECT_EXISTS: 409,
    ResultCode.OBJECT_DOES_NOT_EXIST: 404,
    ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION: 409,
    ResultCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION: 409,
    ResultCode.PARAMETER_VALUE_POLICY_ERROR: 422,
    ResultCode.UNIMPLEMENTED_OBJECT_SERVICE: 501,
    ResultCode.DATA_MANAGEMENT_POLICY_VIOLATION: 422,
    ResultCode.AUTHENTICATION_ERROR_SERVER_CLOSING_CONNECTION: 401,
    ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION: 429,
}


def http_status(code: ResultCode) -> int:
    """Core §18.1: Table 9, then the class mapping of Table 10."""
    if code in STATUS_BY_RESULT:
        return STATUS_BY_RESULT[code]
    return 500 if code.value[0][1] in ("4", "5") else 400


def raise_registry_error(resp: ErrorResponse):
    """Translates an error of the registry, or a refusal before any command, into a Problem Detail."""
    raise ProblemException(
        status=http_status(resp.code),
        title=resp.code.value[1],
        detail=resp.msg,
        headers=problem_headers(resp.code, resp.server_transaction_id),
    )


def _default_result(status: int) -> ResultCode:
    if status >= 500:
        return ResultCode.UNIMPLEMENTED_COMMAND if status == 501 else ResultCode.COMMAND_FAILED
    return ResultCode.AUTHENTICATION_ERROR if status == 401 else ResultCode.COMMAND_SYNTAX_ERROR


def handle_rpp_error(request: ConnexionRequest, exc: ProblemException) -> ConnexionResponse:
    """Renders every error as a core §9 Problem Detail with the RPP response headers."""
    headers = {**problem_headers(_default_result(exc.status)), **(exc.headers or {})}
    if "RPP-Cltrid" in request.headers:
        headers["RPP-Cltrid"] = request.headers["RPP-Cltrid"]
    return problem(
        title=exc.title,
        detail=exc.detail,
        status=exc.status,
        type=RPP_ERROR_TYPE,
        instance=exc.instance,
        headers=headers,
        ext={"errors": [{
            "type": RPP_ERROR_TYPE,
            "result": headers["RPP-Code"],
            "reason": exc.detail or exc.title,
        }]},
    )
