from dataclasses import dataclass

from .domain_restore_process import DomainRestoreProcess
from .response import OperationResponse


@dataclass(kw_only=True)
class DomainRestoreResponse(OperationResponse):
    restore: DomainRestoreProcess
