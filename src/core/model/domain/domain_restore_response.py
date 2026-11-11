from dataclasses import dataclass

from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class DomainRestoreResponse(OperationResponse):
    restore: DomainRestoreProcess
