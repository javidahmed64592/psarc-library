"""Unit tests for the psarc_library.server module."""

from __future__ import annotations

from collections.abc import Generator
from importlib.metadata import PackageMetadata
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Security
from fastapi.routing import APIRoute
from fastapi.security import APIKeyHeader

from psarc_library.models import PsarcLibraryServerConfig
from psarc_library.server import PsarcLibraryServer


@pytest.fixture(autouse=True)
def mock_package_metadata() -> Generator[MagicMock]:
    """Mock importlib.metadata.metadata to return a mock PackageMetadata."""
    with patch("python_template_server.template_server.metadata") as mock_metadata:
        mock_pkg_metadata = MagicMock(spec=PackageMetadata)
        metadata_dict = {
            "Name": "psarc-library",
            "Version": "0.1.0",
            "Summary": "A web interface for parsing and exploring Rocksmith psarc files.",
        }
        mock_pkg_metadata.__getitem__.side_effect = lambda key: metadata_dict[key]
        mock_metadata.return_value = mock_pkg_metadata
        yield mock_metadata


@pytest.fixture
def mock_server(
    mock_psarc_library_server_config: PsarcLibraryServerConfig,
) -> Generator[PsarcLibraryServer]:
    """Provide a PsarcLibraryServer instance for testing."""

    async def fake_verify_api_key(
        api_key: str | None = Security(APIKeyHeader(name="X-API-Key", auto_error=False)),
    ) -> None:
        """Fake verify API key that accepts the security header and always succeeds in tests."""
        return

    with (
        patch("psarc_library.server.PsarcLibraryServerConfig.save_to_file"),
        patch.object(PsarcLibraryServer, "_verify_api_key", new=fake_verify_api_key),
    ):
        server = PsarcLibraryServer(config=mock_psarc_library_server_config)
        yield server


class TestPsarcLibraryServer:
    """Unit tests for the PsarcLibraryServer class."""

    def test_init(self, mock_server: PsarcLibraryServer) -> None:
        """Test PsarcLibraryServer initialization."""
        assert isinstance(mock_server.config, PsarcLibraryServerConfig)

    def test_validate_config(
        self, mock_server: PsarcLibraryServer, mock_psarc_library_server_config: PsarcLibraryServerConfig
    ) -> None:
        """Test configuration validation."""
        config_dict = mock_psarc_library_server_config.model_dump()
        validated_config = mock_server.validate_config(config_dict)
        assert validated_config == mock_psarc_library_server_config

    def test_validate_config_invalid_returns_default(self, mock_server: PsarcLibraryServer) -> None:
        """Test invalid configuration returns default configuration."""
        invalid_config = {"model": None}
        validated_config = mock_server.validate_config(invalid_config)
        assert isinstance(validated_config, PsarcLibraryServerConfig)


class TestPsarcLibraryServerRoutes:
    """Integration tests for the mock routes in PsarcLibraryServer."""

    def test_setup_routes(self, mock_server: PsarcLibraryServer) -> None:
        """Test that routes are set up correctly."""
        api_routes = [route for route in mock_server.app.routes if isinstance(route, APIRoute)]
        routes = [route.path for route in api_routes]
        expected_endpoints = [
            "/health",
            "/login",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in routes
