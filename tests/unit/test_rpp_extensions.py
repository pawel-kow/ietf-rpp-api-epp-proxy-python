"""The RPP extensions of the proxy (json §7): each composes, with `allOf`, the effective schema of the objects it
extends, and discovery describes it (json §6.2.12)."""
import re

import pytest
from jsonschema import ValidationError

from rpp.http.app import create_app
from rpp.schema.extensions import EXTENSIONS
from rpp.schema.validator import validate_schema
from tests.helper.profiles import EPP_PROFILE

TRANSFER = {"@type": "domainTransferProcess"}

DATA = {
    "registrant": {"@type": "contact", "id": "DENIC-1000022-HOLDER"},
    "dns": {"@type": "dnsData", "records": [
        {"@type": "dnsRecord", "name": "@", "type": "a", "rdata": {"address": "192.0.2.10"}}]},
}

SEMVER = r"\d+\.\d+\.\d+"


def test_the_rri_extension_describes_itself():
    extension = EXTENSIONS["rri"]

    assert extension.id == "rri"
    assert extension.name == "DENIC RRI"
    assert re.fullmatch(SEMVER, extension.version)
    assert extension.url.startswith("https://")


def test_without_an_extension_the_base_schema_applies():
    validate_schema("domainTransferProcess.create", TRANSFER)


def test_the_rri_extension_requires_the_domain_data_on_a_transfer():
    with pytest.raises(ValidationError, match="registrant"):
        validate_schema("domainTransferProcess.create", TRANSFER, extensions=("rri",))


def test_the_rri_extension_takes_the_domain_data_on_a_transfer():
    validate_schema("domainTransferProcess.create", {**TRANSFER, **DATA}, extensions=("rri",))


def test_the_rri_extension_checks_its_members_with_the_base_definitions():
    with pytest.raises(ValidationError):
        validate_schema("domainTransferProcess.create",
                        {**TRANSFER, **DATA, "registrant": {"@type": "contact"}}, extensions=("rri",))


def test_an_extension_leaves_the_objects_it_does_not_extend_alone():
    validate_schema("domainName.create", {"@type": "domainName", "name": "example.de"}, extensions=("rri",))


def test_an_unknown_extension_is_a_key_error():
    with pytest.raises(KeyError):
        validate_schema("domainTransferProcess.create", TRANSFER, extensions=("nope",))


def test_an_app_whose_profile_offers_an_unknown_extension_does_not_start():
    with pytest.raises(ValueError, match="nope"):
        create_app(None, EPP_PROFILE.with_changes({"extensions": ["nope"]}))
