"""Presets and profiles of the tests, registered as an extension brings them (`RegisteredExtension.presets`, `.profiles`), so
that an app can offer, bind and constrain them without the demo configuration of #180."""
from registration import ExtensionRegistry, RegisteredExtension
from rpp.schema.definitions import Definitions
from rpp.schema.extensions import EXTENSIONS

BASE = {"id": "urn:ietf:params:rpp:preset:base", "version": "1.0"}
BASE_URI = "urn:ietf:params:rpp:schema:json-1.0"


def profile(key, base_profiles=(), required=(), constraints=None, defs=None, version="1.0"):
    """A profile definition. `constraints` maps a definition of the base schema to the key of its sub-schema in `defs`."""
    identifier = f"org.example.rpp.profile.{key}"
    data = {"id": identifier, "name": key, "description": key, "version": version, "rppVersion": "1.0",
            "url": f"https://example.org/{key}", "baseProfiles": [{"id": b, "version": "1.0"} for b in base_profiles],
            "requiredExtensions": [{"id": e, "version": v} for e, v in required]}
    if constraints is not None:
        data["schema"] = {"$id": f"urn:example:schema:{key}", "rpp:profile": {"id": identifier, "version": version},
                          "rpp:constraints": {f"{BASE_URI}#/$defs/{target}": f"#/$defs/{sub}"
                                              for target, sub in constraints.items()},
                          "$defs": defs}
    return identifier, data


def preset(key, base_presets=(), extensions=(), profiles=(), version="1.0"):
    identifier = f"org.example.rpp.preset.{key}"
    return identifier, {"id": identifier, "name": key, "description": key, "version": version, "rppVersion": "1.0",
                        "basePresets": [{"id": b, "version": "1.0"} for b in base_presets],
                        "extensions": [{"id": e, "version": v} for e, v in extensions],
                        "profiles": [{"id": p, "version": "1.0"} for p in profiles]}


# a profile that makes the contact label of a domain one of `admin` (it constrains what RPP leaves open)
ADMIN_ONLY = profile("admin-only", constraints={"domainName.create": "profile.adminOnly"}, defs={
    "profile.adminOnly": {"properties": {"contacts": {"items": {"properties": {"label": {"enum": ["admin"]}}}}}}})

# a profile that requires the authInfo of a domain
AUTH_REQUIRED = profile("auth-required", constraints={"domainName.create": "profile.authRequired"}, defs={
    "profile.authRequired": {"required": ["authInfo"]}})

# a profile that only builds on the first, constraining the number of contacts
AT_MOST_ONE = profile("at-most-one", base_profiles=[ADMIN_ONLY[0]], constraints={"domainName.create": "profile.atMostOne"},
                      defs={"profile.atMostOne": {"properties": {"contacts": {"maxItems": 1}}}})


# a profile that allows one name server, on what a client replaces or patches (domainName.update, and the read
# representation a patch results in)
ONE_NAMESERVER = profile("one-nameserver", constraints={"domainName.update": "profile.oneNs", "domainName.read": "profile.oneNs"},
                         defs={"profile.oneNs": {"properties": {"nameservers": {"maxItems": 1}}}})


# a profile that limits the length of the email address of a contact, which a PATCH sets without a read
SHORT_EMAIL = profile("short-email", constraints={"contact.read": "profile.shortEmail"}, defs={
    "profile.shortEmail": {"properties": {"contactInfo": {"properties": {"emails": {"properties": {
        "email": {"properties": {"address": {"maxLength": 12}}}}}}}}}})


def registry_with(presets=(), profiles=()) -> ExtensionRegistry:
    """A registry of one extension that brings only these presets and profiles (`{key: definition}` pairs)."""
    registry = ExtensionRegistry()
    registry.add(RegisteredExtension(
        id="org.example.rpp.extension.fixture",
        schema={"$id": "https://example.org/fixture", "rpp:extension": {"id": "org.example.rpp.extension.fixture",
                                                                          "name": "Fixture", "version": "1.0"},
                "rpp:extends": {}, "$defs": {}},
        data_objects={}, objects=(), openapi=lambda drafts: {"paths": {}, "components": {"schemas": {}}},
        handlers="rpp.handlers",
        presets={key.rsplit(".", 1)[1]: data for key, data in presets},
        profiles={key.rsplit(".", 1)[1]: data for key, data in profiles}))
    return registry


def definitions_with(presets=(), profiles=()) -> Definitions:
    return Definitions.load(registry_with(presets, profiles), EXTENSIONS)
