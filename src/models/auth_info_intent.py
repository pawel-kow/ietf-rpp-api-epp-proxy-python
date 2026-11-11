from dataclasses import dataclass
from typing import Optional

from .auth_info_action import AuthInfoAction
from .common import AuthInfo


@dataclass(frozen=True, kw_only=True)
class AuthInfoIntent:
    """The authorisation information a full update asks for: kept, set to `auth_info`, or cleared."""
    action: AuthInfoAction = AuthInfoAction.KEEP
    auth_info: Optional[AuthInfo] = None

    @staticmethod
    def keep() -> "AuthInfoIntent":
        return AuthInfoIntent()

    @staticmethod
    def set(auth_info: AuthInfo) -> "AuthInfoIntent":
        return AuthInfoIntent(action=AuthInfoAction.SET, auth_info=auth_info)

    @staticmethod
    def clear() -> "AuthInfoIntent":
        return AuthInfoIntent(action=AuthInfoAction.CLEAR)
