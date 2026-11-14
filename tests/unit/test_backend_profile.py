
import pytest
from connexion import ProblemException

from core.capabilities.backend_requirement import BackendRequirement
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.domain.domains import ContactReference
from core.model.message.queue_message import QueueMessage
from registry_adapter.epp.gateways.epp_backend import EppBackend
from tests.helper.profiles import EPP_PROFILE, RRI_PROFILE
from rpp.http.operation import map_request
from rpp.mapping.domain import domain_patch, domain_replacement, domain_restore_report, domains
from rpp.mapping.message import messages
from tests.helper.epp_ns_map import EPP_NS_MAP
from tests.unit.test_rpp_domain_restore_mapper import REPORT
from tests.helper.epp_app_context import epp_app_context  # noqa: F401, a fixture

NAME = "foo.example"

OTHER = EPP_PROFILE.with_changes({"name": "Other", "domainName": {
    "contacts": {"labels": ["generalRequest", "abuse"]}, "dns": {"record_types": ["ns", "dnskey", "mx"]}}})


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
    assert EPP_PROFILE.domainName.contacts.labels == ("admin", "billing", "tech")


def test_the_epp_backend_has_the_epp_profile():
    assert EppBackend(None, EPP_NS_MAP, EPP_PROFILE).profile == EPP_PROFILE




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


def test_a_value_not_in_the_form_of_the_backend_is_a_400_that_names_it(epp_app_context):
    epp_app_context.config["RPP_BACKEND_PROFILE"] = OTHER
    report = {"@type": "restoreProcess", "restoreReport": {**REPORT, "statements": REPORT["statements"][:1]}}

    with pytest.raises(ProblemException) as refused:
        map_request(domain_restore_report.rpp_to_model, NAME, report, profile=OTHER)

    assert refused.value.status == 400
    assert refused.value.detail == "Other requires exactly 2 statements in the restore report"


def test_a_backend_requirement_without_a_backend_says_the_backend():
    refusal = BackendRequirement("Phone number '{1}' is not an {backend} number")

    assert str(refusal) == "Phone number '{1}' is not an the backend number"
    assert refusal.detail("EPP") == "Phone number '{1}' is not an EPP number"


def test_a_message_the_proxy_cannot_translate_names_the_backend():
    message = QueueMessage(id="1", creationDate="2026-11-11T00:00:00Z", lang=None, text="Hi", unmapped="urn:example:x")

    assert "The Other message carried data" in messages.model_to_rpp(message, backend_name="Other")["data"]["message"]


def test_a_profile_reads_as_a_tree():
    assert EPP_PROFILE.contact.fax.supported is True
    assert EPP_PROFILE.fact("domainName.processes.transfer.operations") == (
        "request", "query", "cancel", "approve", "reject")


@pytest.mark.parametrize("path", ["contact.fax", "contact.nope", "nope", "contact.fax.supported.x"])
def test_a_path_that_names_no_leaf_is_a_key_error(path):
    with pytest.raises(KeyError):
        EPP_PROFILE.fact(path)


def test_an_attribute_the_profile_lacks_is_named():
    with pytest.raises(AttributeError, match="contact.nope"):
        EPP_PROFILE.contact.nope


def test_a_later_layer_merges_maps_and_replaces_lists():
    changed = EPP_PROFILE.with_changes({"contact": {"fax": {"supported": False}}, "objects": ["domainName"]})

    assert changed.contact.fax.supported is False
    assert changed.contact.region.supported is True
    assert changed.objects == ("domainName",)
    assert EPP_PROFILE.contact.fax.supported is True


@pytest.mark.parametrize("changes, error", [
    ({"contact": {"fax": {"suported": True}}}, "unknown contact.fax.suported"),
    ({"contact": {"fax": "yes"}}, "unknown contact.fax; missing contact.fax.supported"),
    ({"contact": {"fax": {"supported": "yes"}}}, "contact.fax.supported must be of type bool"),
    ({"contact": {"phone": {"max_count": True}}}, "contact.phone.max_count must be of type int"),
    ({"objects": "domainName"}, "objects must be a list of strings"),
])
def test_a_wrong_profile_is_refused_with_the_leaf(changes, error):
    with pytest.raises(ValueError, match=error):
        EPP_PROFILE.with_changes(changes)


def test_the_generic_profiles_have_every_leaf():
    assert RRI_PROFILE.name == "RRI"
    assert "host" not in RRI_PROFILE.objects
