"""PSARC file module."""

import json
import logging
import os
import struct
import zlib
from io import BufferedReader
from pathlib import Path

import numpy as np
from Crypto.Cipher import AES

from psarc_library.constants import PSARC_TOC_DECRYPTION_KEY_ENV_VAR
from psarc_library.models import PsarcHeader, PsarcTocEntry

logger = logging.getLogger(__name__)

if not (_psarc_key := os.getenv(PSARC_TOC_DECRYPTION_KEY_ENV_VAR)):
    error_msg = f"Environment variable not set: {PSARC_TOC_DECRYPTION_KEY_ENV_VAR}"
    logger.exception(error_msg)
    raise SystemExit(error_msg)

_PSARC_KEY = bytes.fromhex(_psarc_key)
_PSARC_HEADER_SIZE = 32
_PSARC_MAGIC = b"PSAR"

_TOC_MAX_COUNT = 100000
_ARCHIVE_FLAG_ENCRYPTED_TOC = 4


def check_header_magic(header_raw: bytes) -> bool:
    """Check if the header magic is valid."""
    return header_raw[0:4] == _PSARC_MAGIC


def unpack_header(header_raw: bytes) -> PsarcHeader:
    """Unpack the PSARC header into a PsarcHeader model."""
    return PsarcHeader(
        toc_length=struct.unpack(">I", header_raw[12:16])[0],
        toc_entry_size=struct.unpack(">I", header_raw[16:20])[0],
        toc_count=struct.unpack(">I", header_raw[20:24])[0],
        block_size=struct.unpack(">I", header_raw[24:28])[0],
        archive_flags=struct.unpack(">I", header_raw[28:32])[0],
    )


def validate_toc_count(toc_count: int) -> bool:
    """Validate the TOC count."""
    return toc_count > 0 and toc_count <= _TOC_MAX_COUNT


def decrypt_toc(toc_raw: bytes) -> bytes:
    """Decrypt the TOC if it is encrypted."""
    cipher = AES.new(_PSARC_KEY, AES.MODE_CFB, bytes(16), segment_size=128)
    return cipher.decrypt(toc_raw)


def parse_toc_entries(toc_raw: bytes, toc_entry_size: int, toc_count: int) -> list[PsarcTocEntry]:
    """Parse TOC entries from the raw TOC data."""
    toc_entries: list[PsarcTocEntry] = []
    for i in range(toc_count):
        entry_raw = toc_raw[i * toc_entry_size : (i + 1) * toc_entry_size]
        if len(entry_raw) < toc_entry_size:
            break
        zindex = struct.unpack(">I", entry_raw[16:20])[0]
        length = int.from_bytes(entry_raw[20:25], "big")
        offset = int.from_bytes(entry_raw[25:30], "big")
        toc_entries.append(PsarcTocEntry(zindex=zindex, length=length, offset=offset))
    return toc_entries


def parse_block_length_table(block_table: bytes, blen_size: int) -> list[int]:
    """Parse the block length table from the TOC data."""
    block_lengths = []
    for i in range(len(block_table) // blen_size):
        val = int.from_bytes(block_table[i * blen_size : (i + 1) * blen_size], "big")
        block_lengths.append(val)
    return block_lengths


def decompress_entry(
    file: BufferedReader, entry: PsarcTocEntry, block_lengths: list[int], unpacked_header: PsarcHeader
) -> bytes:
    """Decompress a file entry from the PSARC data blocks."""
    if entry.length == 0:
        return b""

    file.seek(entry.offset)
    result = bytearray()
    zi = entry.zindex
    remaining_len = entry.length
    while remaining_len > 0:
        if zi >= len(block_lengths):
            result.extend(file.read(remaining_len))
            break
        blen = block_lengths[zi]
        zi += 1
        if blen == 0:
            chunk = file.read(min(unpacked_header.block_size, remaining_len))
            result.extend(chunk)
            remaining_len -= len(chunk)
        else:
            compressed = file.read(blen)
            try:
                dec = zlib.decompress(compressed)
                result.extend(dec)
                remaining_len -= len(dec)
            except zlib.error:
                result.extend(compressed)
                remaining_len -= len(compressed)
    return bytes(result)


def parse_psarc(filepath: Path) -> list[dict]:
    """Extract manifest JSON files from a psarc and return song metadata."""
    with filepath.open("rb") as file:
        header_raw = file.read(_PSARC_HEADER_SIZE)
        if len(header_raw) < _PSARC_HEADER_SIZE:
            return []

        if not check_header_magic(header_raw):
            return []

        if not validate_toc_count((unpacked_header := unpack_header(header_raw)).toc_count):
            return []

        toc_raw = file.read(unpacked_header.toc_length - _PSARC_HEADER_SIZE)

        if unpacked_header.archive_flags == _ARCHIVE_FLAG_ENCRYPTED_TOC:
            toc_raw = decrypt_toc(toc_raw)

        if not (toc_entries := parse_toc_entries(toc_raw, unpacked_header.toc_entry_size, unpacked_header.toc_count)):
            return []

        block_table = toc_raw[unpacked_header.toc_count * unpacked_header.toc_entry_size :]
        blen_size = int(np.log(unpacked_header.block_size) / np.log(256))
        block_lengths = parse_block_length_table(block_table, blen_size)

        if not (filelist_data := decompress_entry(file, toc_entries[0], block_lengths, unpacked_header)):
            return []

        paths = filelist_data.decode("utf-8", errors="ignore").split("\n")

        manifests = []
        for i, path in enumerate(paths):
            if not (cleaned_path := path.strip("\x00").strip()):
                continue

            if "manifests" in cleaned_path.lower() and cleaned_path.endswith(".json"):
                if (entry_idx := i + 1) < len(toc_entries):
                    if data := decompress_entry(file, toc_entries[entry_idx], block_lengths, unpacked_header):
                        manifests.append(json.loads(data.decode("utf-8", errors="ignore")))

    return manifests
