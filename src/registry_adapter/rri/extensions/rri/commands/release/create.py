from registry_adapter.rri.commands.domain.common import domain_names
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.shared.rri_command import run
from registry_adapter.rri.xml.generated.domain_5_0 import Transit


# The registry refuses a TRANSIT of a domain in the status `failed` with 53000080012 (MTEST, 2026-11-28): a class 5 code,
# which would be a 500 without this mapping.
CODES = {"53000080012": ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION}


def rri_release_create(client, name: str, keep_nameservers: bool, client_transaction_id=None):
    """TRANSIT. The registry does not document its default for a TRANSIT without `disconnect`, so it is always sent:
    `false` keeps the name servers, `true` has the registry replace them."""
    return run(client, client_transaction_id, write=True, codes=CODES,
               transit=Transit(**domain_names(name), disconnect=not keep_nameservers))
