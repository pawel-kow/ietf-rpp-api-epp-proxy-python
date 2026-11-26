import re

import jsonschema
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.effective_schema import UNEVALUATED, compose, required_of
from rpp.schema.extensions import EXTENSIONS, own_definitions
from rpp.schema.profile_constraint_violation import ProfileConstraintViolation
from rpp.schema.profile_constraints import ProfileConstraints
from rpp.schema.profile_schema_walk import expand

_UNEXPECTED = re.compile(r"\((.*) (?:was|were) unexpected\)")


def _path(error) -> str:
    return "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)


def _build(definitions: dict, names) -> dict[str, Draft202012Validator]:
    """The validator of each definition `names` stand for; an extension's own object (`requestContact.create`) is
    validated by the name a base object's would have."""
    own = own_definitions()
    validators = {}
    for name in names:
        target = name if name in definitions else own.get(name)
        if target in definitions:
            # the formats the definitions state are checked (#233), as Connexion's validator did before #201
            validators[name] = Draft202012Validator({"$ref": f"#/$defs/{target}", "$defs": definitions},
                                                    format_checker=Draft202012Validator.FORMAT_CHECKER)
    return validators


class SchemaScope:
    """What a request under one preset validates with (D18: per preset, not process-global): the validators of every
    definition for the extensions of the preset, without its applicable profiles and with them, and one per profile, to name
    the one a failure belongs to. They are built when the app is built and a request only looks them up.

    `validate` is the validation of the preset without profiles: a failure is a request that does not conform to the preset
    (400). `validate_request` is the two steps of json §Profiles and Validation: a failure of the second step only is a
    `ProfileConstraintViolation`. A scope without an app (the mappers' own tests) is `SchemaScope.of`.
    """

    def __init__(self, extensions, profiles=(), required=None):
        self.extensions = tuple(extension.id for extension in extensions)
        self._profiles = tuple(profile for profile in profiles if profile.schema is not None)
        names = {*bundle_definitions(), *own_definitions(self.extensions)}
        self._plain = _build(compose(extensions, (), True), names)
        # the composition without injection, in which a definition keeps its key: where the members of a definition are read
        self._composed = compose(extensions, self._profiles, False, required)
        if not self._profiles:
            self._full = self._plain
        else:
            self._full = _build(compose(extensions, self._profiles, True, required), names)
        # one validator set per profile, to name the profile a failure belongs to
        self._single = {profile.id: _build(compose(extensions, (profile,), True, required), names)
                        for profile in self._profiles} if len(self._profiles) > 1 else {}
        self._constraints = {profile.id: ProfileConstraints.of(profile, required_of(profile, required))
                             for profile in self._profiles}
        self.profile_ids = tuple(profile.id for profile in self._profiles)

    _of: dict[tuple[str, ...], "SchemaScope"] = {}

    @classmethod
    def of(cls, extension_ids=()) -> "SchemaScope":
        """The scope of some extensions and no profile, built on first use: for what maps without an app. The app never
        does that, it passes the scope of the preset (a defect where it does not: `SchemaNotBuilt`)."""
        key = tuple(extension_ids)
        if key not in cls._of:
            scope = cls([EXTENSIONS[ext] for ext in key])
            everything = tuple(EXTENSIONS)
            # what maps without an app finds the object of an extension the scope was not given in the scope of all of them
            scope._fallback = cls.of(everything) if key != everything else None
            cls._of[key] = scope
        return cls._of[key]

    _fallback: "SchemaScope | None" = None

    def _lookup(self, validators: dict, name: str):
        validator = validators.get(name)
        if validator is None and self._fallback is not None:
            validator = self._fallback._plain.get(name)
        if validator is None:
            raise SchemaNotBuilt(f"No schema {name} was built for the extensions {', '.join(self.extensions) or '(none)'}")
        return validator

    def has(self, name: str) -> bool:
        """Whether the scope built a validator of the definition (without the fallback of a scope without an app)."""
        return name in self._plain

    def validate(self, name: str, data) -> None:
        """Validates `data` against a definition of the preset without profiles. A member no schema declares is refused as an
        undeclared property (json §4.9.1), the same `ValueError` the dataclasses' check raises."""
        try:
            self._lookup(self._plain, name).validate(data)
        except jsonschema.ValidationError as error:
            if error.validator == UNEVALUATED:
                names = _UNEXPECTED.search(error.message)
                raise ValueError(f"Undeclared property: {names.group(1) if names else error.message}") from None
            raise

    def validate_request(self, name: str, data, patched: bool = False, member: str | None = None) -> None:
        """The two steps. `patched`: `data` is an object a client's patch or replacement results in, whose read-only members
        the server manages: a failure that concerns one of them is not the client's. `member`: only a failure at this member
        of `data` counts (a native patch checks the value of one member, and not what the others of the object lack)."""
        self.validate(name, data)
        if self._full is self._plain:
            return
        if not self._errors(self._full, name, data, patched, member):
            return
        for profile in self._profiles:          # in the order they apply, the bases first
            validators = self._single[profile.id] if self._single else self._full
            errors = self._errors(validators, name, data, patched, member)
            if errors:
                error = best_match(errors)
                raise ProfileConstraintViolation(profile.id, _path(error), _reason(error, profile.id))
        error = best_match(self._errors(self._full, name, data, patched, member))
        raise ProfileConstraintViolation(None, _path(error), _reason(error, None))

    def _errors(self, validators: dict, name: str, data, patched: bool, member: str | None) -> list:
        errors = list(self._lookup(validators, name).iter_errors(data))
        if patched:
            server_managed = self._read_only(name)
            errors = [error for error in errors if not (error.absolute_path and error.absolute_path[0] in server_managed)]
        if member is not None:
            errors = [error for error in errors if error.absolute_path and error.absolute_path[0] == member]
        return errors

    def refuse_removal(self, name: str, member: str) -> None:
        """A removal of `member` of an object of the definition `name` that an applicable profile requires (it lists the
        member in `required`) is a broken constraint of that profile."""
        for profile in self._profiles:
            targets = self._constraints[profile.id].targets.get(name)
            if targets is None:
                continue
            defs = profile.schema["$defs"]
            if any(member in _unconditional_required(defs[sub], defs) for sub in targets[1]):
                raise ProfileConstraintViolation(
                    profile.id, f"$.{member}", f"A constraint of the profile {profile.id} requires '{member}'")

    def _read_only(self, name: str) -> frozenset:
        """The top-level members of the definition that the server manages (`readOnly`), whether RPP or an extension defines
        the definition or the member."""
        own = own_definitions(self.extensions)
        target = name if name in self._composed else own.get(name)
        if target not in self._composed:
            return frozenset()
        return frozenset(member for schema in expand([self._composed[target]], self._composed)
                         for member, sub in schema.get("properties", {}).items()
                         if isinstance(sub, dict) and sub.get("readOnly"))


def _unconditional_required(schema, defs: dict, seen=frozenset()) -> set:
    """The members that `schema` requires whatever the instance is: its `required` and those of its `allOf` branches and
    references, not those of `if`, `then`, `else`, `anyOf`, `oneOf` or `not`, which hold only on some instances."""
    if not isinstance(schema, dict) or id(schema) in seen:
        return set()
    seen = seen | {id(schema)}
    found = set(schema.get("required", ()))
    if isinstance(schema.get("$ref"), str) and schema["$ref"].startswith("#/$defs/"):
        found |= _unconditional_required(defs.get(schema["$ref"].rsplit("/", 1)[-1]), defs, seen)
    for branch in schema.get("allOf") or ():
        found |= _unconditional_required(branch, defs, seen)
    return found


def _reason(error, profile) -> str:
    of = f" of the profile {profile}" if profile else " of a profile"
    if error.validator == "required":
        return f"{error.message}, which a constraint{of} requires"
    if error.validator is None:  # a `false` schema, which has no keyword: the profile does not allow the member
        return f"A constraint{of} does not allow the member"
    return f"The value breaks the constraint '{error.validator}'{of}"


class SchemaNotBuilt(LookupError):
    """A request asked for a validator that no preset of the app has: a defect, not a refusal of the request."""
