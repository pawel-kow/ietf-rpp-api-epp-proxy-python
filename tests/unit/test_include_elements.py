"""Visibility and `includeElements` (data-objects §2.4, §2.7.3, core §16.1.7), see spec-issues.md."""
from eppclient.epp_profile import EPP_PROFILE
import pytest

from models import AuthInfo
from rpp_to_model_mapper import contact_replacement, domain_replacement, include_elements
from tests.helper.contact_fixtures import put_body

PASSWORD = {"@type": "authInfo", "method": "authinfo", "authdata": "NewSecret1!x"}
DOMAIN_BODY = {"@type": "domainName", "nameservers": [{"@type": "host", "hostName": "ns1.foo.example"}]}


def test_the_identifiers_of_the_object_are_accepted():
    assert include_elements.rpp_to_model("domainName", ["authInfo", "status"]) == {"authInfo", "status"}


@pytest.mark.parametrize("identifiers", [["authinfo"], ["authInfo,status"], ["contactInfo"], ["provMetadata.crDate"]])
def test_an_identifier_that_is_not_a_top_level_element_is_rejected(identifiers):
    with pytest.raises(ValueError, match="is not a data element"):
        include_elements.rpp_to_model("domainName", identifiers)


@pytest.mark.parametrize("object_identifier", ["domainName", "contact"])
def test_auth_info_is_shown_only_when_requested(object_identifier):
    rpp = {"name": "x", "authInfo": PASSWORD}

    assert "authInfo" not in include_elements.visible(object_identifier, rpp, frozenset())
    assert include_elements.visible(object_identifier, rpp, frozenset({"authInfo"})) == rpp


def test_a_default_element_is_always_shown():
    rpp = {"hostName": "ns1.foo.example", "status": []}

    assert include_elements.visible("host", rpp, frozenset()) == rpp


def domain_intent(body, requested=frozenset()):
    return domain_replacement.rpp_to_model("foo.example", body, requested, profile=EPP_PROFILE)


def contact_intent(body, requested=frozenset()):
    return contact_replacement.rpp_to_model("JD-1234", body, requested)


@pytest.mark.parametrize("intent, body", [(domain_intent, DOMAIN_BODY), (contact_intent, put_body())])
def test_a_full_update_without_the_request_leaves_auth_info_alone(intent, body):
    assert intent(body).unchanged == {"authInfo"}


@pytest.mark.parametrize("intent, body", [(domain_intent, DOMAIN_BODY), (contact_intent, put_body())])
def test_a_full_update_sending_auth_info_it_does_not_include_is_rejected(intent, body):
    with pytest.raises(ValueError, match="includeElements=authInfo"):
        intent({**body, "authInfo": PASSWORD})


@pytest.mark.parametrize("intent, body", [(domain_intent, DOMAIN_BODY), (contact_intent, put_body())])
def test_a_full_update_including_auth_info_sets_it(intent, body):
    result = intent({**body, "authInfo": PASSWORD}, frozenset({"authInfo"}))

    assert result.unchanged == frozenset() and result.authInfo == AuthInfo(pw="NewSecret1!x")


@pytest.mark.parametrize("intent, body", [(domain_intent, DOMAIN_BODY), (contact_intent, put_body())])
def test_a_full_update_including_auth_info_and_omitting_it_clears_it(intent, body):
    result = intent(body, frozenset({"authInfo"}))

    assert result.unchanged == frozenset() and result.authInfo is None
