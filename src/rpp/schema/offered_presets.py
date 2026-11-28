from dataclasses import replace

from rpp.schema.definitions import Definitions
from rpp.schema.bundle_definitions import bundle_definitions
from rpp.schema.extension_additivity import check_additive
from rpp.schema.extension_dependencies import foreign_references
from rpp.schema.extensions import EXTENSIONS
from rpp.schema.offered_preset import OfferedPreset
from rpp.schema.preset_flattening import PresetFlattening
from rpp.schema.profile_constraints import ProfileConstraints
from rpp.schema.profile_schema_walk import undeclared
from rpp.schema.rpp_profile import RppProfile


class OfferedPresets:
    """The presets one server offers, in the order of its configuration, and the default one.

    `build` checks the choice and stops the app on a wrong one, naming what conflicts: an unknown preset or profile, a
    preset offered twice or without being a default, a cycle, one extension in two versions, an extension the proxy does
    not implement in the version stated or the backend does not hold, an extension whose definitions refer to those of another extension
    that its preset lacks, a profile that requires an extension its preset
    lacks (also one a binding adds), a profile bound that the preset already includes, a Profile Schema that declares what
    its target does not, an Extension Schema that constrains, `$defs` keys that clash, and an informational profile that no
    offered preset applies.
    """

    def __init__(self, offered: tuple[OfferedPreset, ...], default: OfferedPreset, flattening: PresetFlattening):
        self.offered = offered
        self.default = default
        self.flattening = flattening

    @classmethod
    def build(cls, definitions: Definitions, keys, default_key: str, bound: dict, held_extensions,
              informational=()) -> "OfferedPresets":
        """`informational`: the keys of the profiles the server checks itself, which the proxy does not check."""
        keys = tuple(keys)
        unknown = sorted(set(keys) - set(definitions.presets))
        if unknown:
            raise ValueError(f"backend profile: unknown preset {', '.join(unknown)}")
        if len(set(keys)) != len(keys):
            raise ValueError("backend profile: a preset is offered twice")
        if default_key not in keys:
            raise ValueError(f"backend profile: default_preset {default_key!r} is not one of the offered presets")
        stray = sorted(set(bound) - set(keys))
        if stray:
            raise ValueError(f"backend profile: bound_profiles names {', '.join(stray)}, which is not an offered preset")
        flattening = PresetFlattening(definitions)
        offered = tuple(cls._offer(definitions, flattening, definitions.presets[key], key == default_key,
                                   tuple(bound.get(key) or ()), held_extensions) for key in keys)
        for item in offered:
            cls._check_schemas(item)
        offered = cls._with_informational(definitions, offered, tuple(informational))
        return cls(offered, next(item for item in offered if item.default), flattening)

    @staticmethod
    def _offer(definitions, flattening, preset, default, bound_keys, held_extensions) -> OfferedPreset:
        label = f"The preset {preset.id}"
        extensions = []
        for reference in flattening.extensions(preset):
            implemented = EXTENSIONS.get(reference.id)
            if implemented is None:
                raise ValueError(f"{label} contains the extension {reference.id}, which the proxy does not implement")
            if implemented.version != reference.version:
                raise ValueError(f"{label} contains the extension {reference.id} in version {reference.version}, "
                                 f"the proxy implements version {implemented.version}")
            if reference.id not in held_extensions:
                raise ValueError(f"{label} contains the extension {reference.id}, which the backend does not hold")
            extensions.append(implemented)
        for extension in extensions:
            for name, owner_url in extension.owners.items():
                owner = next((other for other in extensions if other.url == owner_url), None)
                if owner is None:
                    known = next((other.id for other in EXTENSIONS.values() if other.url == owner_url), owner_url)
                    raise ValueError(f"The extension {extension.id} extends {name} of the extension {known}, "
                                     f"which the preset {preset.id} does not contain")
                if name not in owner.defs:
                    raise ValueError(f"The extension {extension.id} extends {name}, which the extension {owner.id} does not define")
            for name, owner in foreign_references(extension, EXTENSIONS.values()).items():
                if owner not in extensions:
                    raise ValueError(f"The extension {extension.id} uses {name} of the extension {owner.id}, "
                                     f"which the preset {preset.id} does not contain")
        profiles = flattening.profiles(preset)
        if len(set(bound_keys)) != len(bound_keys):
            raise ValueError(f"bound_profiles of {preset.key} names a profile twice")
        unknown = sorted(set(bound_keys) - set(definitions.profiles))
        if unknown:
            raise ValueError(f"bound_profiles of {preset.key} names an unknown profile {', '.join(unknown)}")
        bound = tuple(definitions.profiles[key] for key in bound_keys)
        twice = [profile.id for profile in bound if profile in profiles]
        if twice:
            raise ValueError(f"{label} includes the profile {twice[0]}, which the server binds to it again")
        ids = {extension.id for extension in extensions}
        for profile in (*profiles, *bound):
            for reference in flattening.required_extensions(profile):
                if reference.id not in ids:
                    raise ValueError(f"The profile {profile.id} requires the extension {reference.id}, "
                                     f"which the preset {preset.id} does not contain")
                if next(e for e in extensions if e.id == reference.id).version != reference.version:
                    raise ValueError(f"The profile {profile.id} requires the extension {reference.id} in version "
                                     f"{reference.version}, which the preset {preset.id} does not contain")
        applicable = flattening.applicable((*profiles, *bound))
        required = {profile.id: frozenset(reference.id for reference in flattening.required_extensions(profile))
                    for profile in applicable}
        return OfferedPreset(definition=preset, extensions=tuple(extensions), profiles=profiles, bound_profiles=bound,
                             applicable=applicable, default=default, required=required)

    @staticmethod
    def _with_informational(definitions: Definitions, offered: tuple[OfferedPreset, ...], keys: tuple[str, ...]):
        if len(set(keys)) != len(keys):
            raise ValueError("backend profile: informational_profiles names a profile twice")
        unknown = sorted(set(keys) - set(definitions.profiles))
        if unknown:
            raise ValueError(f"backend profile: informational_profiles names an unknown profile {', '.join(unknown)}")
        ids = frozenset(definitions.profiles[key].id for key in keys)
        stray = sorted(key for key in keys
                       if not any(profile.id == definitions.profiles[key].id for item in offered for profile in item.applicable))
        if stray:
            raise ValueError(f"backend profile: informational_profiles names {', '.join(stray)}, which no offered preset "
                             f"applies")
        return tuple(replace(item, informational=ids & {profile.id for profile in item.applicable}) for item in offered)

    @classmethod
    def _check_schemas(cls, item: OfferedPreset) -> None:
        base = bundle_definitions()
        defs = {**base, **{name: schema for extension in item.extensions for name, schema in extension.defs.items()}}
        for extension in item.extensions:
            check_additive(extension, defs)
        taken = {name: "RPP or an extension" for name in defs}
        for profile in item.applicable:
            constraints = ProfileConstraints.of(profile, item.required[profile.id])
            for name in (profile.schema or {}).get("$defs", {}):
                if name in taken:
                    raise ValueError(f"The Profile Schema of {profile.id} defines {name}, which {taken[name]} defines "
                                     f"(preset {item.id})")
                taken[name] = f"the profile {profile.id}"
            for target, (_, subs) in constraints.targets.items():
                if target not in defs:
                    raise ValueError(f"The Profile Schema of {profile.id} constrains {target}, which does not exist")
                for sub in subs:
                    bad = undeclared(profile.schema["$defs"][sub], profile.schema["$defs"], defs[target], defs)
                    if bad:
                        raise ValueError(f"The Profile Schema of {profile.id} declares {', '.join(bad)} in {sub}, "
                                         f"which {target} does not declare")

    def by_id(self, preset_id: str) -> OfferedPreset | None:
        return next((item for item in self.offered if item.id == preset_id), None)

    def extension_ids(self) -> tuple[str, ...]:
        """The extensions of the offered presets, each once, in order."""
        return tuple(dict.fromkeys(ext for item in self.offered for ext in item.extension_ids))

    def profiles(self) -> tuple[RppProfile, ...]:
        """The profiles applicable to at least one offered preset, each once."""
        return tuple(dict.fromkeys(profile for item in self.offered for profile in item.applicable))
