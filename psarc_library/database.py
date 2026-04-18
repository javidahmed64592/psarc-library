"""SQLModel database module."""

import logging
from pathlib import Path

from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

from psarc_library.models import PsarcData, PsarcDatabaseConfig, SongData, Tuning
from psarc_library.psarc import parse_psarc

logger = logging.getLogger(__name__)


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
        return Tuning(root=self.root, type=self.type)


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


# Database Manager
class DatabaseManager:
    """Manager class for database operations."""

    def __init__(self, db_config: PsarcDatabaseConfig, psarc_dir: Path) -> None:
        """Initialize the database manager."""
        self.db_config = db_config
        self.psarc_dir = psarc_dir

        logger.info("Creating database directory: %s", self.db_config.db_directory)
        Path(self.db_config.db_directory).mkdir(parents=True, exist_ok=True)

        logger.info("Initializing database with URL: %s", self.db_config.db_url)
        self.engine = create_engine(self.db_config.db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)

        logger.info("Adding initial entries from PSARC directory: %s", self.psarc_dir)
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Scan the PSARC directory and add entries to the database."""
        psarc_files = list(self.psarc_dir.glob("*.psarc"))
        logger.info("Found %d PSARC files in directory", len(psarc_files))

        for psarc_file in psarc_files:
            if self.get_psarc_data_by_filename(filename=psarc_file.name):
                continue

            logger.info("Processing PSARC file: %s", psarc_file.name)
            if not (manifests := parse_psarc(filepath=psarc_file)):
                logger.warning("No valid manifests found in PSARC file: %s", psarc_file.name)
                continue

            if not (psarc_data_list := PsarcData.from_manifests(filename=psarc_file.name, manifests=manifests)):
                logger.warning("Failed to create PSARC data from manifests for file: %s", psarc_file.name)
                continue

            for psarc_data in psarc_data_list:
                self.add_psarc_data(psarc_data=psarc_data)

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
            return psarc_data_db

    def get_psarc_data(self, psarc_id: int) -> PsarcData | None:
        """Get a PsarcData object by ID."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).where(PsarcDataDB.id == psarc_id)
            if psarc_data_db := session.exec(statement).first():
                logger.info("Retrieved PSARC data: %s", psarc_data_db.filename)
                return psarc_data_db.to_psarc_data()
            return None

    def get_all_psarc_data(self, skip: int = 0, limit: int = 100) -> list[PsarcData]:
        """Get all PsarcData objects with pagination."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).offset(skip).limit(limit)
            psarc_data_list = session.exec(statement).all()
            logger.info("Retrieved %d PSARC data entries", len(psarc_data_list))
            return [psarc.to_psarc_data() for psarc in psarc_data_list]

    def update_psarc_data(self, psarc_id: int, psarc_data: PsarcData) -> PsarcData | None:
        """Update a PsarcData object."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).where(PsarcDataDB.id == psarc_id)
            if not (psarc_data_db := session.exec(statement).first()):
                return None

            logger.info("Updating PSARC data: %s", psarc_data_db.filename)
            psarc_data_db.filename = psarc_data.filename
            psarc_data_db.iteration_version = psarc_data.iteration_version
            psarc_data_db.model_name = psarc_data.model_name
            psarc_data_db.is_in_game = psarc_data.is_in_game

            for song in psarc_data_db.songs:
                logger.info("Deleting song: %s by %s", song.title, song.artist)
                session.delete(song)

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
            return psarc_data_db.to_psarc_data()

    def delete_psarc_data(self, psarc_id: int) -> bool:
        """Delete a PsarcData object by ID."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB).where(PsarcDataDB.id == psarc_id)
            if not (psarc_data_db := session.exec(statement).first()):
                return False

            logger.info("Deleting PSARC data: %s", psarc_data_db.filename)
            session.delete(psarc_data_db)
            session.commit()
            return True

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
                statement = statement.where(SongDataDB.title.contains(title))
            if artist:
                statement = statement.where(SongDataDB.artist.contains(artist))
            if album:
                statement = statement.where(SongDataDB.album.contains(album))
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

    def count_psarc_data(self) -> int:
        """Count total number of PSARC data entries."""
        with Session(self.engine) as session:
            statement = select(PsarcDataDB)
            count = len(session.exec(statement).all())
            logger.info("Total PSARC data entries: %d", count)
            return count

    def count_songs(self) -> int:
        """Count total number of songs."""
        with Session(self.engine) as session:
            statement = select(SongDataDB)
            count = len(session.exec(statement).all())
            logger.info("Total songs: %d", count)
            return count
