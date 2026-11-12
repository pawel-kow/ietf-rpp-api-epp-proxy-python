"""Chooses the app under test before any test module composes it (docs/agents/testing.project.md#test-environments)."""
import os

from tests.helper.test_environment import config_file, selected_name

os.environ.setdefault("RPP_CONFIG_FILE", config_file(selected_name()))
