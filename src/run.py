from app import create_app
from config import config
from controller.epp_session_authenticator import EppSessionAuthenticator
from eppclient.eppclient import EPPClient
from eppclient.tcpclient import TCPClient


def new_epp_client(username, password):
    return EPPClient(TCPClient(config.rpp_epp_host, config.rpp_epp_port), username, password)


app = create_app(EppSessionAuthenticator(new_epp_client))
