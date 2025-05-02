# -*- coding: utf-8 -*-
# Project: ConfigGuard
# File: configguard/handlers/toml_handler.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01
# Description: Concrete implementation of StorageHandler for TOML file format.
#              Handles loading and saving configuration data (values-only or full state,
#              including nested structures) to/from TOML files, including optional
#              encryption/decryption. Requires the 'toml' library.

import typing
from collections.abc import Mapping
from pathlib import Path

# Import necessary exceptions and logging from the parent package
from ..exceptions import EncryptionError, HandlerError
from ..log import log
from .base import LoadResult, StorageHandler

# Handle optional 'toml' import
try:
    import toml
except ImportError:
    toml = None  # Define toml as None if the library is not installed


class TomlHandler(StorageHandler):
    """
    Handles loading and saving configuration data in TOML format.

    Supports both saving only configuration values and saving the full state
    (version, schema, values). Also handles encryption/decryption transparently
    if initialized with a Fernet key. Nested configuration structures are
    represented as TOML tables.

    Requires the 'toml' library to be installed (`pip install toml`).
    """

    def __init__(self, fernet: typing.Optional[typing.Any] = None) -> None:
        """
        Initializes the TOML storage handler.

        Args:
            fernet: An optional initialized Fernet instance.

        Raises:
            ImportError: If the 'toml' library is not installed.
        """
        if toml is None:
            log.error("The 'toml' library is required for TomlHandler.")
            log.error("Please install it: pip install toml")
            raise ImportError(
                "TomlHandler requires the 'toml' library. Please install it."
            )
        super().__init__(fernet)

    def load(self, filepath: Path) -> LoadResult:
        """
        Loads configuration from a TOML file, handling decryption if necessary.

        Reads the specified TOML file, decrypts its content if a Fernet key was
        provided, parses the TOML data (which can have nested tables), and
        determines if it represents a 'full' state save or just values.

        Args:
            filepath: The Path object pointing to the TOML configuration file.

        Returns:
            A LoadResult dictionary containing 'version', 'schema', and 'values'.
            The 'values' dictionary can be nested.

        Raises:
            FileNotFoundError: If the file does not exist.
            HandlerError: If the file is not valid TOML, UTF-8, or has an unexpected structure.
            EncryptionError: If decryption fails.
            ImportError: If the 'toml' library is not installed (checked at init).
        """
        log.debug(f"TomlHandler: Attempting to load from: {filepath}")
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        try:
            # 1. Read raw bytes
            raw_data = filepath.read_bytes()
            if not raw_data:
                log.warning(
                    f"TOML configuration file is empty: {filepath}. Returning empty values."
                )
                return {"version": None, "schema": None, "values": {}}

            # 2. Decrypt if needed
            decrypted_bytes: bytes
            if self._fernet:
                log.debug(f"TomlHandler: Decrypting data from {filepath}...")
                try:
                    decrypted_bytes = self._decrypt(raw_data)
                except EncryptionError as e:
                    log.error(f"TomlHandler: Decryption failed for {filepath}: {e}")
                    raise
                log.debug(f"TomlHandler: Decryption successful for {filepath}.")
            else:
                decrypted_bytes = raw_data

            # 3. Decode UTF-8 and parse TOML
            try:
                file_content = decrypted_bytes.decode("utf-8")
                # toml.loads parses the string into a Python dictionary (potentially nested)
                loaded_data = toml.loads(file_content)
            except UnicodeDecodeError as e:
                log.error(
                    f"TomlHandler: UTF-8 decode error in {filepath} after potential decryption: {e}"
                )
                raise HandlerError(
                    f"File {filepath} does not contain valid UTF-8 encoded data."
                ) from e
            except toml.TomlDecodeError as e:
                log.error(f"TomlHandler: TOML decode error in {filepath}: {e}")
                raise HandlerError(f"Invalid TOML structure in {filepath}: {e}") from e
            except Exception as e:
                log.error(
                    f"TomlHandler: Unexpected error during TOML parsing of {filepath}: {e}",
                    exc_info=True,
                )
                raise HandlerError(
                    f"Failed to parse TOML content from {filepath}: {e}"
                ) from e

            # 4. Structure the output
            if isinstance(loaded_data, Mapping):
                # Check for 'full' mode structure
                # Note: TOML doesn't natively support top-level null values easily,
                # so schema might be represented differently if saved 'full'.
                # We assume the 'full' save structure uses specific keys.
                # A common pattern might be to put schema under a specific table.
                # For simplicity matching JSON, we assume top-level keys are used.
                if all(k in loaded_data for k in ("version", "schema", "values")):
                    log.debug(
                        f"TomlHandler: Loaded 'full' structure (version, schema, values) from {filepath}"
                    )
                    loaded_values = loaded_data["values"]
                    loaded_schema = loaded_data["schema"]
                    loaded_version = loaded_data["version"]

                    if not isinstance(loaded_values, Mapping):
                        raise HandlerError(
                            f"Invalid 'values' section in full structure file {filepath} (must be a table/mapping)."
                        )
                    # Schema could be complex; ensure it's a mapping if present
                    if loaded_schema is not None and not isinstance(loaded_schema, Mapping):
                         raise HandlerError(
                            f"Invalid 'schema' section in full structure file {filepath} (must be a table/mapping or missing/null)."
                        )
                    if loaded_version is not None and not isinstance(loaded_version, str):
                        log.warning(f"Version field in {filepath} is not a string. Attempting conversion.")
                        try:
                            loaded_version = str(loaded_version)
                        except Exception:
                             raise HandlerError(f"Could not convert 'version' field in {filepath} to string.")

                    return {
                        "version": loaded_version,
                        "schema": dict(loaded_schema) if loaded_schema else None, # Ensure dict if present
                        "values": dict(loaded_values), # Ensure dict
                    }
                else:
                    # Assume it's just a values dictionary (nested tables are handled)
                    log.debug(
                        f"TomlHandler: Loaded simple values dictionary/mapping from {filepath}"
                    )
                    return {"version": None, "schema": None, "values": dict(loaded_data)} # Ensure dict
            else:
                log.error(
                    f"TomlHandler: Root TOML element in {filepath} is not a table/mapping (found {type(loaded_data).__name__})."
                )
                raise HandlerError(
                    f"Root TOML element in {filepath} must be a table/mapping."
                )

        except (FileNotFoundError, EncryptionError, HandlerError):
            raise
        except Exception as e:
            log.error(
                f"TomlHandler: Unexpected error loading from {filepath}: {e}",
                exc_info=True,
            )
            raise HandlerError(
                f"Unexpected error loading TOML file {filepath}: {e}"
            ) from e

    def save(self, filepath: Path, data: dict, mode: str = "values") -> None:
        """
        Saves configuration data to a TOML file, handling encryption and save modes.

        Serializes the provided data payload to TOML format. Based on the `mode`,
        it either saves the entire structure (version, schema, values) or just
        the values. Nested dictionaries are represented as TOML tables.
        If a Fernet key was provided, the resulting TOML bytes are encrypted.

        Args:
            filepath: The Path object pointing to the target TOML file.
            data: The full data payload from ConfigGuard ('instance_version',
                  'schema_definition', 'config_values').
            mode: 'values' or 'full'.

        Raises:
            HandlerError: If serialization fails, required keys are missing, or file writing fails.
            EncryptionError: If encryption fails.
            ValueError: If an invalid `mode` is provided.
            ImportError: If the 'toml' library is not installed (checked at init).
        """
        log.debug(f"TomlHandler: Saving to: {filepath} (mode: {mode})")

        # 1. Select data structure based on mode
        data_to_serialize: typing.Any
        if mode == "full":
            required_keys = ("instance_version", "schema_definition", "config_values")
            if not all(k in data for k in required_keys):
                missing = [k for k in required_keys if k not in data]
                raise HandlerError(f"Invalid data structure for 'full' save mode. Missing keys: {missing}")

            # TOML requires tables (dictionaries) at the top level.
            # We represent the full structure as distinct top-level keys.
            data_to_serialize = {
                "version": data["instance_version"],
                # Represent schema and values as nested tables
                "schema": data["schema_definition"],
                "values": data["config_values"],
            }
            # Basic check: schema and values should be dictionary-like
            if not isinstance(data_to_serialize["schema"], Mapping):
                 raise HandlerError("'schema_definition' must be a dictionary/mapping for TOML 'full' save.")
            if not isinstance(data_to_serialize["values"], Mapping):
                 raise HandlerError("'config_values' must be a dictionary/mapping for TOML 'full' save.")

            log.debug("TomlHandler: Preparing 'full' data structure for TOML serialization.")

        elif mode == "values":
            if "config_values" not in data:
                raise HandlerError("Invalid data structure for 'values' save mode. Missing 'config_values' key.")
            data_to_serialize = data["config_values"]
            if not isinstance(data_to_serialize, Mapping):
                raise HandlerError("'config_values' must be a dictionary/mapping for 'values' save mode.")
            log.debug("TomlHandler: Preparing 'values'-only data for TOML serialization.")
        else:
            raise ValueError(f"Invalid save mode specified for TomlHandler: '{mode}'. Must be 'values' or 'full'.")

        try:
            # 2. Serialize to TOML string bytes (UTF-8 encoded)
            try:
                # toml.dumps handles nested dictionaries as tables
                toml_string = toml.dumps(data_to_serialize)
                toml_bytes = toml_string.encode("utf-8")
            except TypeError as e:
                log.error(
                    f"TomlHandler: TOML serialization failed. Check for non-serializable types: {e}",
                    exc_info=True,
                )
                raise HandlerError(f"Data cannot be serialized to TOML: {e}") from e
            except Exception as e:
                log.error(f"TomlHandler: Unexpected error during TOML serialization: {e}", exc_info=True)
                raise HandlerError(f"Unexpected TOML serialization error: {e}") from e

            # 3. Encrypt if needed
            bytes_to_write: bytes
            status_log = "(unencrypted)"
            if self._fernet:
                log.debug(f"TomlHandler: Encrypting data for {filepath}...")
                try:
                    bytes_to_write = self._encrypt(toml_bytes)
                except EncryptionError as e:
                    log.error(f"TomlHandler: Encryption failed for {filepath}: {e}")
                    raise
                status_log = "(encrypted)"
                log.debug(f"TomlHandler: Encryption successful for {filepath}.")
            else:
                bytes_to_write = toml_bytes

            # 4. Write bytes to file
            log.debug(f"TomlHandler: Writing {len(bytes_to_write)} bytes to {filepath}")
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(bytes_to_write)
            except IOError as e:
                log.error(f"TomlHandler: File write error for {filepath}: {e}")
                raise HandlerError(f"Failed to write configuration file {filepath}: {e}") from e
            except Exception as e:
                log.error(f"TomlHandler: Unexpected error writing file {filepath}: {e}", exc_info=True)
                raise HandlerError(f"Unexpected error writing file {filepath}: {e}") from e

            log.info(f"TomlHandler: Successfully saved to {filepath} {status_log} (mode: {mode}).")

        except (EncryptionError, HandlerError, ValueError):
            raise
        except Exception as e:
            log.error(f"TomlHandler: Unexpected error saving to {filepath}: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error saving TOML file {filepath}: {e}") from e