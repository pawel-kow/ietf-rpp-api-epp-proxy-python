import hashlib
import re

from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.domain.common import domain_names
from registry_adapter.rri.commands.shared.rri_command import refused, run
from registry_adapter.rri.xml.generated.domain_5_0 import CreateAuthInfo1, DeleteAuthInfo1

# An AuthInfo1 is 8 to 16 of these characters (ref §3.6): no I, O, l, o, 0 or 1.
AUTH_INFO1 = re.compile(r"[A-HJ-NP-Za-km-np-z2-9+\-/*]{8,16}")


def valid_auth_info1(password: str) -> bool:
    return AUTH_INFO1.fullmatch(password) is not None


def bad_auth_info(client_transaction_id) -> ErrorResponse:
    """The refusal of an AuthInfo1 the registry cannot take, before any command."""
    return refused(ResultCode.PARAMETER_VALUE_POLICY_ERROR,
                   "An authInfo for RRI is 8 to 16 characters of A-H J-N P-Z a-k m-n p-z 2-9 + - / *",
                   client_transaction_id)


def rri_create_auth_info1(client, name: str, password: str, client_transaction_id=None, n=1, *,
                          expire: str | None = None, codes: dict | None = None):
    """CREATE-AUTHINFO1 with the SHA-256 of the password: RRI never holds the password itself. Its lifetime is the
    registry's default (gap Q4) unless `expire` (`YYYYMMDD`) says otherwise. The hash of a short secret can be guessed,
    so the request is not printed."""
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return run(client, client_transaction_id, write=True, n=n, loggable=False, codes=codes,
               create_auth_info1=CreateAuthInfo1(**domain_names(name), hash=digest, expire=expire))


def rri_delete_auth_info1(client, name: str, client_transaction_id=None, n=1):
    return run(client, client_transaction_id, write=True, n=n, delete_auth_info1=DeleteAuthInfo1(**domain_names(name)))
