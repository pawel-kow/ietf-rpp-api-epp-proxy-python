from enum import Enum


class AuthInfoAction(Enum):
    """What a full update does with the authorisation information of the object."""
    KEEP = "keep"
    SET = "set"
    CLEAR = "clear"
