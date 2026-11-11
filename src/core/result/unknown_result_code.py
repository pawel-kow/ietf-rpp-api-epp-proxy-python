from dataclasses import dataclass


@dataclass(frozen=True)
class UnknownResultCode:
    """A result code the proxy has no name for. It answers like a ResultCode: `value` is (code, text).

    Core §18.1: RPP-Code is the code with a leading 0, and the HTTP status comes from Table 10 by class.
    """
    value: tuple[str, str]
