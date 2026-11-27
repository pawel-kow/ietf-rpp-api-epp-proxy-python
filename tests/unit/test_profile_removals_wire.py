"""The removal of a member that an applicable profile requires in the update definition (spec-issues.md, two-step validation of a
patch): refused with that profile (422 02308) on the patch of a contact and of a host, which is applied to the object read for
it, and nothing is sent but the read. Under a preset without the profile the same patch is sent."""
import base64

from core.session.session_pool import SessionPool
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient
from tests.helper.preset_fixtures import BASE, preset, profile, registry_with
from tests.helper.profiles import EPP_PROFILE
from tests.unit.test_contact_put_wire import DONE, info as contact_info
from tests.unit.test_host_wire import info as host_info
from tests.unit.test_rri_wire import DISCOVERY
from tests.unit.test_preset_profile_constraints_wire import epp_reply

MEDIA_TYPE = "application/rpp+json"
AUTH = {"Authorization": "Basic " + base64.b64encode(b"user:pw").decode(), "Accept": MEDIA_TYPE,
        "Content-Type": MEDIA_TYPE, "RPP-Cltrid": "cl-1"}

# profiles that require a top-level member of an update definition
NEEDS_CONTACT_INFO = profile("needs-contact-info", constraints={"contact.update": "profile.c"}, defs={
    "profile.c": {"required": ["contactInfo"]}})
NEEDS_DNS = profile("needs-dns", constraints={"host.update": "profile.h"}, defs={"profile.h": {"required": ["dns"]}})

PLAIN = preset("plain", base_presets=[BASE["id"]])
CONTACTS = preset("contacts", base_presets=[BASE["id"]], profiles=[NEEDS_CONTACT_INFO[0]])
HOSTS = preset("hosts", base_presets=[BASE["id"]], profiles=[NEEDS_DNS[0]])


def app(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, reply=(True, "1000", epp_reply()), replies=list(replies)))
        return clients[-1]

    profile_ = EPP_PROFILE.with_changes({"presets": ["plain", "contacts", "hosts"], "default_preset": "plain"})
    http = create_app(SessionPool(epp_backends(factory)), profile_, discovery_settings=DISCOVERY,
                      registry=registry_with([PLAIN, CONTACTS, HOSTS], [NEEDS_CONTACT_INFO, NEEDS_DNS])).test_client()
    return http, clients


def named(chosen):
    return {**AUTH, "RPP-Preset": f"preset={chosen[0]};version=1.0"}


def sent(clients):
    return [message for client in clients for message in client.sent]


def test_the_removal_of_a_member_the_contact_update_requires_is_a_422_and_sends_nothing_but_the_read():
    http, clients = app(contact_info())

    response = http.patch("/contacts/JD-1234", json=[{"op": "remove", "path": "/contactInfo"}], headers=named(CONTACTS))

    assert response.status_code == 422 and response.headers["RPP-Code"] == "02308"
    assert response.json()["errors"][0]["profile"] == NEEDS_CONTACT_INFO[0]
    assert len(sent(clients)) == 1 and "contact:info" in sent(clients)[0]


def test_the_removal_of_a_member_the_host_update_requires_is_a_422_and_sends_nothing_but_the_read():
    http, clients = app(host_info())

    response = http.patch("/hosts/ns1.example.example", json=[{"op": "remove", "path": "/dns"}], headers=named(HOSTS))

    assert response.status_code == 422 and response.headers["RPP-Code"] == "02308"
    assert response.json()["errors"][0]["profile"] == NEEDS_DNS[0]
    assert len(sent(clients)) == 1 and "host:info" in sent(clients)[0]


def test_the_same_removal_is_refused_by_the_preset_schema_alone_under_a_preset_without_the_profile():
    """`contactInfo` is required by RPP itself (step 1, 400), which the profile restates: without the profile only step 1 refuses."""
    http, clients = app(contact_info())

    response = http.patch("/contacts/JD-1234", json=[{"op": "remove", "path": "/contactInfo"}], headers=named(PLAIN))

    assert (response.status_code, response.headers["RPP-Code"]) == (400, "02001")
    assert len(sent(clients)) == 1
