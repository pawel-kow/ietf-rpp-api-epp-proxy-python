import re

TEL_URI = re.compile(r"^tel:\+(\d{1,3})-([0-9-]+)(?:;ext=(\d+))?$")
EPP_NUMBER = re.compile(r"^\+(\d{1,3})\.(\d+)(?:x(\d+))?$")


def tel_to_epp(tel: str) -> str:
    """'tel:+1-703-555-5555;ext=12' to '+1.7035555555x12'. The first hyphen ends the country code."""
    match = TEL_URI.match(tel)
    if match is None:
        raise ValueError(f"Phone number '{tel}' is not a tel: URI with a country code separator")
    country, number, extension = match.groups()
    return f"+{country}.{number.replace('-', '')}" + (f"x{extension}" if extension else "")


def epp_to_tel(number: str) -> str:
    """'+1.7035555555x12' to 'tel:+1-7035555555;ext=12'."""
    match = EPP_NUMBER.match(number)
    if match is None:
        raise ValueError(f"Phone number '{number}' is not an EPP number")
    country, subscriber, extension = match.groups()
    return f"tel:+{country}-{subscriber}" + (f";ext={extension}" if extension else "")
