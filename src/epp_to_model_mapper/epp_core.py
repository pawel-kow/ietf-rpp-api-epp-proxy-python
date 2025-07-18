from models import ErrorResponse, ResultCode
from helpers import decode_xml

def get_epp_error_response(xml_string: str, client_transaction_id: str) -> ErrorResponse:
    root = decode_xml(xml_string)
    return ErrorResponse(
        code=get_epp_code(root),
        msg=get_epp_msg(root),
        server_transaction_id=get_epp_svTRID(root),
        client_transaction_id=get_epp_clTRID(root) if client_transaction_id is not None else None,
    )

def get_epp_code(root):
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}
    # Extract the result code and message
    result = root.find("./epp:response/epp:result", namespaces=namespace)
    if result is not None:
        return map_epp_code(result.attrib.get("code"))
    else:
        raise ValueError("EPP result code not found in the response")

def get_epp_msg(root):
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}
    # Extract the result code and message
    result = root.find("./epp:response/epp:result/epp:msg", namespaces=namespace)
    if result is not None:
        return result.text
    else:
        raise ValueError("EPP result message not found in the response")

def get_epp_svTRID(root):
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}
    # Extract the transaction ID
    if root.find(".//epp:svTRID", namespaces=namespace) is None:
        raise ValueError("EPP svTRID not found in the response")
    return root.find(".//epp:svTRID", namespaces=namespace).text

def get_epp_clTRID(root):
    namespace = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}
    # Extract the transaction ID
    if root.find(".//epp:clTRID", namespaces=namespace) is not None:
        return root.find(".//epp:clTRID", namespaces=namespace).text
    else:
        return None

def map_epp_code(code: str) -> ResultCode:
    """
    Maps EPP result codes to OperationResponse.EPPResultCode.
    Args:
        code (str): The EPP result code.
    Returns:
        ResultCode: The mapped result code.
    """
    epp_code_map = {
        "1000": ResultCode.COMMAND_COMPLETED_SUCCESSFULLY,
        "1001": ResultCode.COMMAND_COMPLETED_ACTION_PENDING,
        "1300": ResultCode.COMMAND_COMPLETED_NO_MESSAGES,
        "1301": ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE,
        "1500": ResultCode.COMMAND_COMPLETED_ENDING_SESSION,
        "2000": ResultCode.UNKNOWN_COMMAND,
        "2001": ResultCode.COMMAND_SYNTAX_ERROR,
        "2002": ResultCode.COMMAND_USE_ERROR,
        "2003": ResultCode.REQUIRED_PARAMETER_MISSING,
        "2004": ResultCode.PARAMETER_VALUE_RANGE_ERROR,
        "2005": ResultCode.PARAMETER_VALUE_SYNTAX_ERROR,
        "2100": ResultCode.UNIMPLEMENTED_PROTOCOL_VERSION,
        "2101": ResultCode.UNIMPLEMENTED_COMMAND,
        "2102": ResultCode.UNIMPLEMENTED_OPTION,
        "2103": ResultCode.UNIMPLEMENTED_EXTENSION,
        "2104": ResultCode.BILLING_FAILURE,
        "2105": ResultCode.OBJECT_NOT_ELIGIBLE_FOR_RENEWAL,
        "2106": ResultCode.OBJECT_NOT_ELIGIBLE_FOR_TRANSFER,
        "2200": ResultCode.AUTHENTICATION_ERROR,
        "2201": ResultCode.AUTHORIZATION_ERROR,
        "2202": ResultCode.INVALID_AUTHORIZATION_INFORMATION,
        "2300": ResultCode.OBJECT_PENDING_TRANSFER,
        "2301": ResultCode.OBJECT_NOT_PENDING_TRANSFER,
        "2302": ResultCode.OBJECT_EXISTS,
        "2303": ResultCode.OBJECT_DOES_NOT_EXIST,
        "2304": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,
        "2305": ResultCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION,
        "2306": ResultCode.PARAMETER_VALUE_POLICY_ERROR,
        "2307": ResultCode.UNIMPLEMENTED_OBJECT_SERVICE,
        "2308": ResultCode.DATA_MANAGEMENT_POLICY_VIOLATION,
        "2400": ResultCode.COMMAND_FAILED,
        "2500": ResultCode.COMMAND_FAILED_SERVER_CLOSING_CONNECTION,
        "2501": ResultCode.AUTHENTICATION_ERROR_SERVER_CLOSING_CONNECTION,
        "2502": ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,
    }
    
    try:
        return epp_code_map[code]
    except ValueError:
        raise ValueError(f"Unknown EPP result code: {code}")