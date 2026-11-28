from typing import Protocol

from core.model.shared.common import AuthInfo
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from extensions.rri.core.model.verification_process import VerificationProcess


class VerificationProcessGateway(Protocol):
    """The verification of the holders of a domain name that the registry requires, which a client only reads."""

    def info(self, name: str, authorization: AuthInfo | None = None,
             client_transaction_id=None) -> OperationResponse[VerificationProcess] | ErrorResponse:
        """The process of the domain `name`. `authorization` is the Object Authorisation a client other than the sponsor
        sends. The payload has no deadline for a domain without a process."""
