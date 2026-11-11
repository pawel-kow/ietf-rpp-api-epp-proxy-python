import logging

from rpp.http.app import create_app
from config import config
from core.session.session_pool import SessionPool
from registry_adapter.epp.gateways.epp_backend import EppBackend
from registry_adapter.epp.profile import EPP_PROFILE
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.common.transport.tcp_client import TCPClient
from registry_adapter.common.transport.tls import new_tls_context
from rpp.mapping.domain.idn_tables import IdnTables


logger = logging.getLogger(__name__)


def tls_context_from_config(settings):
    if not settings.rpp_epp_use_tls:
        return None
    if settings.rpp_epp_tls_insecure_skip_verify:
        logger.warning("rpp_epp_tls_insecure_skip_verify is on: the EPP server's certificate is not verified")
    return new_tls_context(settings.rpp_epp_tls_insecure_skip_verify)


tls_context = tls_context_from_config(config)


def new_epp_client(username, password):
    return EPPClient(TCPClient(config.rpp_epp_host, config.rpp_epp_port, tls_context), username, password)


def new_backend(username, password):
    return EppBackend(new_epp_client(username, password), config.rpp_epp_ns_map)


app = create_app(
    SessionPool(new_backend), EPP_PROFILE, discovery_settings=config,
    idn_tables=IdnTables(config.rpp_idn_lgr_tables),
)
