import logging

from xsdata.models.datatype import XmlDateTime

from core.model.shared.common import AuthInfo
from extensions.rri.core.model.holder_verification import HolderVerification
from extensions.rri.core.model.verification_process import VerificationProcess
from registry_adapter.rri.commands.domain.common import UNKNOWN_SPONSOR, domain_names
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.extensions.rri.contact_members import records_of
from registry_adapter.rri.xml.generated.contact_5_0 import RoleType
from registry_adapter.rri.xml.generated.domain_5_0 import Info, InfoData

logger = logging.getLogger(__name__)


def _deadline(value, name: str) -> str | None:
    """A deadline in UTC. A value the proxy cannot read is left out, logged by the name of its field."""
    if value is None:
        return None
    try:
        if not isinstance(value, XmlDateTime):
            raise ValueError("not a date and time")
        return utc_time(value)
    except (ValueError, OverflowError):
        logger.warning("%s is no date and time the proxy can read", name)
        return None


def verification_process_from_rri(data: InfoData) -> VerificationProcess:
    """The deadlines and the holders of a recursive domain INFO, in the order the registry lists the holders. The registry
    leaves out the handles and all but the claims and the result for a domain of another RegAcc."""
    holders = [HolderVerification(handle=contact.handle.value if contact.handle is not None else None,
                                  verifications=records_of(contact.verification_information))
               for contact in data.contact if contact.role == RoleType.HOLDER]
    return VerificationProcess(
        sponsor_id=data.reg_acc.reg_acc_id if data.reg_acc else UNKNOWN_SPONSOR,
        hold_deadline=_deadline(data.verification_deadline_before_dedelegation, "verificationDeadlineBeforeDedelegation"),
        deletion_deadline=_deadline(data.verification_deadline_before_deletion, "verificationDeadlineBeforeDeletion"),
        holders=holders)


def rri_verification_process_info(client, name: str, authorization: AuthInfo | None, client_transaction_id=None):
    """Domain INFO with `recursive="true"`, with the Object Authorisation of the request as `domain:authInfo`. The request and
    the reply carry personal data, verification information and the authorisation, so neither is printed."""
    return run(client, client_transaction_id, write=False, loggable=False,
               payload_of=lambda transaction: verification_process_from_rri(data_of(transaction, InfoData)),
               info_1=Info(**domain_names(name), recursive=True, auth_info=authorization.pw if authorization else None))
