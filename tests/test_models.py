"""Unit tests for the psarc_library.models module."""

from psarc_library.models import PsarcLibraryServerConfig


# Psarc Library Server Configuration Models
class TestPsarcLibraryServerConfig:
    """Unit tests for the PsarcLibraryServerConfig class."""

    def test_model_dump(
        self,
        mock_psarc_library_server_config: PsarcLibraryServerConfig,
    ) -> None:
        """Test the model_dump method."""
        assert isinstance(mock_psarc_library_server_config.model_dump(), dict)


# API Response Models
