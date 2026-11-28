import logging
from datetime import date, datetime, timedelta, timezone

from xsdata.models.datatype import XmlDateTime

from extensions.rri.core.model.auth_info_process import AuthInfoProcess
from registry_adapter.rri.commands.domain.common import UNKNOWN_SPONSOR, domain_names
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.domain_5_0 import Info, InfoData

logger = logging.getLogger(__name__)


def last_valid_day(stated) -> date:
    """The last day an AuthInfo1 is valid, in the registry's own UTC offset. `domain:authInfo1` is the instant it expires:
    for the `expire` of `20261129` MTEST states `2026-11-30T00:00:00+01:00`, so the last day is the one that precedes the
    instant. xsdata keeps the offset and the fraction; `24:00:00` is the midnight that ends the day, as XML Schema has it.
    Raises ValueError for a value that is no date and time."""
    try:
        moment = stated.to_datetime()
    except ValueError:
        if (stated.hour, stated.minute, stated.second) != (24, 0, 0) or stated.fractional_second:
            raise
        zone = timezone(timedelta(minutes=stated.offset)) if stated.offset is not None else None
        moment = datetime(stated.year, stated.month, stated.day, tzinfo=zone) + timedelta(days=1)
    return (moment - timedelta(microseconds=1)).date()


def auth_info_process_from_rri(data: InfoData) -> AuthInfoProcess:
    """The AuthInfo1 of a domain and its sponsor. An instant the proxy cannot read is an AuthInfo1 with no date, logged by
    the name of its field."""
    sponsor = data.reg_acc.reg_acc_id if data.reg_acc else UNKNOWN_SPONSOR
    stated = data.auth_info1
    if stated is None:
        return AuthInfoProcess(sponsor_id=sponsor, exists=False)
    try:
        # xsdata leaves the text of a value that is no `XmlDateTime` as it is
        if not isinstance(stated, XmlDateTime):
            raise ValueError("not a date and time")
        return AuthInfoProcess(sponsor_id=sponsor, expiry_date=last_valid_day(stated))
    except (ValueError, OverflowError):
        logger.warning("The authInfo1 of a domain is no date and time the proxy can read")
        return AuthInfoProcess(sponsor_id=sponsor)


def rri_auth_info_process_info(client, name: str, client_transaction_id=None):
    """Domain INFO, for the expiry date of the AuthInfo1."""
    return run(client, client_transaction_id, write=False,
               payload_of=lambda transaction: auth_info_process_from_rri(data_of(transaction, InfoData)),
               info_1=Info(**domain_names(name), recursive=False))
