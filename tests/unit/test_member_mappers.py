"""The registry of the mappers of the members extensions add to a base object (rpp/mapping/shared/member_mappers.py), with the
domain's one and the rri extension's mapper."""
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from rpp.mapping.domain.domain_members import DOMAIN_MEMBERS
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
    assert DOMAIN_MEMBERS.to_rpp({"abuse": "X", "admin": "Y"}, "domainName.read", (EXTENSION_ID,)) == {
        "abuse": {"@type": "requestContact", "id": "X"}}


def test_registering_a_mapper_twice_is_no_change():
    before = DOMAIN_MEMBERS.of((EXTENSION_ID,))

    DOMAIN_MEMBERS.add(before[0])

    assert DOMAIN_MEMBERS.of((EXTENSION_ID,)) == before
