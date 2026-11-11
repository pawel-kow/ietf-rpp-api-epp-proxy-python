from dataclasses import dataclass

from core.model.domain.domain_renew_process import DomainRenewProcess
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class DomainRenewResponse(OperationResponse):
    renewal: DomainRenewProcess
