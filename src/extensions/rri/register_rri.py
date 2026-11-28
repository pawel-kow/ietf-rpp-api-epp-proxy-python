import json
from pathlib import Path

import yaml

from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from extensions.rri.rpp.mapping.contact_members import ContactVerificationMembers
from extensions.rri.rpp.mapping.messages import RriMessageMapper
from extensions.rri.rpp.mapping.request_contact_members import RequestContactMembers
from extensions.rri.rpp.mapping.request_template_members import RequestTemplateMembers
from extensions.rri.rpp.schema.openapi_fragment import HANDLERS, openapi_fragment
from registration import ExtensionRegistry, RegisteredExtension
from rpp.mapping.contact.contact_members import CONTACT_MEMBERS
from rpp.mapping.domain.domain_members import DOMAIN_MEMBERS
from rpp.mapping.message.message_mappers import MESSAGE_MAPPERS
from rpp.mapping.organisation.organisation_members import ORGANISATION_MEMBERS

SCHEMAS = Path(__file__).parent / "rpp" / "schema"

# The top-level data elements of the objects, with their Visibility (docs/rri/rri-extension.md): a request contact has none
# with onDemand Visibility.
DATA_OBJECTS = {
    "requestContact": {"id": "default", "provMetadata": "default", "uriTemplate": "default"},
}

PRESET_KEY = "rri"

STRICT_PRESET_KEY = "rri-strict"

PROFILE_KEY = "rri"

# The Process Objects it adds to a domain name (docs/rri/rri-extension.md).
PROCESSES = {"domainName": ("authInfoProcess", "authInfoIssueProcess", "verificationProcess", "releaseProcess")}

# The operations of each, the leaves the test selectors read.
AUTH_INFO_PROCESS = "domainName.processes.authInfoProcess.operations"

AUTH_INFO_ISSUE_PROCESS = "domainName.processes.authInfoIssueProcess.operations"

VERIFICATION_PROCESS = "domainName.processes.verificationProcess.operations"

RELEASE_PROCESS = "domainName.processes.releaseProcess.operations"

# The request contacts of a domain, 0 to 1 of each role (rri 5.0 reference §5.2): a domain needs none.
REQUEST_CONTACT_LIMITS = {"min_count": 0, "max_count": 1}


def _definition(name: str) -> dict:
    """A definition file of the extension (`rri-preset.yaml`, `rri-strict-preset.yaml`, `rri-profile.yaml`)."""
    return yaml.safe_load((SCHEMAS / name).read_text(encoding="utf-8"))


def _profile() -> dict:
    """The DENIC RRI profile (docs/rri/rri-profile.md) with its Profile Schema."""
    return {**_definition("rri-profile.yaml"),
            "schema": json.loads((SCHEMAS / "rri-profile.schema.json").read_text(encoding="utf-8"))}


def register(registry: ExtensionRegistry) -> None:
    """Registers every part of the extension in the pipeline: its schema, the data model, the OpenAPI fragment and the
    handlers of its request contact paths, the mapper of the request contacts of a domain, the one of the request templates of an organisation, the mapper of its message types, its part of the RRI backend, the
    leaves it adds to the backend profile, and the RPP presets that offer it (the preset `rri`, and `rri-strict` with the DENIC RRI profile applied) with the profile."""
    CONTACT_MEMBERS.add(ContactVerificationMembers())
    DOMAIN_MEMBERS.add(RequestContactMembers())
    ORGANISATION_MEMBERS.add(RequestTemplateMembers())
    MESSAGE_MAPPERS.add(RriMessageMapper())
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads((SCHEMAS / "rri-extension.schema.json").read_text(encoding="utf-8")),
        data_objects=DATA_OBJECTS,
        objects=("requestContact",),
        processes=PROCESSES,
        openapi=openapi_fragment,
        handlers=HANDLERS,
        profile_layer={
            "objects": ["requestContact"],
            "extensions": [EXTENSION_ID],
            "presets": [PRESET_KEY],
            "default_preset": PRESET_KEY,
            "domainName": {"generalRequest": REQUEST_CONTACT_LIMITS, "abuse": REQUEST_CONTACT_LIMITS,
                           "processes": {"authInfoProcess": {"operations": ["create", "read", "delete"]},
                                         "authInfoIssueProcess": {"operations": ["create"]},
                                         "verificationProcess": {"operations": ["read"]},
                                         "releaseProcess": {"operations": ["create"]}}},
        },
        profile_leaves={**{f"domainName.{role}.{limit}": int for role in ("generalRequest", "abuse")
                           for limit in ("min_count", "max_count")},
                        AUTH_INFO_PROCESS: tuple, AUTH_INFO_ISSUE_PROCESS: tuple, VERIFICATION_PROCESS: tuple, RELEASE_PROCESS: tuple},
        presets={PRESET_KEY: _definition("rri-preset.yaml"), STRICT_PRESET_KEY: _definition("rri-strict-preset.yaml")},
        profiles={PROFILE_KEY: _profile()},
    ))
