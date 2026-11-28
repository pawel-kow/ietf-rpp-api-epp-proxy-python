from registration.registered_extension import RegisteredExtension


class ExtensionRegistry:
    """The extensions one app is built with, in the order of the configuration. An extension is registered by its own
    `register(registry)`, once; a second extension of the same id is a configuration error."""

    def __init__(self):
        self._extensions: dict[str, RegisteredExtension] = {}

    def add(self, extension: RegisteredExtension) -> None:
        if extension.id in self._extensions:
            raise ValueError(f"The extension {extension.id} is registered twice")
        self._extensions[extension.id] = extension

    def __iter__(self):
        return iter(self._extensions.values())

    def __len__(self) -> int:
        return len(self._extensions)

    def get(self, extension_id: str) -> RegisteredExtension:
        return self._extensions[extension_id]

    def ids(self) -> tuple[str, ...]:
        return tuple(self._extensions)

    def handler_packages(self) -> tuple[str, ...]:
        return tuple(extension.handlers for extension in self if extension.handlers)

    def backend_parts(self, backend: str) -> dict[str, str]:
        """The module of each registered extension in the backend, by extension id."""
        return {extension.id: extension.backend_parts[backend] for extension in self
                if backend in extension.backend_parts}

    def needing_gateways(self) -> frozenset[str]:
        """The ids of the extensions that have objects, processes or handlers: their part of a backend must have gateways."""
        return frozenset(extension.id for extension in self if extension.objects or extension.processes or extension.handlers)

    def profile_leaves(self) -> dict[str, type]:
        return {path: kind for extension in self for path, kind in extension.profile_leaves.items()}
