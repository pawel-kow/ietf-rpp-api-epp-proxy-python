from dataclasses import replace

import pytest
from connexion import ProblemException

from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.domain.domains import ContactReference
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.operation import map_request
from rpp.mapping.domain import domain_patch, domain_replacement, domains
from tests.helper.epp_ns_map import EPP_NS_MAP
from tests.helper.epp_app_context import epp_app_context  # noqa: F401, a fixture

NAME = "foo.example"

OTHER = replace(
    EPP_PROFILE, name="Other", contact_labels=("generalRequest", "abuse"), domain_record_types=("ns", "dnskey", "mx"),
)


def create(profile, **members):
    return domains.rpp_to_model({"@type": "domainName", "name": NAME, **members}, profile=profile)


def contact(label, contact_id="c1"):
    return {"label": label, "object": {"@type": "contact", "id": contact_id}}


def records(*records):
    return {"@type": "dnsData", "records": list(records)}


DS = {"@type": "dnsRecord", "name": "@", "type": "ds", "rdata": {
    "keyTag": "12345", "algorithm": "8", "digestType": "2", "digest": "49FD46E6C4B45C55D4AC" * 3 + "49FD",
}}


def test_epp_holds_the_contact_roles_of_rfc_5731():
    assert EPP_PROFILE.contact_labels == ("admin", "billing", "tech")


def test_the_epp_backend_has_the_epp_profile():
    assert EppBackend(None, EPP_NS_MAP).profile == EPP_PROFILE


def test_the_epp_backend_offers_the_lgrs_of_its_idn_tables():
    backend = EppBackend(None, EPP_NS_MAP, IdnTables({"latn-1.0": "de"}))

    assert backend.profile == replace(EPP_PROFILE, lgrs=frozenset({"latn-1.0"}))


def test_a_contact_label_of_the_backend_is_accepted():
    assert create(OTHER, contacts=[contact("abuse")]).contacts == [ContactReference(id="c1", types=["abuse"])]


def test_a_contact_label_epp_knows_is_refused_by_another_backend():
    with pytest.raises(NotSupportedByBackend, match="Contact label 'admin'"):
        create(OTHER, contacts=[contact("admin")])


def test_a_contact_label_of_a_patch_is_checked_against_the_backend():
    add = [{"op": "add", "path": "/contacts", "value": contact("tech")}]

    with pytest.raises(NotSupportedByBackend):
        domain_patch.rpp_to_model(NAME, add, profile=OTHER)
    assert domain_patch.rpp_to_model(NAME, add, profile=EPP_PROFILE) is not None


def test_a_contact_label_of_a_full_update_is_checked_against_the_backend():
    body = {"@type": "domainName", "contacts": [contact("billing")]}

    with pytest.raises(NotSupportedByBackend):
        domain_replacement.rpp_to_model(NAME, body, profile=OTHER)


def test_a_record_type_the_backend_does_not_hold_at_the_apex_is_refused():
    with pytest.raises(NotSupportedByBackend, match="DNS record type 'ds'"):
        create(OTHER, dns=records(DS))
    assert create(EPP_PROFILE, dns=records(DS)).dnsSEC is not None


def test_a_refusal_names_the_backend_of_the_application(epp_app_context):
    epp_app_context.config["RPP_BACKEND_PROFILE"] = OTHER

    with pytest.raises(ProblemException) as refused:
        map_request(create, OTHER, contacts=[contact("admin")])

    assert refused.value.detail == "Contact label 'admin' cannot be expressed in Other"
    assert refused.value.headers["RPP-Code"] == "02102"


def test_a_refusal_for_epp_names_epp(epp_app_context):
    with pytest.raises(ProblemException) as refused:
        map_request(create, EPP_PROFILE, contacts=[contact("reseller")])

    assert refused.value.detail == "Contact label 'reseller' cannot be expressed in EPP"
