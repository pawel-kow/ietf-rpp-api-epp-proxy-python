from registration.extension_registry import ExtensionRegistry

# The leaves that are lists the extensions add to, not replace (an extension brings its presets).
ADDITIVE = ("objects", "extensions", "presets")


def with_extensions(layers, registry: ExtensionRegistry) -> list[dict]:
    """The layers of a backend profile with those of the registered extensions: the leaves they add are a layer of
    their own after the generic profile, and the `objects` and `extensions` they list are added to those of the generic
    profile (the first layer), which would otherwise be replaced."""
    layers = list(layers)
    if not len(registry) or not layers:
        return layers
    added = {key: [] for key in ADDITIVE}
    extra: dict = {}
    for extension in registry:
        for key, value in extension.profile_layer.items():
            if key in ADDITIVE:
                added[key].extend(value)
            else:
                extra[key] = value
    first = dict(layers[0])
    for key in ADDITIVE:
        if not added[key]:
            continue
        first[key] = [*first.get(key, ()), *(item for item in added[key] if item not in first.get(key, ()))]
    return [first, extra, *layers[1:]]
