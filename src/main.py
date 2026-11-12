"""The composition root: the only module that knows every other. It loads the settings once and builds the app for the
backend the settings name (`rpp_backend`)."""
import logging

from core.session.session_pool import SessionPool
from registry_adapter.common.transport.tcp_client import LENGTH_OF_PAYLOAD, TCPClient
from registry_adapter.common.transport.tls import new_tls_context
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.profile import epp_profile
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.rri.gateways.rri_backend import RriBackend
from registry_adapter.rri.profile import rri_profile
from registry_adapter.rri.session.rri_client import RriClient
from rpp.http.app import create_app
from settings.load_settings import load_settings

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


settings = load_settings()
tls_context = tls_context_from_config(settings.epp)
idn_tables = IdnTables(settings.epp.rpp_idn_lgr_tables)


def new_epp_client(username, password):
    return EPPClient(TCPClient(settings.epp.rpp_epp_host, settings.epp.rpp_epp_port, tls_context), username, password)


def new_epp_backend(username, password):
    return EppBackend(new_epp_client(username, password), settings.epp.rpp_epp_ns_map, idn_tables)


rri_tls = rri_tls_context(settings.rri) if settings.backend == "rri" else None


def new_rri_client(username, password):
    rri = settings.rri
    transport = TCPClient(rri.rpp_rri_host, rri.rpp_rri_port, rri_tls, framing=LENGTH_OF_PAYLOAD)
    return RriClient(transport, username, password)


def new_rri_backend(username, password):
    return RriBackend(new_rri_client(username, password), settings.rri.rpp_rri_lgr)


# The backend factory and the profile of each protocol `rpp_backend` can name.
BACKENDS = {
    "epp": (new_epp_backend, lambda: epp_profile(idn_tables)),
    "rri": (new_rri_backend, lambda: rri_profile(settings.rri.rpp_rri_lgr)),
}

new_backend, _profile_of = BACKENDS[settings.backend]

app = create_app(SessionPool(new_backend), _profile_of(), discovery_settings=settings.discovery)
