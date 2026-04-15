"""Unit tests for the psarc_library.main module."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from psarc_library.main import run
from psarc_library.models import PsarcLibraryServerConfig


@pytest.fixture
def mock_psarc_library_server_class(mock_psarc_library_server_config: PsarcLibraryServerConfig) -> Generator[MagicMock]:
    """Mock PsarcLibraryServer class."""
    with patch("psarc_library.main.PsarcLibraryServer") as mock_server:
        mock_server.load_config.return_value = mock_psarc_library_server_config
        yield mock_server


class TestRun:
    """Unit tests for the run function."""

    def test_run(self, mock_psarc_library_server_class: MagicMock) -> None:
        """Test successful server run."""
        run()

        mock_psarc_library_server_class.return_value.run.assert_called_once()
