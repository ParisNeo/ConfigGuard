# Project: ConfigGuard
# File: configguard/handlers/json_handler.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Verified for nesting support)
# Description: Concrete implementation of StorageHandler for JSON file format.
#              Handles loading and saving configuration data (values-only or full state,
#              including nested structures) to/from JSON files, including optional
#              encryption/decryption.

import json
import typing
from collections.abc import Mapping  # Use Mapping for type hint flexibility
from pathlib import Path

from ..exceptions import EncryptionError, HandlerError
from ..log import log
from .base import LoadResult, StorageHandler


class JsonHandler(StorageHandler):
    """
    Handles loading and saving configuration data in JSON format.

    Supports both saving only configuration values and saving the full state
    (version, schema, values). Also handles encryption/decryption transparently
    if initialized with a Fernet key. Nested configuration structures are
    handled naturally by the JSON format.
    """

    # __init__ is inherited from StorageHandler, takes optional fernet

    def load(self, filepath: Path) -> LoadResult:
        """
        Loads configuration from a JSON file, handling decryption if necessary.

        Reads the specified JSON file, decrypts its content if a Fernet key was
        provided, parses the JSON data (which can be nested), and determines
        if it represents a 'full' state save (with version/schema) or just
        configuration values.

        Args:
            filepath: The Path object pointing to the JSON configuration file.

        Returns:
            A LoadResult dictionary containing 'version', 'schema', and 'values'.
            The 'values' dictionary can be nested.

        Raises:
            FileNotFoundError: If the file does not exist.
            HandlerError: If the file is not valid JSON, UTF-8, or has an unexpected structure.
            EncryptionError: If decryption fails.
        """
        log.debug(f"JsonHandler: Attempting to load from: {filepath}")
        if not filepath.exists():
            # Let FileNotFoundError propagate up as per StorageHandler spec
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        try:
            # 1. Read raw bytes from the file
            raw_data = filepath.read_bytes()
            if not raw_data:
                log.warning(
                    f"JSON configuration file is empty: {filepath}. Returning empty values."
                )
                # Return default empty result for an empty file
                return {"version": None, "schema": None, "values": {}}

            # 2. Decrypt if a Fernet instance is available
            decrypted_bytes: bytes
            if self._fernet:
                log.debug(f"JsonHandler: Decrypting data from {filepath}...")
                try:
                    decrypted_bytes = self._decrypt(raw_data)
                except EncryptionError as e:
                    log.error(f"JsonHandler: Decryption failed for {filepath}: {e}")
                    raise  # Re-raise specific error
                log.debug(f"JsonHandler: Decryption successful for {filepath}.")
            else:
                decrypted_bytes = raw_data

            # 3. Decode UTF-8 and parse JSON
            try:
                file_content = decrypted_bytes.decode("utf-8")
                # The loaded_data can be a nested dictionary if the JSON contains nested objects
                loaded_data = json.loads(file_content)
            except UnicodeDecodeError as e:
                log.error(
                    f"JsonHandler: UTF-8 decode error in {filepath} after potential decryption: {e}"
                )
                raise HandlerError(
                    f"File {filepath} does not contain valid UTF-8 encoded data."
                ) from e
            except json.JSONDecodeError as e:
                log.error(f"JsonHandler: JSON decode error in {filepath}: {e}")
                raise HandlerError(f"Invalid JSON structure in {filepath}: {e}") from e
            except Exception as e:
                log.error(
                    f"JsonHandler: Unexpected error during JSON parsing of {filepath}: {e}",
                    exc_info=True,
                )
                raise HandlerError(
                    f"Failed to parse JSON content from {filepath}: {e}"
                ) from e

            # 4. Structure the output based on loaded data structure
            if isinstance(
                loaded_data, Mapping
            ):  # Check if it's a dictionary-like object
                # Check if it looks like the 'full' structure saved by save(mode='full')
                if all(k in loaded_data for k in ("version", "schema", "values")):
                    log.debug(
                        f"JsonHandler: Loaded 'full' structure (version, schema, values) from {filepath}"
                    )
                    # Perform basic type validation on the structure elements
                    loaded_values = loaded_data["values"]
                    loaded_schema = loaded_data["schema"]
                    loaded_version = loaded_data["version"]

                    # Values should be a dictionary/mapping (can be nested)
                    if not isinstance(loaded_values, Mapping):
                        raise HandlerError(
                            f"Invalid 'values' section in full structure file {filepath} (must be a dictionary/mapping)."
                        )
                    # Schema should be a dictionary/mapping or None (can be nested)
                    if loaded_schema is not None and not isinstance(
                        loaded_schema, Mapping
                    ):
                        raise HandlerError(
                            f"Invalid 'schema' section in full structure file {filepath} (must be a dictionary/mapping or null)."
                        )
                    # Version can be None or string
                    if loaded_version is not None and not isinstance(
                        loaded_version, str
                    ):
                        log.warning(
                            f"Version field in {filepath} is not a string (type: {type(loaded_version).__name__}). Attempting conversion."
                        )
                        try:
                            loaded_version = str(loaded_version)
                        except Exception:
                            raise HandlerError(
                                f"Could not convert 'version' field in {filepath} to string."
                            )

                    return {
                        "version": loaded_version,
                        "schema": loaded_schema,  # Can be nested dict
                        "values": loaded_values,  # Can be nested dict
                    }
                else:
                    # Assume it's just a values dictionary (legacy or saved with mode='values')
                    # This dictionary can be nested if the original JSON was nested.
                    log.debug(
                        f"JsonHandler: Loaded simple values dictionary/mapping from {filepath}"
                    )
                    return {
                        "version": None,
                        "schema": None,
                        "values": dict(loaded_data),
                    }  # Ensure it's a dict
            else:
                # If the top level isn't a dict/mapping, it's an invalid format
                log.error(
                    f"JsonHandler: Root JSON element in {filepath} is not a dictionary/mapping (found {type(loaded_data).__name__})."
                )
                raise HandlerError(
                    f"Root JSON element in {filepath} must be a dictionary/mapping."
                )

        except (FileNotFoundError, EncryptionError, HandlerError):
            # Re-raise known, handled errors
            raise
        except Exception as e:
            # Catch unexpected errors during file IO or processing
            log.error(
                f"JsonHandler: Unexpected error loading from {filepath}: {e}",
                exc_info=True,
            )
            raise HandlerError(
                f"Unexpected error loading JSON file {filepath}: {e}"
            ) from e

    def save(self, filepath: Path, data: dict, mode: str = "values") -> None:
        """
        Saves configuration data to a JSON file, handling encryption and save modes.

        Serializes the provided data payload to JSON. Based on the `mode`, it either
        saves the entire structure (version, schema, values) or just the values.
        Nested structures within 'schema' or 'values' are handled correctly by `json.dumps`.
        If a Fernet key was provided at initialization, the resulting JSON bytes
        are encrypted before writing to the file.

        Args:
            filepath: The Path object pointing to the target JSON file.
                      Parent directories will be created if they don't exist.
            data: The full data payload from ConfigGuard, containing keys
                  'instance_version', 'schema_definition', and 'config_values'.
                  'schema_definition' and 'config_values' can be nested dictionaries.
            mode: 'values' to save only `data['config_values']`.
                  'full' to save a JSON object with 'version', 'schema', and 'values' keys
                  using the corresponding data from the payload.

        Raises:
            HandlerError: If serialization fails or required data keys are missing
                          in the `data` payload for the specified `mode`. Also raised
                          for file writing errors.
            EncryptionError: If encryption fails.
            ValueError: If an invalid `mode` is provided.
        """
        log.debug(f"JsonHandler: Saving to: {filepath} (mode: {mode})")

        # 1. Select data structure to serialize based on mode
        data_to_serialize: typing.Any
        if mode == "full":
            required_keys = ("instance_version", "schema_definition", "config_values")
            if not all(k in data for k in required_keys):
                missing = [k for k in required_keys if k not in data]
                log.error(
                    f"JsonHandler: Invalid data structure provided for 'full' save mode. Missing keys: {missing}"
                )
                raise HandlerError(
                    f"Invalid data structure provided for 'full' save mode. Missing keys: {missing}"
                )
            # Construct the specific JSON structure for 'full' mode
            # The schema_definition and config_values can be nested dicts
            data_to_serialize = {
                "version": data["instance_version"],
                "schema": data["schema_definition"],
                "values": data["config_values"],
            }
            log.debug(
                "JsonHandler: Preparing 'full' data structure for JSON serialization."
            )
        elif mode == "values":
            if "config_values" not in data:
                log.error(
                    "JsonHandler: Invalid data structure provided for 'values' save mode. Missing 'config_values' key."
                )
                raise HandlerError(
                    "Invalid data structure provided for 'values' save mode. Missing 'config_values' key."
                )
            # Use only the values dictionary for serialization (can be nested)
            data_to_serialize = data["config_values"]
            # Ensure it's a dictionary-like structure
            if not isinstance(data_to_serialize, Mapping):
                log.error(
                    f"JsonHandler: 'config_values' in data payload is not a dictionary/mapping (type: {type(data_to_serialize).__name__}) for 'values' mode."
                )
                raise HandlerError(
                    "'config_values' must be a dictionary/mapping for 'values' save mode."
                )
            log.debug(
                "JsonHandler: Preparing 'values'-only data for JSON serialization."
            )
        else:
            raise ValueError(
                f"Invalid save mode specified for JsonHandler: '{mode}'. Must be 'values' or 'full'."
            )

        try:
            # 2. Serialize the selected data structure to JSON bytes (UTF-8 encoded)
            try:
                # json.dumps handles nested dictionaries correctly
                json_bytes = json.dumps(
                    data_to_serialize, indent=4, ensure_ascii=False
                ).encode("utf-8")
            except TypeError as e:
                log.error(
                    f"JsonHandler: JSON serialization failed. Check for non-serializable types in config values or schema: {e}",
                    exc_info=True,
                )
                raise HandlerError(f"Data cannot be serialized to JSON: {e}") from e
            except Exception as e:
                log.error(
                    f"JsonHandler: Unexpected error during JSON serialization: {e}",
                    exc_info=True,
                )
                raise HandlerError(f"Unexpected JSON serialization error: {e}") from e

            # 3. Encrypt the JSON bytes if a Fernet instance is available
            bytes_to_write: bytes
            status_log = "(unencrypted)"
            if self._fernet:
                log.debug(f"JsonHandler: Encrypting data for {filepath}...")
                try:
                    bytes_to_write = self._encrypt(json_bytes)
                except EncryptionError as e:
                    log.error(f"JsonHandler: Encryption failed for {filepath}: {e}")
                    raise  # Re-raise specific error
                status_log = "(encrypted)"
                log.debug(f"JsonHandler: Encryption successful for {filepath}.")
            else:
                bytes_to_write = json_bytes

            # 4. Write the final bytes (encrypted or plain) to the file
            log.debug(f"JsonHandler: Writing {len(bytes_to_write)} bytes to {filepath}")
            try:
                # Ensure parent directory exists before attempting to write
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(bytes_to_write)
            except OSError as e:
                log.error(f"JsonHandler: File write error for {filepath}: {e}")
                raise HandlerError(
                    f"Failed to write configuration file {filepath}: {e}"
                ) from e
            except Exception as e:
                log.error(
                    f"JsonHandler: Unexpected error writing file {filepath}: {e}",
                    exc_info=True,
                )
                raise HandlerError(
                    f"Unexpected error writing file {filepath}: {e}"
                ) from e

            log.info(
                f"JsonHandler: Successfully saved to {filepath} {status_log} (mode: {mode})."
            )

        except (EncryptionError, HandlerError, ValueError):
            # Re-raise known, handled errors
            raise
        except Exception as e:
            # Catch unexpected errors during IO or processing
            log.error(
                f"JsonHandler: Unexpected error saving to {filepath}: {e}",
                exc_info=True,
            )
            raise HandlerError(
                f"Unexpected error saving JSON file {filepath}: {e}"
            ) from e
