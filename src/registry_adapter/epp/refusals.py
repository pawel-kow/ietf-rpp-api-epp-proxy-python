from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.epp.profile import EPP_PROFILE


def _unimplemented(message: str) -> ErrorResponse:
    """A refusal before any EPP command, so there is no transaction to name."""
    return ErrorResponse(
        code=ResultCode.UNIMPLEMENTED_OPTION, msg=message, server_transaction_id=None, client_transaction_id=None,
    )


def not_supported_by_epp(feature: str) -> ErrorResponse:
    """What EPP has no place for, worded as the mappers' `NotSupportedByBackend` for EPP."""
    return _unimplemented(f"{feature} cannot be expressed in {EPP_PROFILE.name}")
