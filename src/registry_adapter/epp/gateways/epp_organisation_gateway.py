from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode


class EppOrganisationGateway:
    """EPP has no organisation objects: every organisation command answers `UNIMPLEMENTED_COMMAND`, the port's convention for
    a command the backend lacks. It is never what answers a request, as the profile has no `organisation` object."""

    def info(self, id, client_transaction_id=None):
        return ErrorResponse(code=ResultCode.UNIMPLEMENTED_COMMAND, msg="EPP has no organisation objects",
                             server_transaction_id=None, client_transaction_id=client_transaction_id)
