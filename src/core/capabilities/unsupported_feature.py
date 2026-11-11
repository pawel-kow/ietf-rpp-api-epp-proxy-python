from core.result.result_code import ResultCode


class UnsupportedFeature(Exception):
    """Valid input that cannot reach the backend. A subclass says why, and `code` is its result code."""

    code = ResultCode.UNIMPLEMENTED_OPTION
