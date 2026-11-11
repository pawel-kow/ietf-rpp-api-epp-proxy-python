from dataclasses import dataclass

from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class HostDeleteResponse(OperationResponse):
    pass
