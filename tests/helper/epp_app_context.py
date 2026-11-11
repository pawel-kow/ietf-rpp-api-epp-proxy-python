import pytest
from flask import Flask

from registry_adapter.epp.profile import EPP_PROFILE


@pytest.fixture
def epp_app_context():
    """An application with the EPP backend, from which `map_request` names the backend as the handlers do."""
    app = Flask(__name__)
    app.config["RPP_BACKEND_PROFILE"] = EPP_PROFILE
    with app.app_context():
        yield app
