"""
Database utilities for persisting upload metadata into PostgreSQL.

Assumptions:
- A table named `metadata` already exists with columns:
  unique_id (uuid, default gen_random_uuid()), uploaded_at (timestamp, default current_timestamp),
  file_name (varchar), storage_path (text).
- Connection settings are provided via environment variables (see defaults below).
"""
from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Iterable, Optional

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from src.models.api_models import METADATA_DIR, MetadataRecord

LOGGER = logging.getLogger(__name__)

# Environment-driven connection settings with safe defaults for local dev.
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")


def _connect():
    """Create a new psycopg connection."""
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )

# def _connect():
#     """Create a new psycopg connection."""
#     try:
#         conn = psycopg.connect(
#             host=DB_HOST,
#             port=DB_PORT,
#             dbname=DB_NAME,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             row_factory=dict_row,
#         )
#         print("Connection successful!")
#         return conn
#     except Exception as e:
#         print("Connection failed:", e)
#         raise


def parse_metadata_file(path: Path) -> Optional[MetadataRecord]:
    """
    Parse a single metadata .txt file into a MetadataRecord.
    Expected format (key=value per line):
      unique_id=<uuid>
      file_name=<name>
      storage_path=<path>
      uploaded_at=<iso timestamp>
    """
    try:
        content = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.error("Failed to read metadata file %s: %s", path, exc)
        return None

    data = {}
    for line in content:
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        data[key.strip()] = val.strip()

    required_keys = {"unique_id", "file_name", "storage_path", "uploaded_at"}
    if not required_keys.issubset(data):
        LOGGER.warning("Skipping metadata file %s due to missing keys", path)
        return None

    try:
        return MetadataRecord(
            unique_id=data["unique_id"],
            file_name=data["file_name"],
            storage_path=data["storage_path"],
            uploaded_at=data["uploaded_at"],
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.error("Failed to parse metadata file %s: %s", path, exc)
        return None


def load_metadata_from_dir(directory: Path = METADATA_DIR) -> list[MetadataRecord]:
    """Load all .txt metadata files from the given directory."""
    records: list[MetadataRecord] = []
    if not directory.exists():
        LOGGER.info("Metadata directory %s does not exist yet", directory)
        return records

    for file in directory.glob("*.txt"):
        record = parse_metadata_file(file)
        if record:
            records.append(record)
    return records


def insert_metadata_records(records: Iterable[MetadataRecord]) -> int:
    """
    Insert metadata records into the `Metadata` table.
    Skips records that already exist (based on unique_id).

    Returns the number of rows actually inserted (excluding conflicts).
    """
    records = list(records)
    if not records:
        return 0

    query = sql.SQL(
        """
        INSERT INTO "metadata" (unique_id, uploaded_at, file_name, storage_path)
        VALUES (%(unique_id)s, %(uploaded_at)s, %(file_name)s, %(storage_path)s)
        ON CONFLICT (unique_id) DO NOTHING
        """
    )

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, [r.model_dump() for r in records])
            rows_inserted = cur.rowcount
        conn.commit()
    LOGGER.info("Inserted %d metadata records (attempted %d)", rows_inserted, len(records))
    return rows_inserted


def sync_metadata_directory_to_db(directory: Path = METADATA_DIR) -> int:
    """
    Convenience helper: load all metadata files from disk and insert into DB.

    Intended to be called for each request that passes rate limiting.
    """
    records = load_metadata_from_dir(directory)
    return insert_metadata_records(records)

