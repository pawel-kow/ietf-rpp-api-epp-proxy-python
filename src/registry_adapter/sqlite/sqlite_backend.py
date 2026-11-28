from core.capabilities.backend_profile import BackendProfile
from registry_adapter.sqlite.client_directory import ClientDirectory
from registry_adapter.sqlite.extension_part import ExtensionPart
from registry_adapter.sqlite.gateways.sqlite_message_gateway import SqliteMessageGateway
from registry_adapter.sqlite.gateways.unsupported_gateway import UnsupportedGateway
from registry_adapter.sqlite.message_store import MessageStore
from registry_adapter.sqlite.sqlite_context import SqliteContext
from registry_adapter.sqlite.sqlite_database import SqliteDatabase


class SqliteBackend:
    """The demo registry over a database (a `RegistryBackend`), for one client. The login is the client: the sponsor of what
    it creates. The data objects of the drafts are not held, and the objects of the configured extensions are reached by
    their extension id (`extension`)."""

    def __init__(self, database: SqliteDatabase, clients: ClientDirectory, profile: BackendProfile,
                 extension_parts: list[ExtensionPart], username: str, password: str):
        self.profile = profile
        self._clients = clients
        self._username = username
        # Whether the login was right is known at `connect`, which checks it; the password is not kept.
        self._connected = clients.verify(username, password)
        hooks: dict[str, dict] = {}
        for part in extension_parts:
            for target, hook in part.hooks.items():
                hooks.setdefault(target, {})[part.extension_id] = hook
        context = SqliteContext(database=database, sponsor_id=username, messages=MessageStore(), hooks=hooks)
        self.domains = UnsupportedGateway("domain name")
        self.contacts = UnsupportedGateway("contact")
        self.hosts = UnsupportedGateway("host")
        self.messages = SqliteMessageGateway(context)
        self._extensions = {part.extension_id: part.gateways(context) for part in extension_parts if part.gateways is not None}

    @property
    def sponsor_id(self) -> str:
        return self._username

    @property
    def connected(self) -> bool:
        return self._connected

    def extension(self, extension_id: str):
        return self._extensions[extension_id]

    def connect(self) -> None:
        """The login was checked when the session was made."""

    def disconnect(self) -> None:
        """There is no connection to close."""

    def verify_credentials(self, user: str, password: str) -> bool:
        return user == self._username and self._clients.verify(user, password)
