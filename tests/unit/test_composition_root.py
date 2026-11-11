import ssl
from types import SimpleNamespace

from config import Config, config
from eppclient.epp_backend import EppBackend
from eppclient.tcpclient import TCPClient
import run
from run import new_backend, new_epp_client, tls_context, tls_context_from_config


def test_default_factory_connects_to_the_configured_backend():
    client = new_epp_client("user", "pw")

    assert isinstance(client.client, TCPClient)
    assert client.client.server_address == config.rpp_epp_host
    assert client.client.server_port == config.rpp_epp_port


def test_default_factory_uses_the_request_credentials():
    client = new_epp_client("user", "pw")

    assert client.verify_credentials("user", "pw")


def test_the_backend_is_epp_over_the_default_client():
    backend = new_backend("user", "pw")

    assert isinstance(backend, EppBackend)
    assert backend.epp_client.client.server_address == config.rpp_epp_host
    assert backend.sponsor_id == "user"


def test_no_tls_context_when_tls_is_off():
    settings = SimpleNamespace(rpp_epp_use_tls=False, rpp_epp_tls_insecure_skip_verify=True)

    assert tls_context_from_config(settings) is None


def test_tls_context_verifies_unless_told_otherwise():
    settings = SimpleNamespace(rpp_epp_use_tls=True, rpp_epp_tls_insecure_skip_verify=False)

    assert tls_context_from_config(settings).verify_mode == ssl.CERT_REQUIRED


def test_tls_context_honours_the_opt_in():
    settings = SimpleNamespace(rpp_epp_use_tls=True, rpp_epp_tls_insecure_skip_verify=True)

    assert tls_context_from_config(settings).verify_mode == ssl.CERT_NONE


def test_default_factory_passes_the_tls_context_to_the_transport():
    client = new_epp_client("user", "pw")

    assert client.client.tls_context is tls_context


def test_tls_is_on_and_verified_when_the_config_is_silent(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("rpp_epp_host: example.org\n")
    monkeypatch.setenv("RPP_CONFIG_FILE", str(config_file))

    settings = Config()

    assert settings.rpp_epp_use_tls is True
    assert settings.rpp_epp_tls_insecure_skip_verify is False


def test_the_composition_root_gives_discovery_the_configuration():
    assert config.rpp_base_url
    assert config.rpp_tlds
    assert config.rpp_environment_name
    assert config.rpp_environment_status


def test_the_composition_root_hands_the_configuration_to_the_app():
    assert run.app.app.config["RPP_DISCOVERY_SETTINGS"] is config


def test_the_app_maps_lgr_to_the_configured_idn_tables():
    tables = run.app.app.config["RPP_IDN_TABLES"]

    for lgr, table in (config.rpp_idn_lgr_tables or {}).items():
        assert tables.table(lgr) == table
        assert tables.lgr(table) == lgr
