from models import ResultCode


class UnsupportedRppFeature(Exception):
    """Valid RPP input that cannot reach the backend. A subclass says why, and `code` is its result code."""

    code = ResultCode.UNIMPLEMENTED_OPTION
