import pytest
from jsonschema import ValidationError

from models import Discovery
from rpp_to_model_mapper import discovery


def a_discovery(**changes):
    values = dict(
        version="1.0", base_url="https://rpp.example/rpp", tlds=["example"], environment_name="rpp.example",
        environment_status="test", objects=["domainName", "host", "contact"], datetime="2026-05-31T12:30:00Z",
        profiles=["urn:ietf:params:rpp:profile:epp-compatibility"],
    )
    return Discovery(**{**values, **changes})


def test_all_required_members():
    assert discovery.model_to_rpp(a_discovery()) == {
        "@type": "discovery",
        "versions": [{"@type": "discoveryVersion", "version": "1.0", "baseUrl": "https://rpp.example/rpp"}],
        "environment": {"@type": "discoveryEnvironment", "name": "rpp.example", "status": "test"},
        "tlds": ["example"],
        "profiles": ["urn:ietf:params:rpp:profile:epp-compatibility"],
        "objects": ["domainName", "host", "contact"],
        "datetime": "2026-05-31T12:30:00Z",
    }


def test_no_tlds_is_invalid():
    with pytest.raises(ValidationError):
        discovery.model_to_rpp(a_discovery(tlds=[]))
