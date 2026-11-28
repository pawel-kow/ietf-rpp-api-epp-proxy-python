from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True, kw_only=True)
class RegisteredExtension:
    """Everything one extension adds to the pipeline, as its `register` states it. The registry holds it as data: it
    imports nothing of the proxy, names no backend (a backend lists the extensions it holds, `registry_adapter.<backend>.extensions.PARTS`), and the code that reads it (the app, a backend) knows what each part is.

    - `id`: the extension id of its RPP schema.
    - `schema`: the parsed RPP extension schema (guidelines §8).
    - `data_objects`: the top-level data elements of each object it defines, with their Visibility
      (`{object: {element: visibility}}`), which `includeElements` reads.
    - `objects`: the identifiers of the objects it defines.
    - `processes`: the identifiers of the Process Objects it adds, by the data object that owns them
      (`{"domainName": ("authInfoProcess",)}`), whose paths are `<plural of the object>/<id>/processes/<plural>`: a preset
      without the extension refuses them as it refuses its objects.
    - `openapi`: a function that builds its OpenAPI fragment (`{"paths": ..., "components": {"schemas": ...}}`) from the
      OpenAPI document of the drafts (and of the extensions before it), which it reads and does not change: an object that
      shares the uniform interface of a base object has the paths of that object. Every operationId of it is a fully
      qualified function name in `handlers`, or names the module of its handler (`x-openapi-router-controller`). None for an
      extension without paths.
    - `handlers`: the package of its handler modules (None for an extension without paths).
    - `profile_layer`: the leaves it adds to the backend profile, with `objects`, `extensions` and `presets` to add to those the
      generic profile lists; `profile_leaves` the type of each leaf of it that the profile does not have.
    - `presets`: the presets it brings (`{key: definition}`, as a preset file of `rpp/schema/schemas/presets` states it).
    - `profiles`: the profiles it brings (`{key: definition}`, as a profile file states it, with its Profile Schema, if
      any, as `schema`).
    """
    id: str
    schema: dict
    data_objects: dict[str, dict[str, str]]
    objects: tuple[str, ...]
    processes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    openapi: Callable[[dict], dict] | None = None
    handlers: str | None = None
    profile_layer: dict[str, Any] = field(default_factory=dict)
    profile_leaves: dict[str, type] = field(default_factory=dict)
    presets: dict[str, dict] = field(default_factory=dict)
    profiles: dict[str, dict] = field(default_factory=dict)
