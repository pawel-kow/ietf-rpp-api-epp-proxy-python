from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

class ResultCode(Enum):
    COMMAND_COMPLETED_SUCCESSFULLY = ("1000", "Command completed successfully")
    COMMAND_COMPLETED_ACTION_PENDING = ("1001", "Command completed successfully; action pending")
    COMMAND_COMPLETED_NO_MESSAGES = ("1300", "Command completed successfully; no messages")
    COMMAND_COMPLETED_ACK_TO_DEQUEUE = ("1301", "Command completed successfully; ack to dequeue")
    COMMAND_COMPLETED_ENDING_SESSION = ("1500", "Command completed successfully; ending session")
    UNKNOWN_COMMAND = ("2000", "Unknown command")
    COMMAND_SYNTAX_ERROR = ("2001", "Command syntax error")
    COMMAND_USE_ERROR = ("2002", "Command use error")
    REQUIRED_PARAMETER_MISSING = ("2003", "Required parameter missing")
    PARAMETER_VALUE_RANGE_ERROR = ("2004", "Parameter value range error")
    PARAMETER_VALUE_SYNTAX_ERROR = ("2005", "Parameter value syntax error")
    UNIMPLEMENTED_PROTOCOL_VERSION = ("2100", "Unimplemented protocol version")
    UNIMPLEMENTED_COMMAND = ("2101", "Unimplemented command")
    UNIMPLEMENTED_OPTION = ("2102", "Unimplemented option")
    UNIMPLEMENTED_EXTENSION = ("2103", "Unimplemented extension")
    BILLING_FAILURE = ("2104", "Billing failure")
    OBJECT_NOT_ELIGIBLE_FOR_RENEWAL = ("2105", "Object is not eligible for renewal")
    OBJECT_NOT_ELIGIBLE_FOR_TRANSFER = ("2106", "Object is not eligible for transfer")
    AUTHENTICATION_ERROR = ("2200", "Authentication error")
    AUTHORIZATION_ERROR = ("2201", "Authorization error")
    INVALID_AUTHORIZATION_INFORMATION = ("2202", "Invalid authorization information")
    OBJECT_PENDING_TRANSFER = ("2300", "Object pending transfer")
    OBJECT_NOT_PENDING_TRANSFER = ("2301", "Object not pending transfer")
    OBJECT_EXISTS = ("2302", "Object exists")
    OBJECT_DOES_NOT_EXIST = ("2303", "Object does not exist")
    OBJECT_STATUS_PROHIBITS_OPERATION = ("2304", "Object status prohibits operation")
    OBJECT_ASSOCIATION_PROHIBITS_OPERATION = ("2305", "Object association prohibits operation")
    PARAMETER_VALUE_POLICY_ERROR = ("2306", "Parameter value policy error")
    UNIMPLEMENTED_OBJECT_SERVICE = ("2307", "Unimplemented object service")
    DATA_MANAGEMENT_POLICY_VIOLATION = ("2308", "Data management policy violation")
    COMMAND_FAILED = ("2400", "Command failed")
    COMMAND_FAILED_SERVER_CLOSING_CONNECTION = ("2500", "Command failed; server closing connection")
    AUTHENTICATION_ERROR_SERVER_CLOSING_CONNECTION = ("2501", "Authentication error; server closing connection")
    SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION = ("2502", "Session limit exceeded; server closing connection")

@dataclass(kw_only=True)
class OperationResponse:
    code: ResultCode
    msg: str
    server_transaction_id: Optional[str]
    client_transaction_id: Optional[str]

@dataclass(kw_only=True)
class ErrorResponse(OperationResponse):
    pass

