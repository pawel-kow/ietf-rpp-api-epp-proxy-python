"""The composition root: the only module that knows every other. It loads the settings once and builds the app."""
import logging

from core.session.session_pool import SessionPool
from registry_adapter.common.transport.tcp_client import TCPClient
from registry_adapter.common.transport.tls import new_tls_context
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.epp.idn_tables import IdnTables
from registry_adapter.epp.profile import epp_profile
from registry_adapter.epp.session.epp_client import EPPClient
from rpp.http.app import create_app
from settings.load_settings import load_settings

logger = logging.getLogger(__name__)


def tls_context_from_config(epp_settings):
    if not epp_settings.rpp_epp_use_tls:
        return None
    if epp_settings.rpp_epp_tls_insecure_skip_verify:
        logger.warning("rpp_epp_tls_insecure_skip_verify is on: the EPP server's certificate is not verified")
    return new_tls_context(epp_settings.rpp_epp_tls_insecure_skip_verify)


settings = load_settings()
tls_context = tls_context_from_config(settings.epp)
idn_tables = IdnTables(settings.epp.rpp_idn_lgr_tables)


def new_epp_client(username, password):
    return EPPClient(TCPClient(settings.epp.rpp_epp_host, settings.epp.rpp_epp_port, tls_context), username, password)


def new_backend(username, password):
    return EppBackend(new_epp_client(username, password), settings.epp.rpp_epp_ns_map, idn_tables)


app = create_app(SessionPool(new_backend), epp_profile(idn_tables), discovery_settings=settings.discovery)
