"""The composition root: the only module that knows every other. It loads the settings once and builds the app for the
backend the settings name (`rpp_backend`). `compose` builds an app from any settings, so the integration tests can
build one per test environment."""
import logging
from collections.abc import Callable
from dataclasses import dataclass

from core.capabilities.backend_profile import BackendProfile
from core.session.session_pool import SessionPool
from registry_adapter.common.transport.tcp_client import LENGTH_OF_PAYLOAD, TCPClient
from registry_adapter.common.transport.tls import new_tls_context
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.rri.gateways.rri_backend import RriBackend
from registry_adapter.rri.session.rri_client import RriClient
from rpp.http.app import create_app
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
    app: object


def compose(settings: Settings) -> Composition:
    """Builds the app for the backend `settings` names (`rpp_backend`)."""
    tls_context = tls_context_from_config(settings.epp)
    idn_tables = IdnTables(settings.epp.rpp_idn_lgr_tables)
    # The generic profile of the protocol, the server's own over it, and the LGRs of the config.
    profile = BackendProfile.from_layers(*settings.profile_layers, {"lgrs": list(settings.lgrs)})

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

    def new_rri_backend(username, password):
        return RriBackend(new_rri_client(username, password), profile, settings.rri.rpp_rri_lgr)

    # The backend factory of each protocol `rpp_backend` can name.
    backends = {
        "epp": new_epp_backend,
        "rri": new_rri_backend,
    }
    new_backend = backends[settings.backend]
    sessions = SessionPool(new_backend)
    app = create_app(sessions, profile, discovery_settings=settings.discovery)
    return Composition(settings=settings, profile=profile, tls_context=tls_context, idn_tables=idn_tables,
                       new_epp_client=new_epp_client, new_backend=new_backend, sessions=sessions, app=app)


# The app of the settings loaded once (RPP_CONFIG_FILE, else config.yaml), which uvicorn serves as `main:app`.
default = compose(load_settings())
settings = default.settings
tls_context = default.tls_context
idn_tables = default.idn_tables
profile = default.profile
new_epp_client = default.new_epp_client
new_backend = default.new_backend
app = default.app
