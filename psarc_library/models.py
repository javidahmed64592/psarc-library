"""Pydantic models for the server."""

from __future__ import annotations

import logging
from enum import StrEnum

from pydantic import BaseModel, Field, ValidationError
from python_template_server.models import TemplateServerConfig

logger = logging.getLogger(__name__)


# Psarc Library Configuration Models
class PsarcLibraryServerConfig(TemplateServerConfig):
    """Psarc Library server configuration."""


# Psarc Models
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


# API Response Models
