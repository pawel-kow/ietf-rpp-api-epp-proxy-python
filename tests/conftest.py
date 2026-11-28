"""Chooses the app under test before any test module composes it (docs/agents/testing.project.md#test-environments)."""
import os

import pytest

from tests.helper.test_environment import config_file, selected_name

os.environ.setdefault("RPP_CONFIG_FILE", config_file(selected_name()))


@pytest.fixture(autouse=True)
def restore_backend_catalogues():
    """A test-only extension adds its entry to the catalogue of a backend (`register_definitions`): none outlives its test."""
    from registry_adapter.rri.extensions import PARTS as rri
    from registry_adapter.sqlite.extensions import PARTS as sqlite
    saved = dict(rri), dict(sqlite)
    yield
    for parts, before in zip((rri, sqlite), saved):
        parts.clear()
        parts.update(before)
