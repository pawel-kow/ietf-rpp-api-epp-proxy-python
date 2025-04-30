from models import OperationResponse, ErrorResponse
from helpers import decode_xml

def get_epp_error_response(xml_string: str) -> ErrorResponse:
    root = decode_xml(xml_string)
    return ErrorResponse(
        code=get_epp_code(root),
        msg=get_epp_msg(root),
        server_transaction_id=get_epp_svTRID(root),
        client_transaction_id=get_epp_clTRID(root)
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

def map_epp_code(code: str) -> OperationResponse.ResultCode:
    """
    Maps EPP result codes to OperationResponse.EPPResultCode.
    Args:
        code (str): The EPP result code.
    Returns:
        OperationResponse.ResultCode: The mapped result code.
    """
    epp_code_map = {
        "1000": OperationResponse.ResultCode.COMMAND_COMPLETED_SUCCESSFULLY,
        "1001": OperationResponse.ResultCode.COMMAND_COMPLETED_ACTION_PENDING,
        "1300": OperationResponse.ResultCode.COMMAND_COMPLETED_NO_MESSAGES,
        "1301": OperationResponse.ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE,
        "1500": OperationResponse.ResultCode.COMMAND_COMPLETED_ENDING_SESSION,
        "2000": OperationResponse.ResultCode.UNKNOWN_COMMAND,
        "2001": OperationResponse.ResultCode.COMMAND_SYNTAX_ERROR,
        "2002": OperationResponse.ResultCode.COMMAND_USE_ERROR,
        "2003": OperationResponse.ResultCode.REQUIRED_PARAMETER_MISSING,
        "2004": OperationResponse.ResultCode.PARAMETER_VALUE_RANGE_ERROR,
        "2005": OperationResponse.ResultCode.PARAMETER_VALUE_SYNTAX_ERROR,
        "2100": OperationResponse.ResultCode.UNIMPLEMENTED_PROTOCOL_VERSION,
        "2101": OperationResponse.ResultCode.UNIMPLEMENTED_COMMAND,
        "2102": OperationResponse.ResultCode.UNIMPLEMENTED_OPTION,
        "2103": OperationResponse.ResultCode.UNIMPLEMENTED_EXTENSION,
        "2104": OperationResponse.ResultCode.BILLING_FAILURE,
        "2105": OperationResponse.ResultCode.OBJECT_NOT_ELIGIBLE_FOR_RENEWAL,
        "2106": OperationResponse.ResultCode.OBJECT_NOT_ELIGIBLE_FOR_TRANSFER,
        "2200": OperationResponse.ResultCode.AUTHENTICATION_ERROR,
        "2201": OperationResponse.ResultCode.AUTHORIZATION_ERROR,
        "2202": OperationResponse.ResultCode.INVALID_AUTHORIZATION_INFORMATION,
        "2300": OperationResponse.ResultCode.OBJECT_PENDING_TRANSFER,
        "2301": OperationResponse.ResultCode.OBJECT_NOT_PENDING_TRANSFER,
        "2302": OperationResponse.ResultCode.OBJECT_EXISTS,
        "2303": OperationResponse.ResultCode.OBJECT_DOES_NOT_EXIST,
        "2304": OperationResponse.ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION,
        "2305": OperationResponse.ResultCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION,
        "2306": OperationResponse.ResultCode.PARAMETER_VALUE_POLICY_ERROR,
        "2307": OperationResponse.ResultCode.UNIMPLEMENTED_OBJECT_SERVICE,
        "2308": OperationResponse.ResultCode.DATA_MANAGEMENT_POLICY_VIOLATION,
        "2400": OperationResponse.ResultCode.COMMAND_FAILED,
        "2500": OperationResponse.ResultCode.COMMAND_FAILED_SERVER_CLOSING_CONNECTION,
        "2501": OperationResponse.ResultCode.AUTHENTICATION_ERROR_SERVER_CLOSING_CONNECTION,
        "2502": OperationResponse.ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION,
    }
    
    try:
        return epp_code_map[code]
    except ValueError:
        raise ValueError(f"Unknown EPP result code: {code}")