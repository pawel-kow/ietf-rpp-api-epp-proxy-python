from dataclasses import dataclass

from .response import OperationResponse


@dataclass(kw_only=True)
class HostUpdateResponse(OperationResponse):
    pass
