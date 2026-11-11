import re

from core.capabilities.backend_requirement import BackendRequirement

TEL_URI = re.compile(r"tel:(\+(\d{1,3})\.(\d{1,14}))(?:;ext=(\d+))?")

DOTTED_NUMBER = re.compile(r"(\+\d{1,3}\.\d+)(?:x(\d+))?")

MAX_DIGITS = 15


def rpp_to_model(tel: str) -> str:
    """'tel:+1.7035555555;ext=12' to '+1.7035555555x12' (rpp-telephone-uri of the JSContact profile)."""
    match = TEL_URI.fullmatch(tel)
    if match is None or len(match[2]) + len(match[3]) > MAX_DIGITS:
        raise ValueError(f"Phone number '{tel}' is not an rpp-telephone-uri")
    return match[1] + (f"x{match[4]}" if match[4] else "")


def model_to_rpp(number: str) -> str:
    """'+1.7035555555x12' to 'tel:+1.7035555555;ext=12'."""
    match = DOTTED_NUMBER.fullmatch(number)
    if match is None:
        raise BackendRequirement(f"Phone number '{number}' is not an {{backend}} number")
    return f"tel:{match[1]}" + (f";ext={match[2]}" if match[2] else "")
