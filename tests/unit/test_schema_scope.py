"""The validators of a preset (D18) and the two steps of json §Profiles and Validation, without an app."""
import pytest
from jsonschema import ValidationError

from rpp.schema.definitions import Definitions
from rpp.schema.offered_presets import OfferedPresets
from rpp.schema.profile_constraint_violation import ProfileConstraintViolation
from rpp.schema.schema_scope import SchemaNotBuilt, SchemaScope
from rpp.schema.extensions import EXTENSIONS
from tests.helper.profiles import RRI_REGISTRY
from tests.helper.preset_fixtures import ADMIN_ONLY, AUTH_REQUIRED, BASE, definitions_with, preset, profile

PROV_REQUIRED = profile("prov-required", constraints={"domainName.read": "profile.prov"}, defs={
    "profile.prov": {"properties": {"provMetadata": {"required": ["repositoryId"]}}}})
ONE_CONTACT = profile("one-contact", constraints={"domainName.read": "profile.one"}, defs={
    "profile.one": {"properties": {"contacts": {"maxItems": 1}}}})

READ = {"@type": "domainName", "name": "foo.example", "status": [{"@type": "domainStatus", "label": "ok"}],
        "provMetadata": {"@type": "provMetadata", "spClientId": "clientA", "crClientId": "clientA", "crDate": "2025-01-01T00:00:00Z"}}

# the rri extension refers to the Component Objects of the messages extension, so a preset that has it has that one too
RRI_EXTENSIONS = ("de.denic.rpp.rri", "io.github.pawel-kow.rpp.messages")

PRESET_EXTENSIONS = (*RRI_EXTENSIONS, "io.github.pawel-kow.rpp.domain-lock", "io.github.pawel-kow.rpp.registry-changes")


def scope_of(*profiles, extensions=(), held=()):
    entries = [preset("p", base_presets=[BASE["id"]], profiles=[p[0] for p in profiles],
                      extensions=[(e, EXTENSIONS[e].version) for e in extensions])]
    offered = OfferedPresets.build(definitions_with(entries, list(profiles)), ["p"], "p", {}, held or extensions).offered[0]
    return SchemaScope(offered.extensions, offered.applicable, offered.required)


def test_without_a_profile_the_two_steps_are_the_one_validation():
    scope = SchemaScope.of()

    scope.validate_request("domainName.read", READ)
    with pytest.raises(ValueError, match="Undeclared property"):
        scope.validate_request("domainName.read", {**READ, "surprise": 1})


def test_the_formats_the_definitions_state_are_checked():
    """#233: a value that is not of its `format` is refused, as before #201."""
    scope = SchemaScope.of()
    read = {**READ, "provMetadata": {**READ["provMetadata"], "crDate": "yesterday"}}

    with pytest.raises(ValidationError, match="date-time"):
        scope.validate_request("domainName.read", read)


def test_step_one_fails_with_the_error_of_today_before_a_profile_is_asked():
    scope = scope_of(ADMIN_ONLY)

    with pytest.raises(ValidationError):
        scope.validate_request("domainName.create", {"@type": "domainName", "name": "a.example", "contacts": [{}]})
    with pytest.raises(ValueError, match="Undeclared"):
        scope.validate_request("domainName.create", {"@type": "domainName", "name": "a.example", "x": 1})


def test_step_two_fails_with_the_profile_the_path_and_a_reason_that_holds_no_value_of_the_request():
    scope = scope_of(ADMIN_ONLY)
    body = {"@type": "domainName", "name": "a.example",
            "contacts": [{"label": "secret-label", "object": {"@type": "contact", "id": "C-1"}}]}

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.create", body)

    assert error.value.profile == ADMIN_ONLY[0]
    assert error.value.path == "$.contacts[0].label"
    assert "secret-label" not in error.value.reason and ADMIN_ONLY[0] in error.value.reason


def test_the_profile_is_the_one_whose_sub_schema_failed_among_several():
    scope = scope_of(ADMIN_ONLY, AUTH_REQUIRED)
    contact = {"label": "admin", "object": {"@type": "contact", "id": "C-1"}}

    with pytest.raises(ProfileConstraintViolation) as missing:
        scope.validate_request("domainName.create", {"@type": "domainName", "name": "a.example", "contacts": [contact]})
    with pytest.raises(ProfileConstraintViolation) as label:
        scope.validate_request("domainName.create", {"@type": "domainName", "name": "a.example", "authInfo": {
            "@type": "authInfo", "method": "password", "authdata": "x"}, "contacts": [{**contact, "label": "tech"}]})

    assert missing.value.profile == AUTH_REQUIRED[0] and "authInfo" in missing.value.reason
    assert label.value.profile == ADMIN_ONLY[0]


def test_an_object_a_profile_does_not_constrain_is_not_asked():
    scope_of(ADMIN_ONLY).validate_request("host.create", {"@type": "host", "hostName": "ns.example"})


def test_a_patched_object_is_not_refused_for_a_server_managed_member_but_a_created_one_is():
    scope = scope_of(PROV_REQUIRED)

    scope.validate_request("domainName.read", READ, patched=True)           # the server's own metadata, not the client's
    with pytest.raises(ProfileConstraintViolation, match="repositoryId"):
        scope.validate_request("domainName.read", READ)


def test_a_patched_object_is_refused_for_what_the_client_changed():
    scope = scope_of(ONE_CONTACT)
    contact = {"label": "admin", "object": {"@type": "contact", "id": "C-1"}}

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.read", {**READ, "contacts": [contact, contact]}, patched=True)

    assert error.value.profile == ONE_CONTACT[0] and error.value.path == "$.contacts"


def test_the_published_composition_and_the_validators_are_those_of_the_preset_not_of_the_process():
    with_profile, without = scope_of(ADMIN_ONLY), scope_of()
    body = {"@type": "domainName", "name": "a.example",
            "contacts": [{"label": "tech", "object": {"@type": "contact", "id": "C-1"}}]}

    without.validate_request("domainName.create", body)
    with pytest.raises(ProfileConstraintViolation):
        with_profile.validate_request("domainName.create", body)
    without.validate_request("domainName.create", body)       # building another scope changed nothing of the first


def test_a_definition_the_preset_does_not_have_is_not_built_not_a_refusal_of_the_request():
    scope = scope_of()

    with pytest.raises(SchemaNotBuilt):
        scope.validate("requestContact.create", {})


def test_the_extensions_of_a_preset_are_the_ones_it_validates_for():
    rri = Definitions.load(RRI_REGISTRY).presets["rri"]
    offered = OfferedPresets.build(Definitions.load(RRI_REGISTRY), ["rri"], "rri", {}, PRESET_EXTENSIONS).offered[0]
    scope = SchemaScope(offered.extensions, offered.applicable)

    assert scope.extensions == PRESET_EXTENSIONS and rri.id == "de.denic.rpp.preset.rri"
    scope.validate("requestContact.create", {"@type": "requestContact", "id": "DENIC-1000022-GR",
                                             "uriTemplate": "https://example.com/c?d={Alabel}"})


def test_the_profile_named_is_the_first_whose_own_schema_the_request_breaks():
    # both break the request: the profile that applies first is named, with its own error, not the best of the union
    scope = scope_of(ADMIN_ONLY, AUTH_REQUIRED)
    body = {"@type": "domainName", "name": "a.example",
            "contacts": [{"label": "tech", "object": {"@type": "contact", "id": "C-1"}}]}

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.create", body)

    assert error.value.profile == ADMIN_ONLY[0] and error.value.path == "$.contacts[0].label"


def test_a_failure_of_a_later_profile_is_named_when_the_first_one_holds():
    scope = scope_of(ADMIN_ONLY, AUTH_REQUIRED)
    body = {"@type": "domainName", "name": "a.example",
            "contacts": [{"label": "admin", "object": {"@type": "contact", "id": "C-1"}}]}

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.create", body)

    assert error.value.profile == AUTH_REQUIRED[0] and "authInfo" in error.value.reason


def test_a_patched_object_names_the_profile_of_the_failure_the_client_caused_not_a_server_managed_one():
    scope = scope_of(PROV_REQUIRED, ONE_CONTACT)
    contact = {"label": "admin", "object": {"@type": "contact", "id": "C-1"}}

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.read", {**READ, "contacts": [contact, contact]}, patched=True)

    assert error.value.profile == ONE_CONTACT[0] and error.value.path == "$.contacts"


def test_the_server_managed_members_are_those_of_the_composed_definition_including_an_extension_object():
    url = EXTENSIONS["de.denic.rpp.rri"].url
    managed = profile("managed", required=[("de.denic.rpp.rri", "0.4.0")], constraints={}, defs={
        "profile.m": {"properties": {"provMetadata": {"required": ["repositoryId"]}, "uriTemplate": {"minLength": 40}}}})
    managed[1]["schema"]["rpp:constraints"] = {f"{url}#/$defs/ext.rri.requestContact.read": "#/$defs/profile.m"}
    scope = scope_of(managed, extensions=RRI_EXTENSIONS)
    stored = {"@type": "requestContact", "id": "DENIC-1000022-GR", "uriTemplate": "https://example.com/c?d={Alabel}",
              "provMetadata": {"@type": "provMetadata", "spClientId": "DENIC-1000022", "crDate": "2025-01-01T00:00:00Z"}}

    with pytest.raises(ProfileConstraintViolation) as client:
        scope.validate_request("requestContact.read", stored, patched=True)       # the template is the client's
    with pytest.raises(ProfileConstraintViolation, match="repositoryId"):
        scope.validate_request("requestContact.read", {**stored, "uriTemplate": "https://example.com/contact-form?domain={Alabel}"})   # not patched

    assert client.value.path == "$.uriTemplate" and client.value.profile == managed[0]
    scope.validate_request("requestContact.read", {**stored, "uriTemplate": "https://example.com/contact-form?domain={Alabel}"}, patched=True)


REQUIRES_RADIUS = profile("needs-mass", constraints={"domainName.update": "profile.n"}, defs={
    "profile.n": {"properties": {"contacts": {"maxItems": 1}}, "required": ["registrant"]}})


def test_a_member_is_checked_against_the_profiles_without_what_the_other_members_lack():
    scope = scope_of(REQUIRES_RADIUS)
    contact = {"label": "admin", "object": {"@type": "contact", "id": "C-1"}}

    scope.validate_request("domainName.update", {"@type": "domainName", "nameservers": []}, member="nameservers")
    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.update", {"@type": "domainName", "contacts": [contact, contact]}, member="contacts")

    assert error.value.profile == REQUIRES_RADIUS[0] and error.value.path == "$.contacts"


def test_the_removal_of_a_member_a_profile_requires_is_refused_naming_the_profile():
    scope = scope_of(REQUIRES_RADIUS)

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.refuse_removal("domainName.update", "registrant")

    assert error.value.profile == REQUIRES_RADIUS[0] and error.value.path == "$.registrant"
    scope.refuse_removal("domainName.update", "nameservers")       # no profile requires it
    scope.refuse_removal("host.update", "registrant")              # a definition no profile constrains


def test_a_native_patch_does_not_enforce_a_constraint_reported_at_the_object_root():
    # GAP (D24, .spec/spec-issues.md): a member check sees what is reported at the member or below it. A constraint such
    # as `not` that forbids a member, reported at the root of the object, is not enforced on a native patch.
    forbids = profile("forbids-radius", constraints={"domainName.update": "profile.f"},
                      defs={"profile.f": {"not": {"required": ["registrant"]}}})
    scope = scope_of(forbids)
    body = {"@type": "domainName", "registrant": {"@type": "contact", "id": "C-1"}}

    with pytest.raises(ProfileConstraintViolation):
        scope.validate_request("domainName.update", body)                      # the whole object: refused
    scope.validate_request("domainName.update", body, member="registrant")     # a native patch: not enforced


def test_only_an_unconditional_requirement_refuses_a_removal():
    conditional = profile("conditional", constraints={"domainName.update": "profile.c"}, defs={
        "profile.c": {"if": {"required": ["nameservers"]}, "then": {"required": ["registrant"]},
                      "anyOf": [{"required": ["registrant"]}, {"required": ["authInfo"]}]}})
    nested = profile("nested-required", constraints={"domainName.update": "profile.n"}, defs={
        "profile.n": {"allOf": [{"required": ["authInfo"]}]}})

    scope_of(conditional).refuse_removal("domainName.update", "registrant")       # holds only on some objects
    with pytest.raises(ProfileConstraintViolation):
        scope_of(REQUIRES_RADIUS).refuse_removal("domainName.update", "registrant")
    with pytest.raises(ProfileConstraintViolation):
        scope_of(nested).refuse_removal("domainName.update", "authInfo")


NO_AUTH_INFO = profile("no-auth-info", constraints={"domainName.create": "profile.noAuthInfo"}, defs={
    "profile.noAuthInfo": {"properties": {"authInfo": False}}})


def test_a_member_a_profile_does_not_allow_is_named_as_not_allowed():
    """A `false` schema has no keyword, so the reason is not "breaks the constraint 'None'". jsonschema gives its error
    no path (it skips the member), so the path is not asserted."""
    scope = scope_of(NO_AUTH_INFO)
    body = {"@type": "domainName", "name": "a.example",
            "authInfo": {"@type": "authInfo", "method": "password", "authdata": "secret"}}

    with pytest.raises(ProfileConstraintViolation) as error:
        scope.validate_request("domainName.create", body)

    assert error.value.profile == NO_AUTH_INFO[0]
    assert error.value.reason == f"A constraint of the profile {NO_AUTH_INFO[0]} does not allow the member"
