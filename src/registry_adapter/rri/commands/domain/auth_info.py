import hashlib
import re

from registry_adapter.rri.commands.domain.common import domain_names
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import CreateAuthInfo1, DeleteAuthInfo1

# An AuthInfo1 is 8 to 16 of these characters (ref §3.6): no I, O, l, o, 0 or 1.
AUTH_INFO1 = re.compile(r"[A-HJ-NP-Za-km-np-z2-9+\-/*]{8,16}")


def valid_auth_info1(password: str) -> bool:
    return AUTH_INFO1.fullmatch(password) is not None


def rri_create_auth_info1(client, name: str, password: str, client_transaction_id=None, n=1):
    """CREATE-AUTHINFO1 with the SHA-256 of the password: RRI never holds the password itself. Its lifetime is the
    registry's default (gap Q4)."""
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return run(client, client_transaction_id, write=True, n=n,
               create_auth_info1=CreateAuthInfo1(**domain_names(name), hash=digest))


def rri_delete_auth_info1(client, name: str, client_transaction_id=None, n=1):
    return run(client, client_transaction_id, write=True, n=n, delete_auth_info1=DeleteAuthInfo1(**domain_names(name)))
