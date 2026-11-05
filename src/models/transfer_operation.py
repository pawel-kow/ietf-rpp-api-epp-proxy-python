from enum import Enum


class TransferOperation(Enum):
    REQUEST = "request"
    QUERY = "query"
    CANCEL = "cancel"
    APPROVE = "approve"
    REJECT = "reject"
