"""PSARC Library server implementation using the TemplateServer base class."""

import logging
from typing import Any

from python_template_server.template_server import TemplateServer

from psarc_library.models import PsarcLibraryServerConfig

logger = logging.getLogger(__name__)


class PsarcLibraryServer(TemplateServer):
    """PSARC Library server implementation."""

    def __init__(self, config: PsarcLibraryServerConfig | None = None) -> None:
        """Initialize the PsarcLibraryServer.

        :param PsarcLibraryServerConfig | None config: Optional pre-loaded configuration
        """
        self.config: PsarcLibraryServerConfig
        super().__init__(
            package_name="psarc-library",
            config=config,
        )

    def validate_config(self, config_data: dict[str, Any]) -> PsarcLibraryServerConfig:
        """Validate configuration data against the PsarcLibraryServerConfig model.

        :param dict config_data: The configuration data to validate
        :return PsarcLibraryServerConfig: The validated configuration model
        :raise ValidationError: If the configuration data is invalid
        """
        return PsarcLibraryServerConfig.model_validate(config_data)  # type: ignore[no-any-return]

    def setup_routes(self) -> None:
        """Add custom API routes."""
        pass
