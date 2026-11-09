from app import create_app
from config import config
from controller.epp_session_authenticator import EppSessionAuthenticator
from eppclient.eppclient import EPPClient
from eppclient.tcpclient import TCPClient
from eppclient.tls import new_tls_context
from rpp_to_model_mapper import IdnTables


def tls_context_from_config(settings):
    if not settings.rpp_epp_use_tls:
        return None
    return new_tls_context(settings.rpp_epp_tls_insecure_skip_verify)


tls_context = tls_context_from_config(config)


def new_epp_client(username, password):
    return EPPClient(TCPClient(config.rpp_epp_host, config.rpp_epp_port, tls_context), username, password)


app = create_app(EppSessionAuthenticator(new_epp_client), config, IdnTables(config.rpp_idn_lgr_tables))
