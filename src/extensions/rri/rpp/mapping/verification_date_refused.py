from core.capabilities.unsupported_feature import UnsupportedFeature
from core.result.result_code import ResultCode


class VerificationDateRefused(UnsupportedFeature):
    """The date of a verification record is a valid date and time that the server cannot pass on: it is not an instant it can state
    at the offset the registry takes (+01:00). The message never holds the value."""

    code = ResultCode.PARAMETER_VALUE_SYNTAX_ERROR
