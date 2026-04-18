"""Pydantic models for the server."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError
from python_template_server.models import BaseResponse, TemplateServerConfig


# PSARC Library Configuration Models
class PsarcDatabaseConfig(BaseModel):
    """Configuration for the PSARC Library database."""

    db_directory: str = Field(
        default="data", description="The directory where the SQLite database file will be stored."
    )
    db_filename: str = Field(default="psarc_library.db", description="The filename for the SQLite database.")

    @property
    def db_url(self) -> str:
        """Construct the database URL for SQLAlchemy."""
        return f"sqlite:///{self.db_directory}/{self.db_filename}"


class PsarcLibraryServerConfig(TemplateServerConfig):
    """PSARC Library server configuration."""

    db: PsarcDatabaseConfig = Field(
        default_factory=PsarcDatabaseConfig, description="Configuration for the PSARC Library database."
    )


# PSARC Models
class TuningRoots(StrEnum):
    """Enumeration for tuning roots."""

    E = "E"
    F = "F"
    G_FLAT = "Gb"
    G = "G"
    A_FLAT = "Ab"
    A = "A"
    B_FLAT = "Bb"
    B = "B"
    C = "C"
    D_FLAT = "Db"
    D = "D"
    E_FLAT = "Eb"

    @classmethod
    def from_semitone_offset(cls, offset: int) -> TuningRoots:
        """Get the tuning root corresponding to a semitone offset from E standard."""
        roots = list(cls)
        return roots[offset % len(roots)]


class TuningType(StrEnum):
    """Enumeration for tuning types."""

    STANDARD = "Standard"
    DROP = "Drop"
    CUSTOM = "Custom"


class TuningDict(BaseModel):
    """Model representing a tuning dictionary from the PSARC manifest."""

    string0: int = Field(..., description="Semitone offset for E string.")
    string1: int = Field(..., description="Semitone offset for A string.")
    string2: int = Field(..., description="Semitone offset for D string.")
    string3: int = Field(..., description="Semitone offset for G string.")
    string4: int = Field(..., description="Semitone offset for B string.")
    string5: int = Field(..., description="Semitone offset for E string.")

    @property
    def tuning_type(self) -> TuningType:
        """Determine the tuning type based on the semitone offsets."""
        if all(self.string0 == getattr(self, f"string{i}") for i in range(6)):
            return TuningType.STANDARD

        if all(self.string0 + 2 == getattr(self, f"string{i}") for i in range(1, 6)):
            return TuningType.DROP

        return TuningType.CUSTOM


class Tuning(BaseModel):
    """Model representing the tuning of a song."""

    root: TuningRoots = Field(..., description="The root note of the tuning.")
    type: TuningType = Field(..., description="The type of tuning (Standard, Drop, Custom).")

    @classmethod
    def from_tuning_dict(cls, tuning_dict: TuningDict) -> Tuning:
        """Create a Tuning instance from a TuningDict."""
        return cls(root=TuningRoots.from_semitone_offset(tuning_dict.string0), type=tuning_dict.tuning_type)


class SongData(BaseModel):
    """Model representing metadata for a single song extracted from a PSARC file."""

    title: str = Field(..., description="The title of the song.")
    artist: str = Field(..., description="The artist of the song.")
    album: str = Field(..., description="The album of the song.")
    year: int = Field(..., description="The release year of the song.")
    tuning: Tuning = Field(..., description="The tuning of the song.")
    length: float = Field(..., description="The length of the song in seconds.")
    tempo: int = Field(..., description="The tempo of the song in BPM.")
    dlc: bool = Field(..., description="Whether the song is DLC or not.")
    dlc_key: str = Field(..., description="The DLC key if the song is DLC, otherwise empty string.")

    @classmethod
    def from_entry(cls, entry: dict) -> SongData:
        """Create a SongData instance from a dictionary entry."""
        attributes: dict = entry.get("Attributes", {})
        return cls(
            title=attributes.get("SongName", ""),
            artist=attributes.get("ArtistName", ""),
            album=attributes.get("AlbumName", ""),
            year=attributes.get("SongYear", 0),
            tuning=Tuning.from_tuning_dict(TuningDict.model_validate(attributes.get("Tuning", {}))),
            length=attributes.get("SongLength", 0),
            tempo=attributes.get("SongAverageTempo", 0),
            dlc=attributes.get("DLC", False),
            dlc_key=attributes.get("DLCKey", ""),
        )

    @property
    def is_valid(self) -> bool:
        """Check if the song data is valid."""
        return bool(self.title and self.artist and self.album and self.year > 0)


class PsarcData(BaseModel):
    """Model representing extracted data from a PSARC file."""

    filename: str = Field(..., description="The filename of the PSARC file.")
    entries: list[SongData] = Field(..., description="A list of song metadata entries extracted from the PSARC file.")
    iteration_version: int = Field(..., description="The iteration version of the PSARC file.")
    model_name: str = Field(..., description="The type of PSARC file.")
    is_in_game: bool = Field(
        default=False,
        description="Manually set depending on whether or not the PSARC successfully imported into the game.",
    )

    @staticmethod
    def filter_entries_function(entry: SongData) -> bool:
        """Filter function to determine if a SongData entry should be included."""
        return entry.is_valid

    @staticmethod
    def filter_psarc_data_function(psarc_data: PsarcData) -> bool:
        """Filter function to determine if a PsarcData entry should be included."""
        return len(psarc_data.entries) > 0

    @classmethod
    def from_manifest(cls, filename: str, manifest: dict) -> PsarcData:
        """Create a PsarcData instance from parsed PSARC data."""
        entries: dict = manifest.get("Entries", {})
        parsed_entries: list[SongData] = []

        for entry in entries.values():
            try:
                parsed_entries.append(SongData.from_entry(entry))
            except ValidationError:
                continue

        parsed_entries = list(filter(cls.filter_entries_function, parsed_entries))

        iteration_version = manifest.get("IterationVersion", 0)
        model_name = manifest.get("ModelName", "")

        return cls(
            filename=filename,
            entries=parsed_entries,
            iteration_version=iteration_version,
            model_name=model_name,
        )

    @classmethod
    def from_manifests(cls, filename: str, manifests: list[dict]) -> list[PsarcData]:
        """Create a list of PsarcData instances from a list of parsed PSARC manifest data."""
        psarc_data_list = []
        for manifest in manifests:
            if (psarc_data := cls.from_manifest(filename=filename, manifest=manifest)) not in psarc_data_list:
                psarc_data_list.append(psarc_data)

        return list(filter(cls.filter_psarc_data_function, psarc_data_list))


# PSARC File Models
class PsarcHeader(BaseModel):
    """Model representing the header of a PSARC file."""

    toc_length: int = Field(..., description="The length of the TOC in bytes.")
    toc_entry_size: int = Field(..., description="The size of each TOC entry in bytes.")
    toc_count: int = Field(..., description="The number of entries in the TOC.")
    block_size: int = Field(..., description="The size of each data block in bytes.")
    archive_flags: int = Field(..., description="Flags indicating properties of the PSARC archive.")


class PsarcTocEntry(BaseModel):
    """Model representing a single entry in the PSARC TOC."""

    zindex: int = Field(..., description="The index of the compressed block containing the file data.")
    length: int = Field(..., description="The uncompressed length of the file data in bytes.")
    offset: int = Field(..., description="The offset of the file data from the start of the data blocks in bytes.")


# Failed PSARC Models
class FailedPsarcEntry(BaseModel):
    """Model representing a failed PSARC file parsing attempt."""

    filename: str = Field(..., description="The filename of the failed PSARC file.")
    filepath: str = Field(..., description="The full path to the failed PSARC file.")
    error_type: str = Field(..., description="The type of error that occurred.")
    error_message: str = Field(..., description="Detailed error message.")
    timestamp: str = Field(..., description="When the failure occurred.")
    file_size: int | None = Field(None, description="Size of the PSARC file in bytes.")
    raw_data: str | None = Field(None, description="Any raw data that could be extracted before failure.")


# API Response Models
class GetPsarcDataResponse(BaseResponse):
    """Response model for getting a single PSARC data entry."""

    data: PsarcData = Field(..., description="The PSARC data")
    psarc_id: int = Field(..., description="The ID of the PSARC data entry")


class ListPsarcDataResponse(BaseResponse):
    """Response model for listing PSARC data entries."""

    data: list[PsarcData] = Field(..., description="List of PSARC data entries")
    total: int = Field(..., description="Total number of PSARC data entries")
    skip: int = Field(..., description="Number of entries skipped")
    limit: int = Field(..., description="Maximum number of entries returned")


class SearchSongsResponse(BaseResponse):
    """Response model for searching songs."""

    data: list[SongData] = Field(..., description="List of songs matching the search criteria")
    total: int = Field(..., description="Total number of songs found")


class StatsResponse(BaseResponse):
    """Response model for database statistics."""

    total_psarc_files: int = Field(..., description="Total number of PSARC files in the database")
    total_songs: int = Field(..., description="Total number of songs in the database")
    total_failed_files: int = Field(default=0, description="Total number of failed PSARC files in the database")


class SyncResponse(BaseResponse):
    """Response model for sync operation."""

    files_processed: int = Field(..., description="Number of files processed")
    files_added: int = Field(..., description="Number of new files added")
    files_failed: int = Field(..., description="Number of files that failed to parse")
    files_skipped: int = Field(..., description="Number of files skipped (already in database)")
    files_cleaned: int = Field(..., description="Number of failed entries cleaned up for missing files")


class ValidatePsarcResponse(BaseResponse):
    """Response model for PSARC file validation."""

    filename: str = Field(..., description="The filename that was validated")
    is_valid: bool = Field(..., description="Whether the file is valid")
    data: PsarcData | None = Field(None, description="Parsed PSARC data if valid")
    error: FailedPsarcEntry | None = Field(None, description="Error details if invalid")


class ListFailedPsarcResponse(BaseResponse):
    """Response model for listing failed PSARC entries."""

    data: list[FailedPsarcEntry] = Field(..., description="List of failed PSARC entries")
    total: int = Field(..., description="Total number of failed entries")
    skip: int = Field(..., description="Number of entries skipped")
    limit: int = Field(..., description="Maximum number of entries returned")
