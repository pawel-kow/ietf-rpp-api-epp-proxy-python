"""The composition root: the only module that knows every other. It loads the settings once and builds the app for the
backend the settings name (`rpp_backend`). `compose` builds an app from any settings, so the integration tests can
build one per test environment."""
import logging
from collections.abc import Callable
from dataclasses import dataclass

from core.capabilities.backend_profile import BackendProfile
from core.session.session_pool import SessionPool
from api_docs.docs_app import DocsApp
from registry_adapter.common.transport.tcp_client import LENGTH_OF_PAYLOAD, TCPClient
from registry_adapter.common.transport.tls import new_tls_context
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.rri.extension_part import load_extension_parts as load_rri_parts
from registry_adapter.rri.gateways.rri_backend import RriBackend
from registry_adapter.rri.session.rri_client import RriClient
from registry_adapter.sqlite.client_directory import ClientDirectory
from registry_adapter.sqlite.extension_part import load_extension_parts
from registry_adapter.sqlite.common_part import COMMON_PART
from registry_adapter.sqlite.sqlite_backend import SqliteBackend
from registry_adapter.sqlite.sqlite_database import SqliteDatabase
from registration import ExtensionRegistry
from registry_setup import backend_parts, backend_profile, load_registry
from rpp.http.app import create_app
from rpp.http.rpp_app import RppApp
from settings.load_settings import load_settings
from settings.settings import Settings

logger = logging.getLogger(__name__)


def tls_context_from_config(epp_settings):
    if not epp_settings.rpp_epp_use_tls:
        return None
    if epp_settings.rpp_epp_tls_insecure_skip_verify:
        logger.warning("rpp_epp_tls_insecure_skip_verify is on: the EPP server's certificate is not verified")
    return new_tls_context(epp_settings.rpp_epp_tls_insecure_skip_verify)


def rri_tls_context(rri_settings):
    if not rri_settings.rpp_rri_use_tls:
        return None
    if rri_settings.rpp_rri_tls_insecure_skip_verify:
        logger.warning("rpp_rri_tls_insecure_skip_verify is on: the RRI server's certificate is not verified")
    return new_tls_context(rri_settings.rpp_rri_tls_insecure_skip_verify)


@dataclass(frozen=True)
class Composition:
    """The app built from one settings, with the parts the tests look at."""
    settings: Settings
    profile: BackendProfile
    tls_context: object
    idn_tables: IdnTables
    new_epp_client: Callable
    new_backend: Callable
    sessions: SessionPool
    app: object  # what is served: the documents and the UI (api_docs) in front of rpp_app (#205)
    rpp_app: RppApp
    registry: ExtensionRegistry


def compose(settings: Settings) -> Composition:
    """Builds the app for the backend `settings` names (`rpp_backend`)."""
    tls_context = tls_context_from_config(settings.epp)
    idn_tables = IdnTables(settings.epp.rpp_idn_lgr_tables)
    # The generic profile of the protocol, the server's own over it, and the LGRs of the config.
    registry = load_registry(settings)
    profile = backend_profile(settings, registry)

    def new_epp_client(username, password):
        return EPPClient(TCPClient(settings.epp.rpp_epp_host, settings.epp.rpp_epp_port, tls_context), username,
                         password)

    def new_epp_backend(username, password):
        return EppBackend(new_epp_client(username, password), settings.epp.rpp_epp_ns_map, profile, idn_tables)

    rri_tls = rri_tls_context(settings.rri) if settings.backend == "rri" else None

    def new_rri_client(username, password):
        rri = settings.rri
        transport = TCPClient(rri.rpp_rri_host, rri.rpp_rri_port, rri_tls, framing=LENGTH_OF_PAYLOAD)
        return RriClient(transport, username, password)

    def rri_backend_factory():
        """The RRI parts of the registered extensions (loaded now), and the factory of a client's session."""
        parts = load_rri_parts(backend_parts("rri", registry), registry.needing_gateways())

        def new_rri_backend(username, password):
            return RriBackend(new_rri_client(username, password), profile, settings.rri.rpp_rri_lgr, parts)
        return new_rri_backend

    def sqlite_backend_factory():
        """The database of the demo backend (its tables are created now), and the factory of a client's session."""
        parts = load_extension_parts(backend_parts("sqlite", registry))
        database = SqliteDatabase(settings.sqlite.rpp_sqlite_url, [COMMON_PART, *(part.part for part in parts)])
        clients = ClientDirectory(settings.sqlite.rpp_sqlite_clients)

        def new_sqlite_backend(username, password):
            return SqliteBackend(database, clients, profile, parts, username, password)
        return new_sqlite_backend

    # The backend factory of each protocol `rpp_backend` can name.
    backends = {
        "epp": lambda: new_epp_backend,
        "rri": rri_backend_factory,
        "sqlite": sqlite_backend_factory,
    }
    new_backend = backends[settings.backend]()
    sessions = SessionPool(new_backend)
    rpp_app = create_app(sessions, profile, discovery_settings=settings.discovery,
                         signalling=settings.preset_signalling, registry=registry, openapi_settings=settings.openapi)
    return Composition(settings=settings, profile=profile, tls_context=tls_context, idn_tables=idn_tables,
                       new_epp_client=new_epp_client, new_backend=new_backend, sessions=sessions,
                       app=DocsApp(rpp_app, rpp_app.openapi_documents()), rpp_app=rpp_app, registry=registry)


# The app of the settings loaded once (RPP_CONFIG_FILE, else config/environments/epp-docker.yaml), which uvicorn serves as `main:app`.
default = compose(load_settings())
settings = default.settings
tls_context = default.tls_context
idn_tables = default.idn_tables
profile = default.profile
new_epp_client = default.new_epp_client
new_backend = default.new_backend
app = default.app
rpp_app = default.rpp_app
