"""The registry of the mappers of the members extensions add to a base object (rpp/mapping/shared/member_mappers.py), with the
domain's one and the rri extension's mapper."""
import pytest

from core.model.contact.contacts import Contact
from core.model.domain.domains import ContactReference, Domain
from extensions.rri.core.model.contact_verifications import ContactVerifications
from extensions.rri.core.model.verification_information import VerificationInformation
from rpp.mapping.contact.contact_members import CONTACT_MEMBERS
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from rpp.mapping.domain.domain_members import DOMAIN_MEMBERS
from rpp.mapping.shared.member_mappers import MemberMappers
from tests.helper.profiles import RRI_REGISTRY  # registers the rri extension, and so its mapper

REQUEST = {"@type": "requestContact", "id": "DENIC-1000022-GR"}


def test_the_mapper_of_an_extension_is_used_for_the_extensions_of_the_request_only():
    assert DOMAIN_MEMBERS.members("domainName.create", (EXTENSION_ID,)) == ("generalRequest", "abuse")
    assert DOMAIN_MEMBERS.members("domainName.create", ()) == ()


def test_the_members_a_definition_has_are_the_extension_schemas():
    # the extension adds the request contacts to a domain and to the request of its transfer
    assert DOMAIN_MEMBERS.members("domainTransferProcess.create", (EXTENSION_ID,)) == ("generalRequest", "abuse")
    assert DOMAIN_MEMBERS.members("contact.create", (EXTENSION_ID,)) == ()


def test_split_takes_the_members_out_and_gives_the_roles():
    rest, roles = DOMAIN_MEMBERS.split({"name": "a.de", "abuse": REQUEST}, "domainName.create", (EXTENSION_ID,))

    assert rest == {"name": "a.de"} and roles == [("abuse", "DENIC-1000022-GR")]


def test_split_without_the_extension_leaves_the_members_undeclared():
    rest, roles = DOMAIN_MEMBERS.split({"name": "a.de", "abuse": REQUEST}, "domainName.create", ())

    assert rest == {"name": "a.de", "abuse": REQUEST} and roles == []


def test_a_member_is_shown_as_the_read_definition_has_it():
    domain = Domain(name="a.de", contacts=[ContactReference(id="X", types=["abuse"]), ContactReference(id="Y", types=["admin"])])

    assert DOMAIN_MEMBERS.to_rpp(domain, "domainName.read", (EXTENSION_ID,)) == {
        "abuse": {"@type": "requestContact", "id": "X"}}


def test_registering_a_mapper_twice_is_no_change():
    before = DOMAIN_MEMBERS.of((EXTENSION_ID,))

    DOMAIN_MEMBERS.add(before[0])

    assert DOMAIN_MEMBERS.of((EXTENSION_ID,)) == before


@pytest.mark.parametrize("value", [False, 0, "", [], None])
def test_a_member_the_request_has_reaches_the_mapper_whatever_its_value(value):
    seen = []

    class Recording:
        extension_id = EXTENSION_ID
        members = ("abuse",)

        def to_model(self, present):
            seen.append(present)
            return []

    mappers = MemberMappers(merge=lambda results: results)
    mappers.add(Recording())

    rest, _ = mappers.split({"name": "a.de", "abuse": value}, "domainName.create", (EXTENSION_ID,))

    assert seen == [{"abuse": value}] and rest == {"name": "a.de"}


def test_a_full_update_states_the_members_so_an_omitted_one_is_the_empty_value():
    members = CONTACT_MEMBERS.members("contact.update", (EXTENSION_ID,))

    rest, held = CONTACT_MEMBERS.split({"contactInfo": {}}, "contact.update", (EXTENSION_ID,), stated=members)

    assert rest == {"contactInfo": {}} and held[EXTENSION_ID].blocks == []


def test_a_preset_without_the_extension_makes_no_entry_even_for_a_full_update():

    rest, held = CONTACT_MEMBERS.split({"contactInfo": {}}, "contact.update", (), stated=())

    assert held == {}


def test_a_patch_states_only_the_members_it_names_and_drops_the_others_unconverted():
    read = {"contactInfo": {}, "verifications": [{"@type": "verificationInformation", "claims": ["name"], "result": "success"}]}

    rest, untouched = CONTACT_MEMBERS.split(read, "contact.update", (EXTENSION_ID,), stated=frozenset())
    _, removed = CONTACT_MEMBERS.split({"contactInfo": {}}, "contact.update", (EXTENSION_ID,), stated={"verifications"})

    assert rest == {"contactInfo": {}} and untouched == {}
    assert removed[EXTENSION_ID].blocks == []


def test_the_members_of_a_contact_are_shown_as_the_read_definition_has_them():
    contact = Contact(id="DENIC-1-X", extensions={EXTENSION_ID: ContactVerifications(
        blocks=[VerificationInformation(claims=["name"], result="success")])})

    assert CONTACT_MEMBERS.to_rpp(contact, "contact.read", (EXTENSION_ID,)) == {"verifications": [
        {"@type": "verificationInformation", "claims": ["name"], "result": "success"}]}
    assert CONTACT_MEMBERS.to_rpp(contact, "contact.read", ()) == {}
    assert CONTACT_MEMBERS.to_rpp(Contact(id="DENIC-1-X"), "contact.read", (EXTENSION_ID,)) == {}
