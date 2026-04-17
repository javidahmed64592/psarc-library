"""Unit tests for the psarc_library.models module."""

import pytest

from psarc_library.models import (
    PsarcData,
    PsarcHeader,
    PsarcLibraryServerConfig,
    PsarcTocEntry,
    SongData,
    Tuning,
    TuningDict,
    TuningRoots,
    TuningType,
)


# PSARC Library Server Configuration Models
class TestPsarcLibraryServerConfig:
    """Unit tests for the PsarcLibraryServerConfig class."""

    def test_model_dump(
        self,
        mock_psarc_library_server_config: PsarcLibraryServerConfig,
    ) -> None:
        """Test the model_dump method."""
        assert isinstance(mock_psarc_library_server_config.model_dump(), dict)


# PSARC Models
class TestTuningRoots:
    """Unit tests for the TuningRoots enumeration."""

    @pytest.mark.parametrize(
        ("offset", "expected_root"),
        [
            (0, TuningRoots.E),
            (-1, TuningRoots.E_FLAT),
            (-2, TuningRoots.D),
            (-3, TuningRoots.D_FLAT),
            (-4, TuningRoots.C),
            (-5, TuningRoots.B),
            (-6, TuningRoots.B_FLAT),
            (-7, TuningRoots.A),
            (-8, TuningRoots.A_FLAT),
            (-9, TuningRoots.G),
            (-10, TuningRoots.G_FLAT),
            (-11, TuningRoots.F),
        ],
    )
    def test_from_semitone_offset(self, offset: int, expected_root: TuningRoots) -> None:
        """Test the from_semitone_offset method."""
        assert TuningRoots.from_semitone_offset(offset) == expected_root


class TestTuningType:
    """Unit tests for the TuningType enumeration."""

    @pytest.mark.parametrize(
        ("tuning_type", "expected_value"),
        [
            (TuningType.STANDARD, "Standard"),
            (TuningType.DROP, "Drop"),
            (TuningType.CUSTOM, "Custom"),
        ],
    )
    def test_values(self, tuning_type: TuningType, expected_value: str) -> None:
        """Test the values of the TuningType enumeration."""
        assert tuning_type == expected_value


class TestTuningDict:
    """Unit tests for the TuningDict model."""

    def test_tuning_type(
        self,
        mock_tuning_dict_standard: TuningDict,
        mock_tuning_dict_drop: TuningDict,
        mock_tuning_dict_custom: TuningDict,
    ) -> None:
        """Test the tuning_type property."""
        assert mock_tuning_dict_standard.tuning_type == TuningType.STANDARD
        assert mock_tuning_dict_drop.tuning_type == TuningType.DROP
        assert mock_tuning_dict_custom.tuning_type == TuningType.CUSTOM


class TestTuning:
    """Unit tests for the Tuning model."""

    def test_from_tuning_dict(
        self,
        mock_tuning_standard: Tuning,
        mock_tuning_drop: Tuning,
        mock_tuning_custom: Tuning,
    ) -> None:
        """Test the from_tuning_dict method."""
        assert mock_tuning_standard.root == TuningRoots.E
        assert mock_tuning_standard.type == TuningType.STANDARD

        assert mock_tuning_drop.root == TuningRoots.D
        assert mock_tuning_drop.type == TuningType.DROP

        assert mock_tuning_custom.root == TuningRoots.D
        assert mock_tuning_custom.type == TuningType.CUSTOM


class TestSongData:
    """Unit tests for the SongData model."""

    def test_model_dump(self, mock_song_data: SongData, mock_song_data_entry: dict) -> None:
        """Test the model_dump method."""
        song_data_dict = mock_song_data.model_dump()
        assert isinstance(song_data_dict, dict)
        assert song_data_dict["title"] == mock_song_data_entry["Attributes"]["SongName"]
        assert song_data_dict["artist"] == mock_song_data_entry["Attributes"]["ArtistName"]
        assert song_data_dict["album"] == mock_song_data_entry["Attributes"]["AlbumName"]
        assert song_data_dict["year"] == mock_song_data_entry["Attributes"]["SongYear"]
        assert song_data_dict["tuning"]["root"] == TuningRoots.E
        assert song_data_dict["tuning"]["type"] == TuningType.STANDARD
        assert song_data_dict["length"] == mock_song_data_entry["Attributes"]["SongLength"]
        assert song_data_dict["tempo"] == mock_song_data_entry["Attributes"]["SongAverageTempo"]
        assert song_data_dict["dlc"] == mock_song_data_entry["Attributes"]["DLC"]
        assert song_data_dict["dlc_key"] == mock_song_data_entry["Attributes"]["DLCKey"]


class TestPsarcData:
    """Unit tests for the PsarcData model."""

    def test_model_dump(self, mock_psarc_data: list[PsarcData]) -> None:
        """Test the model_dump method."""
        for psarc_data in mock_psarc_data:
            assert isinstance(psarc_data.model_dump(), dict)


# PSARC File Models
class TestPsarcHeader:
    """Unit tests for the PsarcHeader model."""

    def test_model_dump(self, mock_psarc_header: PsarcHeader) -> None:
        """Test the model_dump method."""
        assert isinstance(mock_psarc_header.model_dump(), dict)


class TestPsarcTocEntry:
    """Unit tests for the PsarcTocEntry model."""

    def test_model_dump(self, mock_psarc_toc_entry: PsarcTocEntry) -> None:
        """Test the model_dump method."""
        assert isinstance(mock_psarc_toc_entry.model_dump(), dict)


# API Response Models
