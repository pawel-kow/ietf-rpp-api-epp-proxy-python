from dataclasses import dataclass

from .host import Host
from .response import OperationResponse


@dataclass(kw_only=True)
class HostCreateResponse(OperationResponse):
    host: Host
