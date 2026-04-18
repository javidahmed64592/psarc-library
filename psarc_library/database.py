"""SQLModel database module."""

import logging
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

from cachetools import TTLCache
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

from psarc_library.constants import CACHE_MAXSIZE, CACHE_TTL
from psarc_library.models import (
    FailedPsarcEntry,
    PsarcData,
    PsarcDatabaseConfig,
    SongData,
    Tuning,
    TuningRoots,
    TuningType,
)
from psarc_library.psarc import parse_psarc

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")


def cache_method[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to cache method results with automatic invalidation.

    Uses a TTL cache with a 5-minute expiration time. Cache is stored on the instance
    and can be cleared via the instance's _clear_cache method.
    """

    @wraps(func)
    def wrapper(self: "DatabaseManager", *args: Any, **kwargs: Any) -> T:  # noqa: ANN401
        # Generate cache key from function name and arguments
        cache_key = f"{func.__name__}:{args}:{kwargs}"

        # Check if result is in cache
        if cache_key in self._cache:
            logger.debug("Cache hit for %s", cache_key)
            return self._cache[cache_key]  # type: ignore[no-any-return]

        # Call function and cache result
        result = func(self, *args, **kwargs)
        self._cache[cache_key] = result
        logger.debug("Cache miss for %s - result cached", cache_key)
        return result

    return wrapper


# Database Models
class TuningDB(SQLModel, table=True):
    """Model representing a tuning entry in the database."""

    __tablename__ = "tuning"

    id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the tuning")
    root: str = Field(..., description="The root note of the tuning")
    type: str = Field(..., description="The type of tuning (Standard, Drop, Custom)")

    # Relationships
    songs: list["SongDataDB"] = Relationship(back_populates="tuning")

    @classmethod
    def from_tuning(cls, tuning: Tuning) -> "TuningDB":
        """Create a TuningDB instance from a Tuning model."""
        return cls(root=tuning.root, type=tuning.type)

    def to_tuning(self) -> Tuning:
        """Convert TuningDB to Tuning model."""
        return Tuning(root=TuningRoots(self.root), type=TuningType(self.type))


class SongDataDB(SQLModel, table=True):
    """Model representing song metadata in the database."""

    __tablename__ = "song_data"

    id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the song")
    psarc_data_id: int = Field(..., foreign_key="psarc_data.id", description="Foreign key to PSARC data")
    tuning_id: int = Field(..., foreign_key="tuning.id", description="Foreign key to tuning")
    title: str = Field(..., description="The title of the song", index=True)
    artist: str = Field(..., description="The artist of the song", index=True)
    album: str = Field(..., description="The album of the song", index=True)
    year: int = Field(..., description="The release year of the song", index=True)
    length: float = Field(..., description="The length of the song in seconds")
    tempo: int = Field(..., description="The tempo of the song in BPM")
    dlc: bool = Field(..., description="Whether the song is DLC or not", index=True)
    dlc_key: str = Field(..., description="The DLC key if the song is DLC, otherwise empty string")

    # Relationships
    psarc_data: "PsarcDataDB" = Relationship(back_populates="songs")
    tuning: TuningDB = Relationship(back_populates="songs")

    def to_song_data(self) -> SongData:
        """Convert SongDataDB to SongData model."""
        return SongData(
            title=self.title,
            artist=self.artist,
            album=self.album,
            year=self.year,
            tuning=self.tuning.to_tuning(),
            length=self.length,
            tempo=self.tempo,
            dlc=self.dlc,
            dlc_key=self.dlc_key,
        )


class PsarcDataDB(SQLModel, table=True):
    """Model representing a PSARC data entry in the database."""

    __tablename__ = "psarc_data"

    id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the PSARC data entry")
    filename: str = Field(..., description="The filename of the PSARC file", index=True)
    iteration_version: int = Field(..., description="The iteration version of the PSARC file")
    model_name: str = Field(..., description="The type of PSARC file")
    is_in_game: bool = Field(default=False, description="Whether the PSARC successfully imported into the game")

    # Relationships
    songs: list[SongDataDB] = Relationship(back_populates="psarc_data", cascade_delete=True)

    def to_psarc_data(self) -> PsarcData:
        """Convert PsarcDataDB to PsarcData model."""
        return PsarcData(
            filename=self.filename,
            entries=[song.to_song_data() for song in self.songs],
            iteration_version=self.iteration_version,
            model_name=self.model_name,
            is_in_game=self.is_in_game,
        )


class FailedPsarcDB(SQLModel, table=True):
    """Model representing a failed PSARC file parsing attempt in the database."""

    __tablename__ = "failed_psarc"

    id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the failed entry")
    filename: str = Field(..., description="The filename of the failed PSARC file", index=True)
    filepath: str = Field(..., description="The full path to the failed PSARC file")
    error_type: str = Field(..., description="The type of error that occurred")
    error_message: str = Field(..., description="Detailed error message")
    timestamp: str = Field(..., description="When the failure occurred")
    file_size: int | None = Field(None, description="Size of the PSARC file in bytes")
    raw_data: str | None = Field(None, description="Any raw data that could be extracted before failure")

    @classmethod
    def from_failed_entry(cls, entry: FailedPsarcEntry) -> "FailedPsarcDB":
        """Create a FailedPsarcDB instance from a FailedPsarcEntry model."""
        return cls(
            filename=entry.filename,
            filepath=entry.filepath,
            error_type=entry.error_type,
            error_message=entry.error_message,
            timestamp=entry.timestamp,
            file_size=entry.file_size,
            raw_data=entry.raw_data,
        )

    def to_failed_entry(self) -> FailedPsarcEntry:
        """Convert FailedPsarcDB to FailedPsarcEntry model."""
        return FailedPsarcEntry(
            filename=self.filename,
            filepath=self.filepath,
            error_type=self.error_type,
            error_message=self.error_message,
            timestamp=self.timestamp,
            file_size=self.file_size,
            raw_data=self.raw_data,
        )


# Database Manager
class DatabaseManager:
    """Manager class for database operations."""

    def __init__(self, db_config: PsarcDatabaseConfig, psarc_dir: Path) -> None:
        """Initialize the database manager."""
        self.db_config = db_config
        self.psarc_dir = psarc_dir
        self._cache: TTLCache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL)

        logger.info("Creating database directory: %s", self.db_config.db_directory)
        Path(self.db_config.db_directory).mkdir(parents=True, exist_ok=True)

        logger.info("Initializing database with URL: %s", self.db_config.db_url)
        self.engine = create_engine(self.db_config.db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)

        logger.info("Adding initial entries from PSARC directory: %s", self.psarc_dir)
        self._initialize_database()

    def _clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def _initialize_database(self) -> None:
        """Scan the PSARC directory and add entries to the database."""
        psarc_files = list(self.psarc_dir.glob("*.psarc"))
        logger.info("Found %d PSARC files in directory", len(psarc_files))

        for psarc_file in psarc_files:
            if self.get_psarc_data_by_filename(filename=psarc_file.name):
                continue

            self._process_psarc_file(psarc_file=psarc_file)

    def _process_psarc_file(self, psarc_file: Path) -> bool:
        """Process a single PSARC file and add it to the database or record failure.

        :param Path psarc_file: Path to the PSARC file
        :return bool: True if successfully processed, False otherwise
        """
        logger.info("Processing PSARC file: %s", psarc_file.name)

        try:
            # Try to parse the PSARC file
            manifests = parse_psarc(filepath=psarc_file)
            if not manifests:
                self._record_failure(
                    filepath=psarc_file,
                    error_type="ParseError",
                    error_message="No valid manifests found in PSARC file",
                    raw_data=None,
                )
                return False

            # Try to create PsarcData from manifests
            psarc_data_list = PsarcData.from_manifests(filename=psarc_file.name, manifests=manifests)
            if not psarc_data_list:
                self._record_failure(
                    filepath=psarc_file,
                    error_type="ValidationError",
                    error_message="Failed to create PSARC data from manifests - no valid entries found",
                    raw_data=str(manifests),
                )
                return False

        except Exception as e:
            # Catch any unexpected errors and record them
            error_trace = traceback.format_exc()
            self._record_failure(
                filepath=psarc_file,
                error_type=type(e).__name__,
                error_message=f"{e!s}\n\nTraceback:\n{error_trace}",
                raw_data=None,
            )
            logger.exception("Unexpected error processing PSARC file: %s", psarc_file.name)
            return False
        else:
            # Add all valid PSARC data to database
            for psarc_data in psarc_data_list:
                self.add_psarc_data(psarc_data=psarc_data)

            logger.info("Successfully processed PSARC file: %s", psarc_file.name)
            return True

    def _record_failure(
        self, filepath: Path, error_type: str, error_message: str, raw_data: str | None
    ) -> FailedPsarcDB:
        """Record a failed PSARC file parsing attempt.

        :param Path filepath: Path to the failed PSARC file
        :param str error_type: Type of error
        :param str error_message: Detailed error message
        :param str | None raw_data: Any raw data extracted before failure
        :return FailedPsarcDB: The recorded failure entry
        """
        file_size = filepath.stat().st_size if filepath.exists() else None
        timestamp = datetime.now(UTC).isoformat()

        failed_entry = FailedPsarcEntry(
            filename=filepath.name,
            filepath=str(filepath),
            error_type=error_type,
            error_message=error_message,
            timestamp=timestamp,
            file_size=file_size,
            raw_data=raw_data,
        )

        with Session(self.engine) as session:
            # Check if failure already exists for this file
            statement = select(FailedPsarcDB).where(FailedPsarcDB.filename == failed_entry.filename)
            if existing := session.exec(statement).first():
                # Update existing failure record
                logger.info("Updating existing failure record for: %s", filepath.name)
                existing.error_type = failed_entry.error_type
                existing.error_message = failed_entry.error_message
                existing.timestamp = timestamp
                existing.file_size = file_size
                existing.raw_data = raw_data
                session.commit()
                session.refresh(existing)
                return existing

            # Create new failure record
            logger.warning("Recording failure for PSARC file: %s - %s", filepath.name, error_type)
            failed_db = FailedPsarcDB.from_failed_entry(failed_entry)
            session.add(failed_db)
            session.commit()
            session.refresh(failed_db)
            self._clear_cache()  # Cache invalidation for failed entries
            return failed_db

    def _get_or_create_tuning(self, session: Session, tuning: Tuning) -> TuningDB:
        """Get existing tuning or create a new one."""
        statement = select(TuningDB).where(TuningDB.root == tuning.root, TuningDB.type == tuning.type)
        if tuning_db := session.exec(statement).first():
            return tuning_db

        tuning_db = TuningDB.from_tuning(tuning=tuning)
        session.add(tuning_db)
        session.flush()
        return tuning_db

    def add_psarc_data(self, psarc_data: PsarcData) -> PsarcDataDB:
        """Add a PsarcData object to the database."""
        with Session(self.engine) as session:
            psarc_data_db = PsarcDataDB(
                filename=psarc_data.filename,
                iteration_version=psarc_data.iteration_version,
                model_name=psarc_data.model_name,
                is_in_game=psarc_data.is_in_game,
            )

            logger.info("Adding PSARC data: %s", psarc_data_db.filename)
            session.add(psarc_data_db)
            session.flush()

            for song in psarc_data.entries:
                tuning_db = self._get_or_create_tuning(session=session, tuning=song.tuning)
                song_db = SongDataDB(
                    psarc_data_id=psarc_data_db.id,
                    tuning_id=tuning_db.id,
                    title=song.title,
                    artist=song.artist,
                    album=song.album,
                    year=song.year,
                    length=song.length,
                    tempo=song.tempo,
                    dlc=song.dlc,
                    dlc_key=song.dlc_key,
                )
                logger.info("Adding song: %s by %s", song_db.title, song_db.artist)
                session.add(song_db)

            session.commit()
            session.refresh(psarc_data_db)
            self._clear_cache()  # Cache invalidation for PSARC data and song counts
            return psarc_data_db

    def get_psarc_data(self, psarc_id: int) -> PsarcData | None:
        """Get a PsarcData object by ID."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).where(PsarcDataDB.id == psarc_id)
            if psarc_data_db := session.exec(statement).first():
                logger.info("Retrieved PSARC data: %s", psarc_data_db.filename)
                return psarc_data_db.to_psarc_data()
            return None

    @cache_method
    def get_all_psarc_data(self, skip: int = 0, limit: int = 100) -> list[PsarcData]:
        """Get all PsarcData objects with pagination."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).offset(skip).limit(limit)
            psarc_data_list = session.exec(statement).all()
            logger.info("Retrieved %d PSARC data entries", len(psarc_data_list))
            return [psarc.to_psarc_data() for psarc in psarc_data_list]

    @cache_method
    def search_songs(
        self,
        title: str | None = None,
        artist: str | None = None,
        album: str | None = None,
        year: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SongData]:
        """Search for songs by various criteria."""
        with Session(self.engine) as session:
            statement = select(SongDataDB)
            if title:
                statement = statement.where(SongDataDB.title.contains(title))  # type: ignore[attr-defined]
            if artist:
                statement = statement.where(SongDataDB.artist.contains(artist))  # type: ignore[attr-defined]
            if album:
                statement = statement.where(SongDataDB.album.contains(album))  # type: ignore[attr-defined]
            if year:
                statement = statement.where(SongDataDB.year == year)
            statement = statement.offset(skip).limit(limit)
            songs = session.exec(statement).all()
            logger.info("Retrieved %d songs", len(songs))
            return [song.to_song_data() for song in songs]

    def get_psarc_data_by_filename(self, filename: str) -> PsarcData | None:
        """Get a PsarcData object by filename."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).where(PsarcDataDB.filename == filename)
            psarc_data_db = session.exec(statement).first()
            if psarc_data_db:
                logger.info("Retrieved PSARC data by filename: %s", psarc_data_db.filename)
                return psarc_data_db.to_psarc_data()
            return None

    @cache_method
    def count_psarc_data(self) -> int:
        """Count total number of PSARC data entries."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB)
            count = len(session.exec(statement).all())
            logger.info("Total PSARC data entries: %d", count)
            return count

    @cache_method
    def count_songs(self) -> int:
        """Count total number of songs."""
        with Session(self.engine) as session:
            statement = select(SongDataDB)
            count = len(session.exec(statement).all())
            logger.info("Total songs: %d", count)
            return count

    def sync_psarc_directory(self) -> dict[str, int]:
        """Rescan the PSARC directory and add any new files.

        Also cleans up failed entries for files that no longer exist.

        :return dict: Statistics about the sync operation
        """
        logger.info("Starting sync of PSARC directory: %s", self.psarc_dir)
        psarc_files = list(self.psarc_dir.glob("*.psarc"))
        existing_filenames = {f.name for f in psarc_files}
        stats = {"processed": 0, "added": 0, "failed": 0, "skipped": 0, "cleaned": 0}

        # Process existing files
        for psarc_file in psarc_files:
            stats["processed"] += 1

            # Skip if already in database
            if self.get_psarc_data_by_filename(filename=psarc_file.name):
                stats["skipped"] += 1
                continue

            # Process the file
            if self._process_psarc_file(psarc_file=psarc_file):
                stats["added"] += 1
            else:
                stats["failed"] += 1

        # Clean up failed entries for files that no longer exist
        all_failed = self.get_all_failed_psarc(skip=0, limit=10000)  # Get all failed entries
        for failed_entry in all_failed:
            if failed_entry.filename not in existing_filenames:
                logger.info("Cleaning up failed entry for missing file: %s", failed_entry.filename)
                if self.delete_failed_psarc_by_filename(filename=failed_entry.filename):
                    stats["cleaned"] += 1

        logger.info(
            "Sync completed: %d processed, %d added, %d failed, %d skipped, %d cleaned",
            stats["processed"],
            stats["added"],
            stats["failed"],
            stats["skipped"],
            stats["cleaned"],
        )
        self._clear_cache()  # Cache invalidation after sync operation
        return stats

    def validate_psarc_file(self, filepath: Path) -> tuple[bool, PsarcData | None, FailedPsarcEntry | None]:
        """Validate a PSARC file without adding it to the database.

        :param Path filepath: Path to the PSARC file
        :return tuple: (is_valid, psarc_data or None, error or None)
        """
        logger.info("Validating PSARC file: %s", filepath.name)

        try:
            # Try to parse the PSARC file
            manifests = parse_psarc(filepath=filepath)
            if not manifests:
                error = FailedPsarcEntry(
                    filename=filepath.name,
                    filepath=str(filepath),
                    error_type="ParseError",
                    error_message="No valid manifests found in PSARC file",
                    timestamp=datetime.now(UTC).isoformat(),
                    file_size=filepath.stat().st_size if filepath.exists() else None,
                    raw_data=None,
                )
                return False, None, error

            # Try to create PsarcData from manifests
            psarc_data_list = PsarcData.from_manifests(filename=filepath.name, manifests=manifests)
            if not psarc_data_list:
                error = FailedPsarcEntry(
                    filename=filepath.name,
                    filepath=str(filepath),
                    error_type="ValidationError",
                    error_message="Failed to create PSARC data from manifests - no valid entries found",
                    timestamp=datetime.now(UTC).isoformat(),
                    file_size=filepath.stat().st_size if filepath.exists() else None,
                    raw_data=str(manifests),
                )
                return False, None, error

            # Return first valid PsarcData (typically there's only one per file)
            logger.info("PSARC file is valid: %s", filepath.name)
            return True, psarc_data_list[0], None

        except Exception as e:
            error_trace = traceback.format_exc()
            error = FailedPsarcEntry(
                filename=filepath.name,
                filepath=str(filepath),
                error_type=type(e).__name__,
                error_message=f"{e!s}\n\nTraceback:\n{error_trace}",
                timestamp=datetime.now(UTC).isoformat(),
                file_size=filepath.stat().st_size if filepath.exists() else None,
                raw_data=None,
            )
            logger.exception("Error validating PSARC file: %s", filepath.name)
            return False, None, error

    @cache_method
    def get_all_failed_psarc(self, skip: int = 0, limit: int = 100) -> list[FailedPsarcEntry]:
        """Get all failed PSARC entries with pagination.

        :param int skip: Number of entries to skip
        :param int limit: Maximum number of entries to return
        :return list: List of FailedPsarcEntry objects
        """
        with Session(self.engine) as session:
            statement = select(FailedPsarcDB).offset(skip).limit(limit)
            failed_list = session.exec(statement).all()
            logger.info("Retrieved %d failed PSARC entries", len(failed_list))
            return [failed.to_failed_entry() for failed in failed_list]

    def delete_failed_psarc_by_filename(self, filename: str) -> bool:
        """Delete a failed PSARC entry by filename.

        :param str filename: The filename of the failed entry to delete
        :return bool: True if deleted, False if not found
        """
        with Session(self.engine) as session:
            statement = select(FailedPsarcDB).where(FailedPsarcDB.filename == filename)
            if not (failed_db := session.exec(statement).first()):
                return False

            logger.info("Deleting failed PSARC entry by filename: %s", filename)
            session.delete(failed_db)
            session.commit()
            self._clear_cache()  # Cache invalidation for failed entries
            return True

    @cache_method
    def count_failed_psarc(self) -> int:
        """Count total number of failed PSARC entries.

        :return int: Count of failed entries
        """
        with Session(self.engine) as session:
            statement = select(FailedPsarcDB)
            count = len(session.exec(statement).all())
            logger.info("Total failed PSARC entries: %d", count)
            return count
