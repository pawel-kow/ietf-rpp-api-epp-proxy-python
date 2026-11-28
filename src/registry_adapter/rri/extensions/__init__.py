"""The extensions the RRI backend holds: the module of its part of each, by extension id (the `EXTENSION_ID` of the
extension). Plain strings, so that importing this imports no extension, and a deployment loads only the parts of the
extensions it configures. An extension of `rpp_extensions` that is not here stops the app at start."""

PARTS = {
    "de.denic.rpp.rri": "registry_adapter.rri.extensions.rri",
    "io.github.pawel-kow.rpp.messages": "registry_adapter.rri.extensions.messages",
    "io.github.pawel-kow.rpp.domain-lock": "registry_adapter.rri.extensions.domain_lock",
    "io.github.pawel-kow.rpp.registry-changes": "registry_adapter.rri.extensions.registry_changes",
}
