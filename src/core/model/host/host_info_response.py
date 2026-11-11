from dataclasses import dataclass

from core.model.host.host import Host
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class HostInfoResponse(OperationResponse):
    host: Host
