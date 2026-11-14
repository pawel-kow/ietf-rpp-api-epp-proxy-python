"""DENIC message codes → `ResultCode` (docs/rri/gap-analysis.md §5).

An RRI code has 11 digits, `A B CCC DDDDDD`: its class, interface, module and code. A refusal is mapped by the code
of its first error message through `CODES`, and a code not in it by its class: 6 is a permanent error of the request,
5 a temporary one of the registry, 7 and 8 technical.
"""
from core.result.result_code import ResultCode

CODES = {
    "83000000010": ResultCode.AUTHENTICATION_ERROR,  # login failed
    "63100020005": ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,  # login blocked
    "73100000005": ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,  # too many sessions
    "63300022003": ResultCode.AUTHORIZATION_ERROR,  # domain of another provider
    "63200020603": ResultCode.AUTHORIZATION_ERROR,  # contact of another provider
    "63300062009": ResultCode.OBJECT_DOES_NOT_EXIST,  # domain does not exist
    "63300062010": ResultCode.OBJECT_DOES_NOT_EXIST,  # RegAcc does not exist
    "63310062004": ResultCode.OBJECT_EXISTS,  # domain exists
    "56310082011": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,  # domain in redemption period
    "66310082014": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,  # RESTORE of a domain not in redemption period
    "53000080009": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,  # locked
    "53000080011": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,  # dispute
    "63370088701": ResultCode.INVALID_AUTHORIZATION_INFORMATION,  # AuthInfo does not match
    "56000088709": ResultCode.INVALID_AUTHORIZATION_INFORMATION,  # AuthInfo2 does not exist
    "63380063209": ResultCode.COMMAND_USE_ERROR,  # CHPROV of an own domain
    "63391068704": ResultCode.OBJECT_EXISTS,  # AuthInfo1 exists
    "63393068704": ResultCode.OBJECT_EXISTS,  # AuthInfo2 exists
    "63392068709": ResultCode.OBJECT_DOES_NOT_EXIST,  # AuthInfo1 does not exist
    "63220080801": ResultCode.PARAMETER_VALUE_POLICY_ERROR,  # name immutable
    "53000080002": ResultCode.PARAMETER_VALUE_POLICY_ERROR,  # value cannot be deleted
    "63650063607": ResultCode.OBJECT_DOES_NOT_EXIST,  # not the oldest message
    "63650063609": ResultCode.OBJECT_DOES_NOT_EXIST,  # message id does not exist
    "53000060009": ResultCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION,  # a contact does not exist
    "63300080700": ResultCode.PARAMETER_VALUE_POLICY_ERROR,  # contact of the wrong type for its role
    "53000000008": ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,  # daily quota exceeded
    "56000020021": ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,  # ACL exceeded
    "55000000002": ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,  # ACL exceeded (ACL page)
    # Concurrent write on the same object (gap Q19): a status a client may retry.
    "53000000012": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,
    "63000060504": ResultCode.PARAMETER_VALUE_POLICY_ERROR,  # CTID used before
    "53300062003": ResultCode.PARAMETER_VALUE_SYNTAX_ERROR,  # a domain name of an invalid format
    # The request failed the XSDs: a defect of the proxy, not of the client's request.
    "83000000004": ResultCode.COMMAND_FAILED,
}

CLASSES = {
    "6": ResultCode.PARAMETER_VALUE_POLICY_ERROR,
    "5": ResultCode.COMMAND_FAILED,
    "7": ResultCode.COMMAND_FAILED,
    "8": ResultCode.COMMAND_FAILED,
}


def result_code(denic_code: str | None) -> ResultCode:
    """The `ResultCode` of a refusal whose first error has `denic_code` (None when it has none)."""
    if denic_code is None:
        return ResultCode.COMMAND_FAILED
    return CODES.get(denic_code) or CLASSES.get(denic_code[:1], ResultCode.COMMAND_FAILED)
