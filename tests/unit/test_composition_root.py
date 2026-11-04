from config import config
from eppclient.tcpclient import TCPClient
from run import new_epp_client


def test_default_factory_connects_to_the_configured_backend():
    client = new_epp_client("user", "pw")

    assert isinstance(client.client, TCPClient)
    assert client.client.server_address == config.rpp_epp_host
    assert client.client.server_port == config.rpp_epp_port


def test_default_factory_uses_the_request_credentials():
    client = new_epp_client("user", "pw")

    assert client.verify_credentials("user", "pw")
