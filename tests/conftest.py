"""Pytest fixtures for the application's unit tests."""

import pytest

from psarc_library.models import PsarcLibraryServerConfig


# Psarc Library Server Configuration Models
@pytest.fixture
def mock_psarc_library_server_config() -> PsarcLibraryServerConfig:
    """Provide a mock PsarcLibraryServerConfig instance."""
    return PsarcLibraryServerConfig()
