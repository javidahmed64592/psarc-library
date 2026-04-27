"""PSARC Library server implementation using the TemplateServer base class."""

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Query, Request
from python_template_server.models import ResponseCode
from python_template_server.template_server import TemplateServer

from psarc_library.constants import GAME_DIR_ENV_VAR
from psarc_library.database import DatabaseManager
from psarc_library.models import (
    ListFailedPsarcResponse,
    ListPsarcDataResponse,
    PsarcLibraryServerConfig,
    StatsResponse,
    SyncResponse,
    ToggleInGameResponse,
)

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

        if not (game_dir := os.getenv(GAME_DIR_ENV_VAR)):
            error_msg = f"Environment variable not set: {GAME_DIR_ENV_VAR}"
            logger.error(error_msg)
            raise SystemExit(error_msg)

        self.game_dir = Path(game_dir)
        self.db_manager = DatabaseManager(
            db_config=self.config.db, base_psarc_file=self.game_dir / "songs.psarc", psarc_dir=self.game_dir / "dlc"
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
        # PSARC data endpoints (read-only)
        self.add_authenticated_route(
            endpoint="/psarc",
            handler_function=self.list_psarc_data,
            response_model=ListPsarcDataResponse,
            methods=["GET"],
            limited=True,
        )
        self.add_authenticated_route(
            endpoint="/psarc/toggle-in-game",
            handler_function=self.toggle_in_game,
            response_model=ToggleInGameResponse,
            methods=["PATCH"],
            limited=True,
        )

        # Sync and validation endpoints
        self.add_authenticated_route(
            endpoint="/sync",
            handler_function=self.sync_psarc_directory,
            response_model=SyncResponse,
            methods=["POST"],
            limited=True,
        )

        # Failed PSARC endpoints
        self.add_authenticated_route(
            endpoint="/failures",
            handler_function=self.list_failed_psarc,
            response_model=ListFailedPsarcResponse,
            methods=["GET"],
            limited=True,
        )

        # Stats endpoint
        self.add_authenticated_route(
            endpoint="/stats",
            handler_function=self.get_stats,
            response_model=StatsResponse,
            methods=["GET"],
            limited=True,
        )

    async def list_psarc_data(
        self, request: Request, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)
    ) -> ListPsarcDataResponse:
        """List all PSARC data entries with pagination.

        :param Request request: The incoming HTTP request
        :param int skip: Number of entries to skip
        :param int limit: Maximum number of entries to return
        :return ListPsarcDataResponse: Response containing list of PSARC data entries
        """
        psarc_data_list = self.db_manager.get_all_psarc_data(skip=skip, limit=limit)
        total = self.db_manager.count_psarc_data()
        return ListPsarcDataResponse(
            message=f"Retrieved {len(psarc_data_list)} PSARC data entries",
            data=psarc_data_list,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def toggle_in_game(self, request: Request, filename: str = Query(...)) -> ToggleInGameResponse:
        """Toggle the is_in_game flag for a PSARC file by filename.

        :param Request request: The incoming HTTP request
        :param str filename: The filename of the PSARC file to toggle
        :return ToggleInGameResponse: Response containing the new in-game status
        :raise HTTPException: If the PSARC file is not found
        """
        new_value = self.db_manager.toggle_is_in_game(filename=filename)
        if new_value is None:
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=f"PSARC file '{filename}' not found")
        return ToggleInGameResponse(
            message=f"Toggled in-game status for '{filename}' to {new_value}",
            filename=filename,
            is_in_game=new_value,
        )

    async def sync_psarc_directory(self, request: Request) -> SyncResponse:
        """Rescan the PSARC directory and add any new files.

        Also cleans up failed entries for files that no longer exist.

        :param Request request: The incoming HTTP request
        :return SyncResponse: Response containing sync statistics
        """
        stats = self.db_manager.sync_psarc_directory()
        message = (
            f"Sync completed: {stats['added']} added, {stats['failed']} failed, "
            f"{stats['skipped']} skipped, {stats['cleaned']} cleaned"
        )
        return SyncResponse(
            message=message,
            files_processed=stats["processed"],
            files_added=stats["added"],
            files_failed=stats["failed"],
            files_skipped=stats["skipped"],
            files_cleaned=stats["cleaned"],
        )

    async def list_failed_psarc(
        self, request: Request, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)
    ) -> ListFailedPsarcResponse:
        """List all failed PSARC entries with pagination.

        :param Request request: The incoming HTTP request
        :param int skip: Number of entries to skip
        :param int limit: Maximum number of entries to return
        :return ListFailedPsarcResponse: Response containing list of failed PSARC entries
        """
        failed_list = self.db_manager.get_all_failed_psarc(skip=skip, limit=limit)
        total = self.db_manager.count_failed_psarc()
        return ListFailedPsarcResponse(
            message=f"Retrieved {len(failed_list)} failed PSARC entries",
            data=failed_list,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_stats(self, request: Request) -> StatsResponse:
        """Get database statistics.

        :param Request request: The incoming HTTP request
        :return StatsResponse: Response containing database statistics
        """
        total_psarc = self.db_manager.count_psarc_data()
        total_songs = self.db_manager.count_songs()
        total_failed = self.db_manager.count_failed_psarc()
        return StatsResponse(
            message="Statistics retrieved successfully",
            total_psarc_files=total_psarc,
            total_songs=total_songs,
            total_failed_files=total_failed,
        )
