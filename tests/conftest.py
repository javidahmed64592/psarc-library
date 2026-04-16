"""Pytest fixtures for the application's unit tests."""

import pytest

from psarc_library.models import (
    PsarcData,
    PsarcLibraryServerConfig,
    SongData,
    Tuning,
    TuningDict,
)


# Psarc Library Server Configuration Models
@pytest.fixture
def mock_psarc_library_server_config() -> PsarcLibraryServerConfig:
    """Provide a mock PsarcLibraryServerConfig instance."""
    return PsarcLibraryServerConfig()


# Psarc Models
@pytest.fixture
def mock_tuning_dict_standard() -> TuningDict:
    """Provide a mock TuningDict instance for standard tuning."""
    return TuningDict(string0=0, string1=0, string2=0, string3=0, string4=0, string5=0)


@pytest.fixture
def mock_tuning_dict_drop() -> TuningDict:
    """Provide a mock TuningDict instance for drop tuning."""
    return TuningDict(string0=-2, string1=0, string2=0, string3=0, string4=0, string5=0)


@pytest.fixture
def mock_tuning_dict_custom() -> TuningDict:
    """Provide a mock TuningDict instance for custom tuning."""
    return TuningDict(string0=-2, string1=0, string2=0, string3=0, string4=0, string5=-2)


@pytest.fixture
def mock_tuning_standard(mock_tuning_dict_standard: TuningDict) -> Tuning:
    """Provide a mock Tuning instance for standard tuning."""
    return Tuning.from_tuning_dict(tuning_dict=mock_tuning_dict_standard)


@pytest.fixture
def mock_tuning_drop(mock_tuning_dict_drop: TuningDict) -> Tuning:
    """Provide a mock Tuning instance for drop tuning."""
    return Tuning.from_tuning_dict(tuning_dict=mock_tuning_dict_drop)


@pytest.fixture
def mock_tuning_custom(mock_tuning_dict_custom: TuningDict) -> Tuning:
    """Provide a mock Tuning instance for custom tuning."""
    return Tuning.from_tuning_dict(tuning_dict=mock_tuning_dict_custom)


@pytest.fixture
def mock_song_data_entry(mock_tuning_dict_standard: TuningDict) -> dict:
    """Provide a mock song data entry."""
    return {
        "Attributes": {
            "SongName": "Song name",
            "ArtistName": "Artist name",
            "AlbumName": "Album name",
            "SongYear": 2026,
            "Tuning": mock_tuning_dict_standard.model_dump(),
            "SongLength": 180,
            "SongAverageTempo": 120,
            "DLC": True,
            "DLCKey": "ABC123",
        }
    }


@pytest.fixture
def mock_song_data(mock_song_data_entry: dict) -> SongData:
    """Provide a mock SongData instance."""
    return SongData.from_entry(entry=mock_song_data_entry)


@pytest.fixture
def mock_psarc_manifest(mock_song_data_entry: dict) -> dict:
    """Provide a mock PSARC manifest containing a single song entry."""
    return {
        "Entries": {
            "song1": mock_song_data_entry,
            "song2": {},
        },
        "IterationVersion": 1,
        "ModelName": "RSEnumerable",
    }


@pytest.fixture
def mock_psarc_manifest_no_entries() -> dict:
    """Provide a mock PSARC manifest containing no song entries."""
    return {
        "Entries": {},
        "IterationVersion": 1,
        "ModelName": "RSEnumerable",
    }


@pytest.fixture
def mock_psarc_data(mock_psarc_manifest: dict, mock_psarc_manifest_no_entries: dict) -> list[PsarcData]:
    """Provide a mock PsarcData instance."""
    return PsarcData.from_manifests(
        filename="song1.psarc",
        manifests=[
            mock_psarc_manifest,
            mock_psarc_manifest_no_entries,
        ],
    )
