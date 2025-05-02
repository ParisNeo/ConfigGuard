# -*- coding: utf-8 -*-
# Project: ConfigGuard
# File: configguard/handlers/sqlite_handler.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01
# Description: Concrete implementation of StorageHandler for SQLite database format.
#              Uses a simple key-value table, storing values as potentially encrypted
#              JSON strings. Handles nested structures via dot notation keys.

import base64
import json
import sqlite3
import typing
from collections.abc import Mapping
from pathlib import Path

# Import necessary exceptions and logging from the parent package
from ..exceptions import EncryptionError, HandlerError
from ..log import log
from .base import LoadResult, StorageHandler

# Define special keys used in the database for full mode
VERSION_DB_KEY = "__configguard_version__"
SCHEMA_DB_KEY = "__configguard_schema__"


class SqliteHandler(StorageHandler):
    """
    Handles loading and saving configuration data to an SQLite database file.

    Uses a simple key-value table (`config`) where keys represent the setting path
    (using dot notation for nesting, e.g., 'section.setting') and values are
    stored as JSON strings.

    If encryption is enabled, the JSON string value is encrypted before being
    stored in the database, and decrypted upon loading.

    Supports both 'values' and 'full' save modes. In 'full' mode, the version
    and schema definition are stored under special keys (`__configguard_version__`
    and `__configguard_schema__`).
    """

    # __init__ is inherited, takes optional fernet

    def _connect(self, filepath: Path) -> sqlite3.Connection:
        """Establish SQLite connection and ensure table exists."""
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(filepath, isolation_level=None) # Autocommit mode
            # Use Write-Ahead Logging for better concurrency (optional but good practice)
            conn.execute("PRAGMA journal_mode=WAL;")
            # Create table if it doesn't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value BLOB
                )
                """
            )
            log.debug(f"SqliteHandler: Connected to DB and ensured 'config' table exists: {filepath}")
            return conn
        except sqlite3.Error as e:
            log.error(f"SqliteHandler: Database connection/setup error for {filepath}: {e}")
            raise HandlerError(f"Failed to connect to or setup SQLite DB {filepath}: {e}") from e

    def _flatten_dict(
        self, nested_dict: Mapping, parent_key: str = "", sep: str = "."
    ) -> typing.Dict[str, typing.Any]:
        """Flattens a nested dictionary into a single level with dot-separated keys."""
        items = {}
        for k, v in nested_dict.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, Mapping):
                items.update(self._flatten_dict(v, new_key, sep=sep))
            else:
                items[new_key] = v
        return items

    def _unflatten_dict(
        self, flat_dict: typing.Dict[str, typing.Any], sep: str = "."
    ) -> dict:
        """Reconstructs a nested dictionary from a flat dictionary with dot-separated keys."""
        unflattened = {}
        for k, v in flat_dict.items():
            parts = k.split(sep)
            d = unflattened
            for i, part in enumerate(parts[:-1]):
                if part not in d:
                    d[part] = {}
                # Handle case where a key conflicts with a path element
                # e.g. having both 'a.b' and 'a' as keys. Prioritize the longer path.
                if not isinstance(d[part], dict):
                     log.warning(f"SqliteHandler: Key conflict during unflattening. Key '{part}' used as section path conflicts with existing value. Overwriting with section structure.")
                     d[part] = {}
                d = d[part]
            # Handle potential conflict at the final key
            final_key = parts[-1]
            if final_key in d and isinstance(d[final_key], dict):
                 log.warning(f"SqliteHandler: Key conflict during unflattening. Key '{final_key}' conflicts with section path. Overwriting section with value.")
            d[final_key] = v
        return unflattened

    def load(self, filepath: Path) -> LoadResult:
        """
        Loads configuration from an SQLite database file.

        Reads the key-value pairs, decrypts values if necessary, parses the
        JSON value strings, and reconstructs the nested configuration structure.
        Checks for special keys to determine if it was a 'full' save.

        Args:
            filepath: The Path object pointing to the SQLite database file.

        Returns:
            A LoadResult dictionary containing 'version', 'schema', and 'values'.

        Raises:
            FileNotFoundError: If the file does not exist (SQLite creates it on connect,
                               so this usually means the *directory* is invalid or permissions issue).
                               We'll check existence first for clarity.
            HandlerError: If database connection, reading, JSON parsing fails, or structure is invalid.
            EncryptionError: If decryption fails.
        """
        log.debug(f"SqliteHandler: Attempting to load from: {filepath}")
        # Check existence explicitly, as connect might create it
        if not filepath.exists():
            log.warning(f"SQLite file not found: {filepath}. Returning empty values.")
            # Return default empty result if file doesn't exist
            return {"version": None, "schema": None, "values": {}}

        conn: typing.Optional[sqlite3.Connection] = None
        try:
            conn = self._connect(filepath)
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM config")
            rows = cursor.fetchall()

            loaded_version: typing.Optional[str] = None
            loaded_schema_str: typing.Optional[str] = None
            flat_values: typing.Dict[str, typing.Any] = {}

            for key, value_blob in rows:
                decrypted_bytes: bytes
                try:
                    # Decrypt blob if needed
                    if self._fernet:
                        if not value_blob: # Handle potential NULL blobs if saving went wrong
                            log.warning(f"SqliteHandler: Found NULL value blob for key '{key}' in encrypted DB. Skipping.")
                            continue
                        decrypted_bytes = self._decrypt(value_blob)
                    else:
                        if not value_blob: # Handle potential NULL blobs
                            log.warning(f"SqliteHandler: Found NULL value blob for key '{key}'. Assuming JSON 'null'.")
                            decrypted_bytes = b'null' # Treat as JSON null if not encrypted
                        else:
                            decrypted_bytes = value_blob

                    # Decode UTF-8 and parse JSON value string
                    value_str = decrypted_bytes.decode("utf-8")
                    parsed_value = json.loads(value_str)

                    # Check for special keys
                    if key == VERSION_DB_KEY:
                        if isinstance(parsed_value, str):
                            loaded_version = parsed_value
                        else:
                            log.warning(f"SqliteHandler: Invalid type for version key '{VERSION_DB_KEY}'. Expected string, got {type(parsed_value).__name__}.")
                    elif key == SCHEMA_DB_KEY:
                         # Store the raw JSON string for schema first
                         loaded_schema_str = value_str
                    else:
                        # Regular configuration key
                        flat_values[key] = parsed_value

                except UnicodeDecodeError as e:
                    log.error(f"SqliteHandler: UTF-8 decode error for key '{key}': {e}")
                    raise HandlerError(f"Invalid UTF-8 data in DB for key '{key}'.") from e
                except json.JSONDecodeError as e:
                    log.error(f"SqliteHandler: JSON decode error for key '{key}': {e}")
                    raise HandlerError(f"Invalid JSON data in DB for key '{key}'.") from e
                except EncryptionError as e:
                    # Log specific key causing decryption error
                    log.error(f"SqliteHandler: Decryption failed for key '{key}': {e}")
                    raise EncryptionError(f"Decryption failed for key '{key}' in DB.") from e
                except Exception as e:
                     log.error(f"SqliteHandler: Unexpected error processing key '{key}': {e}", exc_info=True)
                     raise HandlerError(f"Unexpected error processing key '{key}' from DB.") from e


            # Parse schema string if found
            loaded_schema: typing.Optional[dict] = None
            if loaded_schema_str:
                try:
                    parsed_schema = json.loads(loaded_schema_str)
                    if isinstance(parsed_schema, dict):
                        loaded_schema = parsed_schema
                    else:
                        log.warning(f"SqliteHandler: Invalid type for schema key '{SCHEMA_DB_KEY}'. Expected JSON object, got {type(parsed_schema).__name__}.")
                except json.JSONDecodeError as e:
                    log.error(f"SqliteHandler: JSON decode error for schema key '{SCHEMA_DB_KEY}': {e}")
                    # Continue without schema, but log error
                except Exception as e:
                    log.error(f"SqliteHandler: Unexpected error parsing schema for key '{SCHEMA_DB_KEY}': {e}", exc_info=True)


            # Reconstruct nested dictionary from flat values
            values_dict = self._unflatten_dict(flat_values)

            log.debug(f"SqliteHandler: Load successful from {filepath}. Version='{loaded_version}', Schema loaded={'Yes' if loaded_schema else 'No'}.")
            return {
                "version": loaded_version,
                "schema": loaded_schema,
                "values": values_dict,
            }

        except sqlite3.Error as e:
            log.error(f"SqliteHandler: Database error loading from {filepath}: {e}")
            raise HandlerError(f"SQLite error loading configuration: {e}") from e
        except (EncryptionError, HandlerError):
            raise # Re-raise specific errors
        except Exception as e:
            log.error(f"SqliteHandler: Unexpected error loading from {filepath}: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error loading SQLite file {filepath}: {e}") from e
        finally:
            if conn:
                conn.close()
                log.debug(f"SqliteHandler: Closed DB connection: {filepath}")


    def save(self, filepath: Path, data: dict, mode: str = "values") -> None:
        """
        Saves configuration data to an SQLite database file.

        Flattens nested structures using dot notation keys, serializes values
        to JSON strings, encrypts the JSON string if needed, and stores key-value
        pairs in the 'config' table. Handles 'full' mode by saving special keys.

        Args:
            filepath: The Path object pointing to the target SQLite database file.
            data: The full data payload from ConfigGuard.
            mode: 'values' or 'full'.

        Raises:
            HandlerError: If database connection, serialization, or writing fails.
            EncryptionError: If encryption fails.
            ValueError: If an invalid `mode` is provided.
        """
        log.debug(f"SqliteHandler: Saving to: {filepath} (mode: {mode})")

        # 1. Get values dict based on mode
        values_to_save: Mapping
        if mode == "full":
            required_keys = ("instance_version", "schema_definition", "config_values")
            if not all(k in data for k in required_keys):
                missing = [k for k in required_keys if k not in data]
                raise HandlerError(f"Invalid data structure for 'full' save mode. Missing keys: {missing}")
            values_to_save = data["config_values"]
            if not isinstance(values_to_save, Mapping):
                 raise HandlerError("'config_values' must be a dictionary/mapping for 'full' save mode.")
            log.debug("SqliteHandler: Preparing 'full' data for SQLite save.")
        elif mode == "values":
            if "config_values" not in data:
                raise HandlerError("Invalid data structure for 'values' save mode. Missing 'config_values' key.")
            values_to_save = data["config_values"]
            if not isinstance(values_to_save, Mapping):
                raise HandlerError("'config_values' must be a dictionary/mapping for 'values' save mode.")
            log.debug("SqliteHandler: Preparing 'values'-only data for SQLite save.")
        else:
            raise ValueError(f"Invalid save mode specified for SqliteHandler: '{mode}'. Must be 'values' or 'full'.")

        conn: typing.Optional[sqlite3.Connection] = None
        try:
            conn = self._connect(filepath)
            cursor = conn.cursor()

            # Flatten the dictionary to get dot-notation keys
            flat_values = self._flatten_dict(values_to_save)

            # Prepare data for insertion (key, encrypted_json_blob)
            items_to_insert: typing.List[typing.Tuple[str, bytes]] = []

            # Add special keys for 'full' mode
            if mode == "full":
                try:
                    # Version (serialize just the string to JSON)
                    version_json = json.dumps(data["instance_version"]).encode("utf-8")
                    version_blob = self._encrypt(version_json) if self._fernet else version_json
                    items_to_insert.append((VERSION_DB_KEY, version_blob))

                    # Schema (serialize the dict to JSON)
                    schema_json = json.dumps(data["schema_definition"]).encode("utf-8")
                    schema_blob = self._encrypt(schema_json) if self._fernet else schema_json
                    items_to_insert.append((SCHEMA_DB_KEY, schema_blob))
                except TypeError as e:
                     log.error(f"SqliteHandler: Failed to serialize version or schema for 'full' mode: {e}")
                     raise HandlerError(f"Cannot serialize version/schema to JSON: {e}") from e
                except EncryptionError as e:
                     log.error(f"SqliteHandler: Failed to encrypt version or schema for 'full' mode: {e}")
                     raise
                except Exception as e:
                     log.error(f"SqliteHandler: Unexpected error preparing metadata for 'full' mode: {e}", exc_info=True)
                     raise HandlerError("Unexpected error preparing metadata for 'full' mode.") from e


            # Process regular config values
            for key, value in flat_values.items():
                try:
                    # Serialize value to JSON string bytes
                    value_json_bytes = json.dumps(value).encode("utf-8")

                    # Encrypt the JSON bytes if needed
                    value_blob: bytes
                    if self._fernet:
                        value_blob = self._encrypt(value_json_bytes)
                    else:
                        value_blob = value_json_bytes

                    items_to_insert.append((key, value_blob))

                except TypeError as e:
                    log.error(f"SqliteHandler: JSON serialization failed for key '{key}': {e}", exc_info=True)
                    raise HandlerError(f"Data for key '{key}' cannot be serialized to JSON: {e}") from e
                except EncryptionError as e:
                    log.error(f"SqliteHandler: Encryption failed for key '{key}': {e}")
                    raise # Re-raise specific error
                except Exception as e:
                    log.error(f"SqliteHandler: Unexpected error processing key '{key}' for save: {e}", exc_info=True)
                    raise HandlerError(f"Unexpected error processing key '{key}'.") from e

            # Perform database operations within a transaction
            try:
                conn.execute("BEGIN")
                # Clear existing data *only* if saving values-only (full save implies replacing all)
                # Or maybe always clear? Let's always clear for simplicity.
                # If only saving 'values', we might leave old schema/version keys.
                # Safest is to clear all and insert fresh.
                log.debug("SqliteHandler: Clearing existing config table data.")
                cursor.execute("DELETE FROM config")

                # Insert new data
                log.debug(f"SqliteHandler: Inserting/Replacing {len(items_to_insert)} items.")
                cursor.executemany("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", items_to_insert)
                conn.commit()
                log.info(f"SqliteHandler: Successfully saved to {filepath} (mode: {mode}).")

            except sqlite3.Error as e:
                conn.rollback()
                log.error(f"SqliteHandler: Database transaction error during save: {e}")
                raise HandlerError(f"SQLite transaction error during save: {e}") from e

        except sqlite3.Error as e:
            log.error(f"SqliteHandler: Database error saving to {filepath}: {e}")
            raise HandlerError(f"SQLite error saving configuration: {e}") from e
        except (EncryptionError, HandlerError, ValueError):
            raise # Re-raise specific errors
        except Exception as e:
            log.error(f"SqliteHandler: Unexpected error saving to {filepath}: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error saving SQLite file {filepath}: {e}") from e
        finally:
            if conn:
                conn.close()
                log.debug(f"SqliteHandler: Closed DB connection: {filepath}")