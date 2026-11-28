from datetime import datetime, timedelta

from extensions.rri.core.model.auth_info_process import AuthInfoProcess
from registry_adapter.rri.commands.domain.common import UNKNOWN_SPONSOR, domain_names
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.domain_5_0 import Info, InfoData


def auth_info_process_from_rri(data: InfoData) -> AuthInfoProcess:
    """The last day the AuthInfo1 is valid, in the registry's own UTC offset, and the sponsor. `domain:authInfo1` is the
    instant it expires: for the `expire` of `20261129` MTEST states `2026-11-30T00:00:00+01:00`, so the last day is the
    one that precedes the instant."""
    stated = data.auth_info1
    last = (datetime(stated.year, stated.month, stated.day, stated.hour, stated.minute, stated.second)
            - timedelta(microseconds=1)).date() if stated else None
    return AuthInfoProcess(sponsor_id=data.reg_acc.reg_acc_id if data.reg_acc else UNKNOWN_SPONSOR, expiry_date=last)


def rri_auth_info_process_info(client, name: str, client_transaction_id=None):
    """Domain INFO, for the expiry date of the AuthInfo1."""
    return run(client, client_transaction_id, write=False,
               payload_of=lambda transaction: auth_info_process_from_rri(data_of(transaction, InfoData)),
               info_1=Info(**domain_names(name), recursive=False))
