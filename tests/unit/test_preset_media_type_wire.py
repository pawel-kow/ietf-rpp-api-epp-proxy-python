"""Preset signalling with the media type parameters (core §14.3): the selection, its refusals and the response."""
import pytest

from core.session.session_pool import SessionPool
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient
from tests.helper.fake_rri_client import FakeRriClient, rri_backends
from tests.helper.integration_api_test import header_list
from tests.helper.profiles import EPP_PROFILE, RRI_PROFILE, RRI_REGISTRY
from tests.unit.test_presets_wire import BASE, EPP, RRI
from tests.unit.test_rpp_wire import check_reply
from tests.unit.test_rri_adapter import DOMAIN_INFO, NAME
from tests.unit.test_rri_request_contacts import HANDLE, REQUEST_INFO
from tests.unit.test_rri_wire import DISCOVERY, HEADERS, MEDIA_TYPE

PATH = "/.well-known/rpp"
AUTH = {name: value for name, value in HEADERS.items() if name != "Accept"}


def epp_client():
    sessions = SessionPool(epp_backends(lambda username, password: FakeEppClient(username, password)))
    return create_app(sessions, EPP_PROFILE, discovery_settings=DISCOVERY, signalling="media-type").test_client()


def rri_client(*replies):
    sessions = SessionPool(rri_backends(lambda username, password: FakeRriClient(username, password, replies=list(replies))))
    return create_app(sessions, RRI_PROFILE, discovery_settings=DISCOVERY, signalling="media-type", registry=RRI_REGISTRY).test_client()


def media(name, version="1.0", weight=None):
    return f'{MEDIA_TYPE}; preset="{name}"; preset-version="{version}"' + (f"; q={weight}" if weight else "")


def get(accept, client=None, **extra):
    return (client or epp_client()).get(PATH, headers={**AUTH, "Accept": accept, **extra})


def applied(response):
    return response.headers["Content-Type"]


def assert_refused(response, status, code):
    assert response.status_code == status
    assert response.headers["RPP-Code"] == code
    assert response.headers["Content-Type"] == "application/problem+json"  # no preset parameters
    assert "accept" in header_list(response.headers["Vary"])
    assert "RPP-Preset" not in response.headers


def test_a_request_without_parameters_gets_the_default_profile_and_it_is_named_in_the_content_type():
    response = get(MEDIA_TYPE)

    assert response.status_code == 200
    assert applied(response) == media(EPP)
    assert "RPP-Preset" not in response.headers
    assert "accept" in header_list(response.headers["Vary"])


def test_a_request_without_an_accept_gets_the_default_profile():
    response = epp_client().get(PATH, headers=AUTH)

    assert response.status_code == 200 and applied(response) == media(EPP)


@pytest.mark.parametrize("name", [BASE, EPP])
def test_the_accept_selects_an_offered_profile(name):
    assert applied(get(media(name), **{"Content-Type": media(name)})) == media(name)


def test_a_token_value_is_the_same_as_a_quoted_one():
    response = get(f"{MEDIA_TYPE}; preset=de.denic.rpp.preset.rri; preset-version=1.0", client=rri_client())

    assert applied(response) == media(RRI)


def test_the_version_is_compared_as_a_decimal():
    assert applied(get(media(EPP, "1.00"))) == media(EPP)


def test_the_highest_weight_is_answered_and_a_weight_of_zero_excludes():
    both = f"{media(EPP, weight='0.5')}, {media(BASE, weight='0.9')}"
    assert applied(get(both)) == media(BASE)
    assert applied(get(f"{media(BASE, weight='0')}, {media(EPP)}")) == media(EPP)


def test_equal_weights_answer_the_profile_of_the_request():
    both = f"{media(BASE)}, {media(EPP)}"

    assert applied(get(both)) == media(EPP)                                  # the default, no Content-Type
    assert applied(get(both, **{"Content-Type": media(BASE)})) == media(BASE)
    assert applied(get(both, **{"Content-Type": media(EPP)})) == media(EPP)


def test_the_response_profile_can_differ_from_the_request_profile():
    response = get(f"{media(EPP)}, {media(BASE, weight='0.5')}", **{"Content-Type": media(BASE)})

    assert response.status_code == 200 and applied(response) == media(EPP)


def test_a_wildcard_stands_for_every_profile_and_the_default_answers():
    assert applied(get("*/*")) == media(EPP)
    assert applied(get("application/*")) == media(EPP)
    # the most specific range gives the weight: base is excluded, the wildcard accepts the rest
    assert applied(get(f"{media(BASE, weight='0')}, */*;q=0.1")) == media(EPP)


def test_a_bare_range_stands_for_the_default_profile_only():
    assert applied(get(f"{MEDIA_TYPE};q=0.2, {media(BASE, weight='0.1')}")) == media(EPP)


def test_a_range_of_another_media_type_is_ignored():
    assert applied(get(f"text/html, {media(BASE)}", **{"Content-Type": media(BASE)})) == media(BASE)


@pytest.mark.parametrize("accept", [
    media("nope"), media(EPP, "2.0"), media(EPP, "1.1"), media(EPP, weight="0"), "text/html",
    f"{media(RRI)}, {media(EPP, weight='0')}",
])
def test_no_profile_the_server_offers_is_a_406(accept):
    assert_refused(get(accept), 406, "02004")


@pytest.mark.parametrize("accept, code", [
    (f"{MEDIA_TYPE}; preset={EPP}", "02005"),                   # a colon needs quotes: not a token
    (f"{MEDIA_TYPE}; preset=x", "02003"),                       # no version
    (f"{MEDIA_TYPE}; preset-version=1.0", "02003"),
    (f'{MEDIA_TYPE}; preset="{EPP}"; preset-version=1', "02005"),
    (f"{MEDIA_TYPE}; q=2", "02005"),
])
def test_a_value_that_cannot_be_read_is_a_400(accept, code):
    assert_refused(get(accept), 400, code)


def test_the_header_of_the_other_method_is_a_400():
    response = get(MEDIA_TYPE, **{"RPP-Preset": f"preset={EPP};version=1.0"})

    assert_refused(response, 400, "02001")
    assert "RPP-Preset" in response.json()["detail"]


def post(content_type, accept, client=None, body=None):
    headers = {**AUTH, "Accept": accept}
    if content_type is not None:
        headers["Content-Type"] = content_type
    return (client or epp_client()).post("/domainNames", json=body if body is not None else {}, headers=headers)


def test_an_unsupported_profile_or_version_of_the_content_is_a_415():
    for content_type in (media("nope"), media(EPP, "2.0"), media(RRI)):
        assert_refused(post(content_type, media(EPP)), 415, "02004")


def test_a_content_profile_that_the_accept_does_not_list_is_a_400():
    assert_refused(post(media(BASE), media(EPP)), 400, "02001")
    assert_refused(post(media(BASE), MEDIA_TYPE), 400, "02001")          # a bare range is the default
    assert_refused(post(media(BASE), media(EPP) + ", " + media(BASE, weight="0")), 400, "02001")


def test_a_content_profile_that_a_wildcard_lists_is_accepted():
    response = post(media(BASE), "*/*", body={"@type": "domainName", "name": "x.de"})

    # past the selection: what answers is the fake backend, which has no reply to give
    assert response.status_code == 500


def test_the_order_of_the_refusals_is_unreadable_then_415_then_406_then_400():
    assert post(media("nope"), media("nope")).status_code == 415
    assert post(media(EPP), "text/html").status_code == 406
    assert post(media(EPP), "garbage").status_code == 400


def test_a_content_type_without_parameters_is_the_default_profile_for_content():
    assert_refused(post(MEDIA_TYPE, media(BASE)), 400, "02001")


def test_the_request_profile_is_the_content_type_of_a_request_without_content_too():
    bare_and_base = epp_client().get(PATH, headers={**AUTH, "Accept": media(BASE), "Content-Type": MEDIA_TYPE})
    absent_and_base = get(media(BASE))
    named = epp_client().get(PATH, headers={**AUTH, "Accept": media(BASE), "Content-Type": media(BASE)})
    unoffered = epp_client().get(PATH, headers={**AUTH, "Accept": media(BASE), "Content-Type": media(RRI)})

    # no parameters, or no Content-Type, is the default preset, which the Accept must list
    assert_refused(bare_and_base, 400, "02001")
    assert_refused(absent_and_base, 400, "02001")
    assert named.status_code == 200 and applied(named) == media(BASE)
    assert_refused(unoffered, 415, "02004")


def test_the_content_profile_reads_the_content_whatever_the_response_profile_is():
    client = rri_client()
    body = {"@type": "domainName", "name": "foo.de", "generalRequest": {"@type": "requestContact", "id": "X-1"}}
    under_rri = post(media(RRI), f"{media(RRI)}, {media(BASE, weight='0.5')}", client=client, body=body)
    under_base = post(media(BASE), media(BASE), client=client, body=body)
    base_content_rri_answer = post(media(BASE), f"{media(RRI)}, {media(BASE, weight='0.5')}", client=client, body=body)
    rri_content_base_answer = post(media(RRI), f"{media(RRI)};q=0.1, {media(BASE)}", client=client, body=body)

    # the rri member is declared under rri (the request goes on to the mapper) and undeclared under base
    assert under_rri.status_code == 501 and under_rri.headers["RPP-Code"] == "02102"
    assert under_base.status_code == 400 and "Undeclared property" in under_base.json()["detail"]
    assert base_content_rri_answer.status_code == 400 and "Undeclared property" in base_content_rri_answer.json()["detail"]
    assert rri_content_base_answer.status_code == 501 and rri_content_base_answer.headers["RPP-Code"] == "02102"


def test_an_object_of_an_extension_outside_the_request_preset_is_a_400_that_names_the_preset():
    client = rri_client()
    under_base = client.get("/requestContacts/x", headers={**AUTH, "Accept": media(BASE), "Content-Type": media(BASE)})
    answered_in_rri = client.get("/requestContacts/x", headers={
        **AUTH, "Accept": f"{media(RRI)}, {media(BASE, weight='0.5')}", "Content-Type": media(BASE)})

    for response in (under_base, answered_in_rri):
        assert response.status_code == 400 and response.headers["RPP-Code"] == "02001"
        assert "preset:base" in response.json()["detail"]
        assert response.headers["Content-Type"] == "application/problem+json"
        assert "accept" in header_list(response.headers["Vary"]) and "RPP-Preset" not in response.headers


def test_an_object_the_request_profile_has_is_not_refused_for_the_response_profile():
    response = rri_client(REQUEST_INFO).get(f"/requestContacts/{HANDLE}", headers={
        **AUTH, "Accept": f"{media(BASE)}, {media(RRI, weight='0.5')}", "Content-Type": media(RRI)})

    assert response.status_code == 200
    assert response.json()["id"] == HANDLE
    assert applied(response) == media(BASE)


def test_a_request_contact_is_read_and_rendered_under_the_request_profile_where_nothing_is_built_lazily(monkeypatch):
    # The object exists in the request preset only: rendering it under the response preset, which lacks it, would look for a
    # schema no preset built (SchemaNotBuilt, a 500). The app builds what a request needs, and builds nothing later.

    response = rri_client(REQUEST_INFO).get(f"/requestContacts/{HANDLE}", headers={
        **AUTH, "Accept": f"{media(BASE)}, {media(RRI, weight='0.5')}", "Content-Type": media(RRI)})

    assert response.status_code == 200, response.text
    assert response.json()["uriTemplate"]


def test_a_problem_detail_after_the_selection_has_no_profile_parameters_and_lists_accept_in_vary():
    response = rri_client().get("/requestContacts/x", headers={**AUTH, "Accept": media(BASE), "Content-Type": media(BASE)})

    assert response.status_code == 400
    assert response.headers["Content-Type"] == "application/problem+json"
    assert "accept" in header_list(response.headers["Vary"])


def test_an_unauthenticated_request_is_a_401_before_any_profile():
    response = epp_client().get(PATH.replace(PATH, "/domainNames/x.de"), headers={"Accept": media("nope")})

    assert response.status_code == 401


def test_the_header_server_refuses_the_parameters_unchanged():
    sessions = SessionPool(epp_backends(lambda username, password: FakeEppClient(username, password)))
    client = create_app(sessions, EPP_PROFILE, discovery_settings=DISCOVERY).test_client()
    response = client.get(PATH, headers={**AUTH, "Accept": media(EPP)})

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02001"
    assert "RPP-Preset" not in response.headers


def test_an_empty_accept_is_an_absent_one_and_the_default_profile_applies():
    response = get("")

    assert response.status_code == 200 and applied(response) == media(EPP)


def test_an_availability_answer_that_is_a_404_has_the_profile_parameters_too():
    def factory(username, password):
        return FakeEppClient(username, password, replies=[check_reply(False)])

    client = create_app(SessionPool(epp_backends(factory)), EPP_PROFILE, discovery_settings=DISCOVERY,
                        signalling="media-type").test_client()
    response = client.get("/domainNames/foo.example/availability", headers={**AUTH, "Accept": media(EPP)})

    assert response.status_code == 404
    assert response.json() == {"@type": "domainNameAvailability", "available": False}
    assert applied(response) == media(EPP)


def test_the_most_specific_range_gives_the_weight_of_a_profile():
    base = {"Content-Type": media(BASE)}

    # the exact range at 0 excludes epp, though the wildcard accepts it; a request under epp is then refused
    assert applied(get(f"{media(EPP, weight='0')}, */*", **base)) == media(BASE)
    assert_refused(get(f"{media(EPP, weight='0')}, */*"), 400, "02001")
    # the exact range at 0.5 for base beats the wildcard at 1 for base, so epp (1, by the wildcard) is preferred
    assert applied(get(f"{media(BASE, weight='0.5')}, */*", **base)) == media(EPP)
    # the exact range for epp at 0.1 beats the bare range at 0.5 for epp, so base (0.3) is preferred
    exact_over_bare = f"{MEDIA_TYPE}; q=0.5, {media(EPP, weight='0.1')}, {media(BASE, weight='0.3')}"
    assert applied(get(exact_over_bare)) == media(BASE)


def test_the_response_is_rendered_with_the_extensions_of_the_response_profile():
    def read(request_profile, accept):
        def factory(username, password):
            return FakeRriClient(username, password, replies=[DOMAIN_INFO])

        client = create_app(SessionPool(rri_backends(factory)), RRI_PROFILE, discovery_settings=DISCOVERY,
                            signalling="media-type", registry=RRI_REGISTRY).test_client()
        return client.get(f"/domainNames/{NAME}", headers={
            **AUTH, "Accept": accept, "Content-Type": media(request_profile)})

    in_base = read(RRI, f"{media(BASE)}, {media(RRI, weight='0.5')}")
    in_rri = read(BASE, f"{media(RRI)}, {media(BASE, weight='0.5')}")

    assert in_base.status_code == 200 and applied(in_base) == media(BASE)
    assert "abuse" not in in_base.json() and in_base.json()["registrant"]["id"]    # an rri member is left out
    assert in_rri.status_code == 200 and applied(in_rri) == media(RRI)
    assert in_rri.json()["abuse"]["id"]
