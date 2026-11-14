import pytest
from jsonschema import ValidationError

from core.model.shared.discovery import Discovery
from rpp.mapping.discovery import discovery


def a_discovery(**changes):
    values = dict(
        version="1.0", base_url="https://rpp.example/rpp", tlds=["example"], environment_name="rpp.example",
        environment_status="test", objects=["domainName", "host", "contact"], datetime="2026-05-31T12:30:00Z",
        profiles=["urn:ietf:params:rpp:profile:epp-compatibility"],
        extensions=[],
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


def test_an_offered_extension_is_described():
    """Json §6.2.12, from the extension's schema file."""
    extensions = discovery.model_to_rpp(a_discovery(extensions=["rri"]))["extensions"]

    assert extensions == [{"@type": "extension", "name": "DENIC RRI", "id": "rri", "version": "0.1.0",
                           "url": "https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/"
                                  "rri-extension.schema.json"}]
