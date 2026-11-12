"""The RRI adapter over replies recorded from MTEST (personal data replaced): the commands it sends, how it composes a
full update, and how it reads replies and refusals."""
import hashlib
from pathlib import Path

import pytest

from core.model.contact.address import Address
from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contacts import Contact, ContactType
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domains import ContactReference, ContactReferenceNew, Domain, DomainUpdate, \
    DomainUpdateChange
from core.model.contact.contacts import ContactMinimal
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.zone_record import ZoneRecord
from core.model.shared.common import AuthInfo
from core.result.error_response import ErrorResponse
from core.result.partially_applied import PartiallyApplied
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.shared.rri_command import ctid
from registry_adapter.rri.gateways.rri_backend import RriBackend
from registry_adapter.rri.result_codes import result_code
from tests.helper.fake_rri_client import FakeRriClient, error, reply

REPLIES = Path(__file__).parent / "rri_replies"

DOMAIN_INFO = reply(data=(REPLIES / "domain_info.xml").read_text())

CONTACT_INFO = reply(data=(REPLIES / "contact_info.xml").read_text())

NAME = "rpp-exp-caa50f65.de"


def backend(*replies):
    client = FakeRriClient(replies=list(replies))
    return RriBackend(client), client


def test_the_sponsor_is_the_regacc_of_the_login():
    assert backend()[0].sponsor_id == "DENIC-1000022"


def test_domain_info_reads_the_domain():
    gateway, client = backend(DOMAIN_INFO)

    domain = gateway.domains.info(NAME, client_transaction_id="cl-1").payload

    assert '<domain:info recursive="false">' in client.sent[0] and "<ctid>" not in client.sent[0]
    assert domain.name == NAME
    assert domain.status == ["pendingCreate"]
    assert domain.clID == "DENIC-1000022"
    assert domain.crDate == "2026-11-12T00:20:33.000000Z"
    assert domain.contacts == [ContactReference(id="DENIC-1000022-HOLDER", types=["registrant"]),
                               ContactReference(id="DENIC-1000022-GENREQ", types=["generalRequest"]),
                               ContactReference(id="DENIC-1000022-GENREQ", types=["abuse"])]
    assert domain.records == [
        ZoneRecord(owner=NAME, type="a", address="192.0.2.10"),
        ZoneRecord(owner=f"www.{NAME}", type="aaaa", address="2001:db8::1"),
        ZoneRecord(owner=NAME, type="mx", preference=10, exchange=NAME),
    ]
    assert domain.authInfo is None


def test_a_refusal_carries_the_denic_code():
    gateway, _ = backend(error("63300062009", "Domain doesn't exist", NAME))

    resp = gateway.domains.info(NAME, client_transaction_id="cl-1")

    assert isinstance(resp, ErrorResponse)
    assert resp.code == ResultCode.OBJECT_DOES_NOT_EXIST
    assert resp.registry_code == "63300062009"
    assert resp.client_transaction_id == "cl-1"


def test_a_deleted_domain_reads_with_what_rri_shows():
    deleted = reply(data=('<domain:infoData xmlns:domain="http://registry.denic.de/domain/5.0">'
                          f'<domain:handle>{NAME}</domain:handle><domain:ace>{NAME}</domain:ace>'
                          '<domain:status>redemptionPeriod</domain:status>'
                          '<domain:changed>2026-11-12T01:20:34+01:00</domain:changed></domain:infoData>'))
    gateway, _ = backend(deleted, deleted)

    domain = gateway.domains.info(NAME).payload
    assert domain.status == ["pendingDelete"] and domain.clID == "unknown"
    assert gateway.domains.restore_info(NAME).payload.rgpStatus == ["redemptionPeriod"]


@pytest.mark.parametrize("code, expected", [
    ("63200020603", ResultCode.AUTHORIZATION_ERROR),
    ("63310062004", ResultCode.OBJECT_EXISTS),
    ("53000000012", ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION),
    ("63299999999", ResultCode.PARAMETER_VALUE_POLICY_ERROR),
    ("53999999999", ResultCode.COMMAND_FAILED),
    ("83000000004", ResultCode.COMMAND_FAILED),
    (None, ResultCode.COMMAND_FAILED),
])
def test_result_codes(code, expected):
    assert result_code(code) == expected


@pytest.mark.parametrize("client_id, n, expected", [
    ("cl-1", 1, "cl-1"), ("cl-1", 2, "cl-1-2"), ("a b", 1, "a b"),
])
def test_the_ctid_is_the_clients_id(client_id, n, expected):
    assert ctid(client_id, n) == expected


@pytest.mark.parametrize("client_id", [None, "ab", "x" * 61, " lead", "two  spaces", "tab\tx"])
def test_a_client_id_that_is_no_ctid_gives_a_new_one(client_id):
    assert len(ctid(client_id)) == 36


def _domain(**extra):
    return Domain(name=NAME, contacts=[ContactReference(id="DENIC-1000022-HOLDER", types=["registrant"]),
                                       ContactReference(id="DENIC-1000022-GENREQ", types=["generalRequest"])],
                  records=[ZoneRecord(owner=NAME, type="a", address="192.0.2.10")], **extra)


def test_create_with_auth_info_sends_its_hash():
    gateway, client = backend(reply(ctid="cl-1"), reply(ctid="cl-1-2"))

    resp = gateway.domains.create(_domain(authInfo=AuthInfo(pw="Abc2345678")), client_transaction_id="cl-1")

    assert resp.payload.name == NAME
    assert "<domain:create>" in client.sent[0] and "<ctid>cl-1</ctid>" in client.sent[0]
    assert '<domain:contact role="holder">DENIC-1000022-HOLDER</domain:contact>' in client.sent[0]
    assert 'xsi:type="dnsentry:A"' in client.sent[0]
    assert hashlib.sha256(b"Abc2345678").hexdigest() in client.sent[1] and "<ctid>cl-1-2</ctid>" in client.sent[1]
    assert "Abc2345678" not in "".join(client.sent)


def test_create_with_an_auth_info_rri_cannot_take_sends_nothing():
    gateway, client = backend()

    resp = gateway.domains.create(_domain(authInfo=AuthInfo(pw="Password1!@")))

    assert resp.code == ResultCode.PARAMETER_VALUE_POLICY_ERROR
    assert client.sent == []


def test_create_whose_auth_info_fails_is_partly_applied():
    gateway, _ = backend(reply(stid="sv-create"), error("63391068704", "AuthInfo1 already exists"))

    resp = gateway.domains.create(_domain(authInfo=AuthInfo(pw="Abc2345678")), client_transaction_id="cl-1")

    assert isinstance(resp, PartiallyApplied)
    assert resp.server_transaction_id == "sv-create" and resp.client_transaction_id == "cl-1"
    assert resp.refusal.code == ResultCode.OBJECT_EXISTS


def test_a_full_update_whose_auth_info_fails_is_partly_applied():
    gateway, _ = backend(DOMAIN_INFO, reply(stid="sv-update"), error("63391068704", "AuthInfo1 already exists"))

    outcome = gateway.domains.replace(_wanted(unchanged=frozenset(), authInfo=AuthInfo(pw="Xyz2345678")))

    assert isinstance(outcome.mutation, PartiallyApplied)
    assert outcome.mutation.server_transaction_id == "sv-update"


def _wanted(**extra):
    base = dict(name=NAME, registrant="DENIC-1000022-HOLDER",
                contacts=[ContactReferenceNew(type="generalRequest", contact=ContactMinimal(id="DENIC-1000022-GENREQ")),
                          ContactReferenceNew(type="abuse", contact=ContactMinimal(id="DENIC-1000022-GENREQ"))],
                records=[ZoneRecord(owner=NAME, type="a", address="192.0.2.10"),
                         ZoneRecord(owner=f"www.{NAME}", type="aaaa", address="2001:db8::1"),
                         ZoneRecord(owner=NAME, type="mx", preference=10, exchange=NAME)],
                unchanged=frozenset({"authInfo"}))
    return DomainReplacement(**{**base, **extra})


def test_replace_that_changes_nothing_sends_nothing():
    gateway, client = backend(DOMAIN_INFO)

    outcome = gateway.domains.replace(_wanted())

    assert outcome.unchanged
    assert len(client.sent) == 1


def test_replace_of_the_records_is_one_update_with_the_full_state():
    gateway, client = backend(DOMAIN_INFO, reply())

    outcome = gateway.domains.replace(_wanted(records=[ZoneRecord(owner=NAME, type="a", address="192.0.2.11")]),
                                      client_transaction_id="cl-1")

    assert not outcome.unchanged
    assert "<domain:update>" in client.sent[1]
    assert "192.0.2.11" in client.sent[1] and "2001:db8::1" not in client.sent[1]
    assert 'role="generalrequest"' in client.sent[1] and 'role="holder"' in client.sent[1]


def test_replace_of_the_holder_is_a_holder_change_which_needs_no_auth_info_removal():
    gateway, client = backend(DOMAIN_INFO, reply(), reply())

    gateway.domains.replace(_wanted(registrant="DENIC-1000022-OTHER", unchanged=frozenset(),
                                    authInfo=AuthInfo(pw="Xyz2345678")))

    assert "<domain:chholder>" in client.sent[1]
    assert "createAuthInfo1" in client.sent[2]
    assert len(client.sent) == 3


def test_a_new_auth_info_replaces_the_stored_one():
    gateway, client = backend(DOMAIN_INFO, reply(), reply())

    gateway.domains.replace(_wanted(unchanged=frozenset(), authInfo=AuthInfo(pw="Xyz2345678")))

    assert "deleteAuthInfo1" in client.sent[1] and "createAuthInfo1" in client.sent[2]


def test_a_cleared_auth_info_is_deleted():
    gateway, client = backend(DOMAIN_INFO, reply())

    gateway.domains.replace(_wanted(unchanged=frozenset(), authInfo=None))

    assert "deleteAuthInfo1" in client.sent[1] and len(client.sent) == 2


def test_partial_update_is_derived_from_the_full_one():
    gateway, client = backend(DOMAIN_INFO, reply(), reply())

    resp = gateway.domains.update(DomainUpdate(name=NAME, change=DomainUpdateChange(
        authInfo=AuthInfo(pw="Xyz2345678"))), client_transaction_id="cl-1")

    assert resp.code == ResultCode.COMMAND_COMPLETED_SUCCESSFULLY
    assert "<domain:info" in client.sent[0]
    assert "deleteAuthInfo1" in client.sent[1] and "createAuthInfo1" in client.sent[2]


def test_partial_update_that_changes_nothing_is_refused_to_another_regacc():
    client = FakeRriClient(username="DENIC-99-RRI", replies=[DOMAIN_INFO])
    gateway = RriBackend(client)

    resp = gateway.domains.update(DomainUpdate(name=NAME), client_transaction_id="cl-1")

    assert resp.code == ResultCode.AUTHORIZATION_ERROR


def test_hosts_transfer_and_renew_are_lacking_commands():
    gateway, client = backend()

    assert gateway.hosts.info("ns1.example.de").code == ResultCode.UNIMPLEMENTED_COMMAND
    assert gateway.domains.transfer(None).code == ResultCode.UNIMPLEMENTED_COMMAND
    assert gateway.domains.renew(None).code == ResultCode.UNIMPLEMENTED_COMMAND
    assert gateway.contacts.delete("x").code == ResultCode.UNIMPLEMENTED_COMMAND
    assert client.sent == []


def test_contact_info_reads_the_contact_and_carries_its_verification_over():
    gateway, _ = backend(CONTACT_INFO)

    contact = gateway.contacts.info("DENIC-1000022-HOLDER").payload

    assert contact.name == "Erika Mustermann"
    assert contact.address == Address(street=["Musterweg 12"], city="Frankfurt am Main", postalCode="60596",
                                      country="DE")
    assert contact.phone == ["+49.6912345678"] and contact.email == ["erika@example.com"]
    assert contact.status == ["ok"] and contact.clID == "DENIC-1000022"
    assert len(contact.carried_over) == 1


def test_contact_update_sends_the_verification_again():
    gateway, client = backend(CONTACT_INFO, reply())

    outcome = gateway.contacts.replace(ContactReplacement(
        id="DENIC-1000022-HOLDER", name="Erika Mustermann", email=["new@example.com"], phone=["+49.6912345678"],
        address=Address(street=["Musterweg 12"], city="Frankfurt am Main", postalCode="60596", country="DE"),
        unchanged=frozenset({"authInfo"})))

    assert not outcome.unchanged
    assert "<contact:update>" in client.sent[1] and "new@example.com" in client.sent[1]
    assert "verificationInformation" in client.sent[1] and "ABC123" in client.sent[1]


def test_contact_update_that_changes_nothing_sends_nothing():
    gateway, client = backend(CONTACT_INFO)

    outcome = gateway.contacts.replace(ContactReplacement(
        id="DENIC-1000022-HOLDER", name="Erika Mustermann", email=["erika@example.com"], phone=["+49.6912345678"],
        address=Address(street=["Musterweg 12"], city="Frankfurt am Main", postalCode="60596", country="DE"),
        unchanged=frozenset({"authInfo"})))

    assert outcome.unchanged and len(client.sent) == 1


def test_contact_not_found_is_404():
    gateway, _ = backend(error("53000060009", "At least one contact does not exist"))

    assert gateway.contacts.info("DENIC-1000022-X").code == ResultCode.OBJECT_DOES_NOT_EXIST


def test_an_org_contact_is_named_by_its_organisation():
    gateway, client = backend(reply())

    gateway.contacts.create(Contact(id="DENIC-1000022-ORG", type=ContactType.ORG, organisationName="Example eG",
                                    email=["a@example.com"], phone=["+49.69123456"],
                                    address=Address(street=["A 1"], city="B", postalCode="60596", country="DE")))

    assert "<contact:type>ORG</contact:type>" in client.sent[0]
    assert "<contact:name>Example eG</contact:name>" in client.sent[0]
    assert "<contact:organisation>" not in client.sent[0]


def test_a_contact_auth_info_is_refused():
    gateway, client = backend()

    resp = gateway.contacts.create(Contact(id="DENIC-1000022-X", authInfo=AuthInfo(pw="x")))

    assert resp.code == ResultCode.UNIMPLEMENTED_OPTION and client.sent == []


QUEUE = reply(data=('<msg:message xmlns:msg="http://registry.denic.de/msg/5.0" msgid="e493e544-da37-11f1" '
                    'msgcnt="2" msgtime="2026-11-07T00:15:01+01:00"><msg:contactDelete><msg:handles>'
                    '<msg:handle>DENIC-1000022-OLD</msg:handle></msg:handles></msg:contactDelete></msg:message>'))


def test_queue_read_is_a_notice_that_names_type_and_objects():
    gateway, client = backend(QUEUE)

    queue = gateway.messages.poll().payload

    assert "<msg:queue-read" in client.sent[0]
    assert queue.queue_size == 2
    assert queue.message.id == "e493e544-da37-11f1"
    assert queue.message.text == "RRI contactDelete: DENIC-1000022-OLD"
    assert queue.message.creationDate == "2026-11-06T23:15:01.000000Z"


def test_an_empty_queue_has_no_message():
    gateway, _ = backend(reply())

    queue = gateway.messages.poll().payload

    assert queue.message is None and queue.queue_size == 0


def test_queue_delete_names_the_message():
    gateway, client = backend(reply())

    gateway.messages.ack("e493e544-da37-11f1")

    assert 'msgid="e493e544-da37-11f1"' in client.sent[0]


def _stored_contact_replacement(**extra):
    base = dict(id="DENIC-1000022-HOLDER", name="Erika Mustermann", email=["erika@example.com"],
                phone=["+49.6912345678"], unchanged=frozenset({"authInfo"}),
                address=Address(street=["Musterweg 12"], city="Frankfurt am Main", postalCode="60596", country="DE"))
    return ContactReplacement(**{**base, **extra})


ORG_CONTACT_INFO = reply(data=(REPLIES / "contact_info.xml").read_text()
                         .replace("<contact:type>PERSON</contact:type>", "<contact:type>ORG</contact:type>"))


@pytest.mark.parametrize("change", [dict(name="Erika Musterfrau"), dict(phone=None), dict(address=None)])
def test_a_contact_update_rri_refuses_is_sent_and_its_refusal_answered(change):
    gateway, client = backend(CONTACT_INFO, error("63220080801", "Name is immutable"))

    resp = gateway.contacts.replace(_stored_contact_replacement(**change))

    assert len(client.sent) == 2 and "<contact:update>" in client.sent[1]
    assert resp.code == ResultCode.PARAMETER_VALUE_POLICY_ERROR and resp.registry_code == "63220080801"


def test_a_person_keeps_its_type_when_an_organisation_is_added():
    gateway, client = backend(CONTACT_INFO, reply(stid="sv-update"))

    gateway.contacts.replace(_stored_contact_replacement(organisationName="Example eG"))

    assert "<contact:type>PERSON</contact:type>" in client.sent[1]
    assert "<contact:name>Erika Mustermann</contact:name>" in client.sent[1]
    assert "<contact:organisation>Example eG</contact:organisation>" in client.sent[1]


def test_the_name_of_a_person_on_an_org_is_refused():
    gateway, client = backend(ORG_CONTACT_INFO)

    resp = gateway.contacts.replace(_stored_contact_replacement(organisationName="Example eG"))

    assert resp.code == ResultCode.UNIMPLEMENTED_OPTION and "name of a person" in resp.msg
    assert len(client.sent) == 1


def test_a_full_update_without_dns_data_sends_nothing():
    gateway, client = backend(DOMAIN_INFO)

    resp = gateway.domains.replace(_wanted(records=[]))

    assert resp.code == ResultCode.UNIMPLEMENTED_OPTION and len(client.sent) == 1


def test_a_create_without_dns_data_sends_nothing():
    gateway, client = backend()

    resp = gateway.domains.create(Domain(name="example.de"))

    assert resp.code == ResultCode.UNIMPLEMENTED_OPTION and client.sent == []


def test_an_lgr_on_an_ascii_name_is_not_sent():
    gateway, client = backend(reply())

    gateway.domains.create(Domain(name="example.de", idn=DomainIdn(lgr="latn-1.0", uname=None),
                                  records=[ZoneRecord(owner="example.de", type="a", address="192.0.2.10")]))

    assert "latn" not in client.sent[0]


def test_a_uname_that_is_not_the_name_is_refused():
    gateway, client = backend()

    resp = gateway.domains.create(Domain(name="xn--bcher-kva.de", idn=DomainIdn(lgr="latn-1.0", uname="bücherei.de")))

    assert resp.code == ResultCode.PARAMETER_VALUE_POLICY_ERROR and "uName" in resp.msg
    assert client.sent == []


def test_an_idn_is_sent_with_its_u_label_and_a_label():
    gateway, client = backend(reply())

    gateway.domains.check("xn--bcher-kva.de")

    assert "<domain:handle>bücher.de</domain:handle><domain:ace>xn--bcher-kva.de</domain:ace>" in client.sent[0]
