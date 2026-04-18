"""PSARC Library server implementation using the TemplateServer base class."""

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Query, Request, UploadFile
from python_template_server.models import ResponseCode
from python_template_server.template_server import TemplateServer

from psarc_library.constants import PSARC_DIR_ENV_VAR
from psarc_library.database import DatabaseManager
from psarc_library.models import (
    GetPsarcDataResponse,
    ListFailedPsarcResponse,
    ListPsarcDataResponse,
    PsarcLibraryServerConfig,
    SearchSongsResponse,
    StatsResponse,
    SyncResponse,
    ValidatePsarcResponse,
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

        if not (psarc_dir := os.getenv(PSARC_DIR_ENV_VAR)):
            error_msg = f"Environment variable not set: {PSARC_DIR_ENV_VAR}"
            logger.error(error_msg)
            raise SystemExit(error_msg)

        self.psarc_dir = Path(psarc_dir)
        self.db_manager = DatabaseManager(db_config=self.config.db, psarc_dir=self.psarc_dir)

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
            endpoint="/psarc/{psarc_id}",
            handler_function=self.get_psarc_data,
            response_model=GetPsarcDataResponse,
            methods=["GET"],
            limited=True,
        )
        self.add_authenticated_route(
            endpoint="/psarc",
            handler_function=self.list_psarc_data,
            response_model=ListPsarcDataResponse,
            methods=["GET"],
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
        self.add_authenticated_route(
            endpoint="/validate",
            handler_function=self.validate_psarc_file,
            response_model=ValidatePsarcResponse,
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

        # Song search and stats
        self.add_authenticated_route(
            endpoint="/songs/search",
            handler_function=self.search_songs,
            response_model=SearchSongsResponse,
            methods=["GET"],
            limited=True,
        )
        self.add_authenticated_route(
            endpoint="/stats",
            handler_function=self.get_stats,
            response_model=StatsResponse,
            methods=["GET"],
            limited=True,
        )

    async def get_psarc_data(self, request: Request, psarc_id: int) -> GetPsarcDataResponse:
        """Get a PSARC data entry by ID.

        :param Request request: The incoming HTTP request
        :param int psarc_id: The ID of the PSARC data entry
        :return GetPsarcDataResponse: Response containing the PSARC data
        :raise HTTPException: If the PSARC data is not found
        """
        psarc_data = self.db_manager.get_psarc_data(psarc_id)
        if not psarc_data:
            raise HTTPException(status_code=ResponseCode.NOT_FOUND, detail=f"PSARC data with ID {psarc_id} not found")
        return GetPsarcDataResponse(
            message="PSARC data retrieved successfully",
            timestamp=GetPsarcDataResponse.current_timestamp(),
            data=psarc_data,
            psarc_id=psarc_id,
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
            timestamp=ListPsarcDataResponse.current_timestamp(),
            data=psarc_data_list,
            total=total,
            skip=skip,
            limit=limit,
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
            timestamp=SyncResponse.current_timestamp(),
            files_processed=stats["processed"],
            files_added=stats["added"],
            files_failed=stats["failed"],
            files_skipped=stats["skipped"],
            files_cleaned=stats["cleaned"],
        )

    async def validate_psarc_file(self, request: Request, file: UploadFile) -> ValidatePsarcResponse:
        """Validate an uploaded PSARC file without adding it to the database.

        :param Request request: The incoming HTTP request
        :param UploadFile file: The uploaded PSARC file
        :return ValidatePsarcResponse: Response containing validation results
        :raise HTTPException: If file upload fails
        """
        if not file.filename or not file.filename.endswith(".psarc"):
            raise HTTPException(status_code=ResponseCode.BAD_REQUEST, detail="File must be a .psarc file")

        # Save uploaded file temporarily
        temp_path = Path(self.psarc_dir) / f"_temp_{file.filename}"
        try:
            content = await file.read()
            temp_path.write_bytes(content)

            # Validate the file
            is_valid, psarc_data, error = self.db_manager.validate_psarc_file(filepath=temp_path)

            if is_valid and psarc_data:
                return ValidatePsarcResponse(
                    message=f"PSARC file '{file.filename}' is valid",
                    timestamp=ValidatePsarcResponse.current_timestamp(),
                    filename=file.filename,
                    is_valid=True,
                    data=psarc_data,
                    error=None,
                )

            return ValidatePsarcResponse(
                message=f"PSARC file '{file.filename}' is invalid",
                timestamp=ValidatePsarcResponse.current_timestamp(),
                filename=file.filename,
                is_valid=False,
                data=None,
                error=error,
            )

        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()

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
            timestamp=ListFailedPsarcResponse.current_timestamp(),
            data=failed_list,
            total=total,
            skip=skip,
            limit=limit,
        )

    async def search_songs(
        self,
        request: Request,
        title: str | None = Query(None),
        artist: str | None = Query(None),
        album: str | None = Query(None),
        year: int | None = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
    ) -> SearchSongsResponse:
        """Search for songs by title, artist, album, or year.

        :param Request request: The incoming HTTP request
        :param str | None title: Song title to search for (partial match)
        :param str | None artist: Artist name to search for (partial match)
        :param str | None album: Album name to search for (partial match)
        :param int | None year: Release year to filter by (exact match)
        :param int skip: Number of entries to skip
        :param int limit: Maximum number of entries to return
        :return SearchSongsResponse: Response containing list of matching songs
        """
        songs = self.db_manager.search_songs(
            title=title,
            artist=artist,
            album=album,
            year=year,
            skip=skip,
            limit=limit,
        )
        return SearchSongsResponse(
            message=f"Found {len(songs)} songs",
            timestamp=SearchSongsResponse.current_timestamp(),
            data=songs,
            total=len(songs),
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
            timestamp=StatsResponse.current_timestamp(),
            total_psarc_files=total_psarc,
            total_songs=total_songs,
            total_failed_files=total_failed,
        )
