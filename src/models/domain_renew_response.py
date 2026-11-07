from dataclasses import dataclass

from .domain_renew_process import DomainRenewProcess
from .response import OperationResponse


@dataclass(kw_only=True)
class DomainRenewResponse(OperationResponse):
    renewal: DomainRenewProcess
