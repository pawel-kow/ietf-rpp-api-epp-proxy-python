import logging

from core.model.domain import domain_application
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domains import Domain, DomainUpdate
from core.model.domain.domain_restore import DomainRestore
from core.ports import derived_update
from core.ports.replace_outcome import ReplaceOutcome
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.partially_applied import PartiallyApplied
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.domain.auth_info import (
    rri_create_auth_info1, rri_delete_auth_info1, valid_auth_info1,
)
from registry_adapter.rri.commands.domain.check import rri_domain_check
from registry_adapter.rri.commands.domain.common import (
    has_auth_info1, state_of, state_of_domain,
)
from registry_adapter.rri.commands.domain.create import rri_domain_create
from registry_adapter.rri.commands.domain.delete import rri_domain_delete
from registry_adapter.rri.commands.domain.info import rri_domain_info
from registry_adapter.rri.commands.domain.restore import rri_domain_restore
from registry_adapter.rri.commands.domain.update import rri_domain_chholder, rri_domain_update
from registry_adapter.rri.commands.shared.rri_command import refused

logger = logging.getLogger(__name__)

AUTH_INFO = "authInfo"


def _bad_auth_info(client_transaction_id) -> ErrorResponse:
    return refused(ResultCode.PARAMETER_VALUE_POLICY_ERROR,
                   "An authInfo for RRI is 8 to 16 characters of A-H J-N P-Z a-k m-n p-z 2-9 + - / *",
                   client_transaction_id)


def _partly_applied(what: str, first: OperationResponse, error: ErrorResponse) -> PartiallyApplied:
    """A request whose first command the registry applied and a later one refused (gap Q7): accepted, with the first
    command's transaction ids, and the refusal logged by its code."""
    logger.warning("RRI %s applied, a later command refused with %s", what, error.registry_code)
    return PartiallyApplied(code=first.code, msg=f"The {what} was applied, but then: {error.msg}",
                            server_transaction_id=first.server_transaction_id,
                            client_transaction_id=first.client_transaction_id, payload=first.payload, refusal=error)


class RriDomainGateway:
    """The domain commands of RRI. RRI updates a domain only by replacing it: UPDATE, or CHHOLDER when the holders
    change, sends the full state, and AuthInfo1 has commands of its own. A partial update is derived from it."""

    def __init__(self, client, lgr: str | None = None):
        self.client = client
        self.lgr = lgr

    def check(self, name, client_transaction_id=None):
        return rri_domain_check(self.client, name, client_transaction_id)

    def info(self, name, client_transaction_id=None):
        return rri_domain_info(self.client, name, client_transaction_id, lgr=self.lgr)

    def restore_info(self, name, client_transaction_id=None):
        return self.info(name, client_transaction_id)

    def create(self, domain: Domain, client_transaction_id=None):
        password = domain.authInfo.pw if domain.authInfo else None
        if password is not None and not valid_auth_info1(password):
            return _bad_auth_info(client_transaction_id)
        created = rri_domain_create(self.client, domain.name, state_of_domain(domain), client_transaction_id)
        if isinstance(created, ErrorResponse) or password is None:
            return self._named(created, domain.name)
        auth = rri_create_auth_info1(self.client, domain.name, password, client_transaction_id, n=2)
        if isinstance(auth, ErrorResponse):
            return _partly_applied("domain create", self._named(created, domain.name), auth)
        return self._named(created, domain.name)

    @staticmethod
    def _named(resp, name):
        """A create answers the domain's name, which the flow reads back."""
        if isinstance(resp, ErrorResponse):
            return resp
        return OperationResponse(code=resp.code, msg=resp.msg, server_transaction_id=resp.server_transaction_id,
                                 client_transaction_id=resp.client_transaction_id, payload=Domain(name=name))

    def update(self, update: DomainUpdate, client_transaction_id=None):
        return derived_update.update(self.info, domain_application.apply, self.replace, update.name, update,
                                     client_transaction_id, self.client.regacc_id)

    def replace(self, wanted: DomainReplacement, current: OperationResponse | None = None, client_transaction_id=None):
        """The native full update: CHHOLDER when the holders change, UPDATE when anything else does, then the
        AuthInfo1 commands. Nothing is sent when nothing changes."""
        if current is None:
            current = self.info(wanted.name)
            if isinstance(current, ErrorResponse):
                return current
        stored: Domain = current.payload
        before = state_of_domain(stored)
        after = state_of(
            wanted.name, registrants=[wanted.registrant] if wanted.registrant else [],
            contacts=[(c.type, c.contact.id) for c in wanted.contacts], ns=wanted.ns, records=wanted.records,
            dns_sec=wanted.dnsSEC,
        )
        keep_auth_info = AUTH_INFO in wanted.unchanged
        password = wanted.authInfo.pw if wanted.authInfo else None
        if not keep_auth_info and password is not None and not valid_auth_info1(password):
            return _bad_auth_info(client_transaction_id)
        steps = []
        holders_change = not before.same_holders(after)
        if holders_change:
            steps.append(("holder change", lambda n: rri_domain_chholder(
                self.client, wanted.name, after, client_transaction_id, n)))
        elif before.key() != after.key():
            steps.append(("update", lambda n: rri_domain_update(self.client, wanted.name, after, client_transaction_id, n)))
        # A holder change removes every AuthInfo; otherwise an AuthInfo1 is replaced or cleared as asked.
        auth_info_exists = has_auth_info1(stored) and not holders_change
        if not keep_auth_info:
            if auth_info_exists and (password is not None or wanted.authInfo is None):
                steps.append(("authInfo removal",
                              lambda n: rri_delete_auth_info1(self.client, wanted.name, client_transaction_id, n)))
            if password is not None:
                steps.append(("authInfo", lambda n: rri_create_auth_info1(
                    self.client, wanted.name, password, client_transaction_id, n)))
        if not steps:
            return ReplaceOutcome(current=current)
        mutation = first = None
        for n, (what, step) in enumerate(steps, start=1):
            resp = step(n)
            if isinstance(resp, ErrorResponse):
                if n == 1:
                    return resp
                mutation = _partly_applied(f"domain {steps[0][0]}", first, resp)
                break
            first = first or resp
            mutation = resp
        return ReplaceOutcome(current=current, update=after, mutation=mutation)

    def delete(self, name, client_transaction_id=None):
        return rri_domain_delete(self.client, name, client_transaction_id)

    def restore(self, restore: DomainRestore, client_transaction_id=None):
        if restore.report is not None:
            return refused(ResultCode.UNIMPLEMENTED_OPTION, "RRI takes no restore report", client_transaction_id)
        return rri_domain_restore(self.client, restore.name, client_transaction_id)

    def transfer(self, transfer, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI has no transfer through this proxy", client_transaction_id)

    def renew(self, renew, client_transaction_id=None):
        return refused(ResultCode.UNIMPLEMENTED_COMMAND, "RRI has no renew", client_transaction_id)
