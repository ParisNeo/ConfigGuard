# -*- coding: utf-8 -*-
# Project: ConfigGuard
# File: configguard/handlers/yaml_handler.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01
# Description: Concrete implementation of StorageHandler for YAML file format.
#              Handles loading and saving configuration data (values-only or full state,
#              including nested structures) to/from YAML files, including optional
#              encryption/decryption. Requires the 'PyYAML' library.

import typing
from collections.abc import Mapping
from pathlib import Path

# Import necessary exceptions and logging from the parent package
from ..exceptions import EncryptionError, HandlerError
from ..log import log
from .base import LoadResult, StorageHandler

# Handle optional 'yaml' import
try:
    import yaml
except ImportError:
    yaml = None  # Define yaml as None if the library is not installed


class YamlHandler(StorageHandler):
    """
    Handles loading and saving configuration data in YAML format.

    Supports both saving only configuration values and saving the full state
    (version, schema, values). Also handles encryption/decryption transparently
    if initialized with a Fernet key. Nested configuration structures are
    handled naturally by YAML.

    Requires the 'PyYAML' library to be installed (`pip install pyyaml`).
    Uses `yaml.safe_load` for security during loading.
    """

    def __init__(self, fernet: typing.Optional[typing.Any] = None) -> None:
        """
        Initializes the YAML storage handler.

        Args:
            fernet: An optional initialized Fernet instance.

        Raises:
            ImportError: If the 'PyYAML' library is not installed.
        """
        if yaml is None:
            log.error("The 'PyYAML' library is required for YamlHandler.")
            log.error("Please install it: pip install pyyaml")
            raise ImportError(
                "YamlHandler requires the 'PyYAML' library. Please install it."
            )
        super().__init__(fernet)

    def load(self, filepath: Path) -> LoadResult:
        """
        Loads configuration from a YAML file, handling decryption if necessary.

        Reads the specified YAML file, decrypts its content if a Fernet key was
        provided, parses the YAML data using `yaml.safe_load`, and determines
        if it represents a 'full' state save or just values.

        Args:
            filepath: The Path object pointing to the YAML configuration file.

        Returns:
            A LoadResult dictionary containing 'version', 'schema', and 'values'.
            The 'values' dictionary can be nested.

        Raises:
            FileNotFoundError: If the file does not exist.
            HandlerError: If the file is not valid YAML, UTF-8, or has an unexpected structure.
            EncryptionError: If decryption fails.
            ImportError: If the 'PyYAML' library is not installed (checked at init).
        """
        log.debug(f"YamlHandler: Attempting to load from: {filepath}")
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        try:
            # 1. Read raw bytes
            raw_data = filepath.read_bytes()
            if not raw_data:
                log.warning(
                    f"YAML configuration file is empty: {filepath}. Returning empty values."
                )
                return {"version": None, "schema": None, "values": {}}

            # 2. Decrypt if needed
            decrypted_bytes: bytes
            if self._fernet:
                log.debug(f"YamlHandler: Decrypting data from {filepath}...")
                try:
                    decrypted_bytes = self._decrypt(raw_data)
                except EncryptionError as e:
                    log.error(f"YamlHandler: Decryption failed for {filepath}: {e}")
                    raise
                log.debug(f"YamlHandler: Decryption successful for {filepath}.")
            else:
                decrypted_bytes = raw_data

            # 3. Decode UTF-8 and parse YAML safely
            try:
                file_content = decrypted_bytes.decode("utf-8")
                # Use safe_load to prevent arbitrary code execution
                loaded_data = yaml.safe_load(file_content)
            except UnicodeDecodeError as e:
                log.error(
                    f"YamlHandler: UTF-8 decode error in {filepath} after potential decryption: {e}"
                )
                raise HandlerError(
                    f"File {filepath} does not contain valid UTF-8 encoded data."
                ) from e
            except yaml.YAMLError as e:
                log.error(f"YamlHandler: YAML decode error in {filepath}: {e}")
                raise HandlerError(f"Invalid YAML structure in {filepath}: {e}") from e
            except Exception as e:
                log.error(
                    f"YamlHandler: Unexpected error during YAML parsing of {filepath}: {e}",
                    exc_info=True,
                )
                raise HandlerError(
                    f"Failed to parse YAML content from {filepath}: {e}"
                ) from e

            # Handle case where YAML file is empty or contains only comments/null
            if loaded_data is None:
                 log.warning(f"YAML file {filepath} parsed as None. Returning empty values.")
                 return {"version": None, "schema": None, "values": {}}

            # 4. Structure the output
            if isinstance(loaded_data, Mapping):
                # Check for 'full' mode structure
                if all(k in loaded_data for k in ("version", "schema", "values")):
                    log.debug(
                        f"YamlHandler: Loaded 'full' structure (version, schema, values) from {filepath}"
                    )
                    loaded_values = loaded_data["values"]
                    loaded_schema = loaded_data["schema"]
                    loaded_version = loaded_data["version"]

                    if not isinstance(loaded_values, Mapping):
                        raise HandlerError(
                            f"Invalid 'values' section in full structure file {filepath} (must be a mapping)."
                        )
                    if loaded_schema is not None and not isinstance(loaded_schema, Mapping):
                         raise HandlerError(
                            f"Invalid 'schema' section in full structure file {filepath} (must be a mapping or null)."
                        )
                    if loaded_version is not None and not isinstance(loaded_version, str):
                        log.warning(f"Version field in {filepath} is not a string. Attempting conversion.")
                        try:
                            loaded_version = str(loaded_version)
                        except Exception:
                             raise HandlerError(f"Could not convert 'version' field in {filepath} to string.")

                    return {
                        "version": loaded_version,
                        "schema": dict(loaded_schema) if loaded_schema else None,
                        "values": dict(loaded_values),
                    }
                else:
                    # Assume it's just a values dictionary (nested mappings are handled)
                    log.debug(
                        f"YamlHandler: Loaded simple values dictionary/mapping from {filepath}"
                    )
                    return {"version": None, "schema": None, "values": dict(loaded_data)}
            else:
                log.error(
                    f"YamlHandler: Root YAML element in {filepath} is not a mapping (found {type(loaded_data).__name__})."
                )
                raise HandlerError(
                    f"Root YAML element in {filepath} must be a mapping (dictionary)."
                )

        except (FileNotFoundError, EncryptionError, HandlerError):
            raise
        except Exception as e:
            log.error(
                f"YamlHandler: Unexpected error loading from {filepath}: {e}",
                exc_info=True,
            )
            raise HandlerError(
                f"Unexpected error loading YAML file {filepath}: {e}"
            ) from e

    def save(self, filepath: Path, data: dict, mode: str = "values") -> None:
        """
        Saves configuration data to a YAML file, handling encryption and save modes.

        Serializes the provided data payload to YAML format using `yaml.dump`.
        Based on the `mode`, it either saves the entire structure or just the values.
        Nested dictionaries/lists are handled correctly. If a Fernet key was provided,
        the resulting YAML bytes are encrypted.

        Args:
            filepath: The Path object pointing to the target YAML file.
            data: The full data payload from ConfigGuard ('instance_version',
                  'schema_definition', 'config_values').
            mode: 'values' or 'full'.

        Raises:
            HandlerError: If serialization fails, required keys are missing, or file writing fails.
            EncryptionError: If encryption fails.
            ValueError: If an invalid `mode` is provided.
            ImportError: If the 'PyYAML' library is not installed (checked at init).
        """
        log.debug(f"YamlHandler: Saving to: {filepath} (mode: {mode})")

        # 1. Select data structure based on mode
        data_to_serialize: typing.Any
        if mode == "full":
            required_keys = ("instance_version", "schema_definition", "config_values")
            if not all(k in data for k in required_keys):
                missing = [k for k in required_keys if k not in data]
                raise HandlerError(f"Invalid data structure for 'full' save mode. Missing keys: {missing}")

            data_to_serialize = {
                "version": data["instance_version"],
                "schema": data["schema_definition"],
                "values": data["config_values"],
            }
            if not isinstance(data_to_serialize["schema"], Mapping):
                 raise HandlerError("'schema_definition' must be a dictionary/mapping for YAML 'full' save.")
            if not isinstance(data_to_serialize["values"], Mapping):
                 raise HandlerError("'config_values' must be a dictionary/mapping for YAML 'full' save.")
            log.debug("YamlHandler: Preparing 'full' data structure for YAML serialization.")

        elif mode == "values":
            if "config_values" not in data:
                raise HandlerError("Invalid data structure for 'values' save mode. Missing 'config_values' key.")
            data_to_serialize = data["config_values"]
            if not isinstance(data_to_serialize, Mapping):
                raise HandlerError("'config_values' must be a dictionary/mapping for 'values' save mode.")
            log.debug("YamlHandler: Preparing 'values'-only data for YAML serialization.")
        else:
            raise ValueError(f"Invalid save mode specified for YamlHandler: '{mode}'. Must be 'values' or 'full'.")

        try:
            # 2. Serialize to YAML string bytes (UTF-8 encoded)
            try:
                # yaml.dump handles nested structures; default_flow_style=False gives block style
                yaml_string = yaml.dump(data_to_serialize, default_flow_style=False, sort_keys=False, allow_unicode=True)
                yaml_bytes = yaml_string.encode("utf-8")
            except yaml.YAMLError as e:
                log.error(f"YamlHandler: YAML serialization failed: {e}", exc_info=True)
                raise HandlerError(f"Data cannot be serialized to YAML: {e}") from e
            except Exception as e:
                log.error(f"YamlHandler: Unexpected error during YAML serialization: {e}", exc_info=True)
                raise HandlerError(f"Unexpected YAML serialization error: {e}") from e

            # 3. Encrypt if needed
            bytes_to_write: bytes
            status_log = "(unencrypted)"
            if self._fernet:
                log.debug(f"YamlHandler: Encrypting data for {filepath}...")
                try:
                    bytes_to_write = self._encrypt(yaml_bytes)
                except EncryptionError as e:
                    log.error(f"YamlHandler: Encryption failed for {filepath}: {e}")
                    raise
                status_log = "(encrypted)"
                log.debug(f"YamlHandler: Encryption successful for {filepath}.")
            else:
                bytes_to_write = yaml_bytes

            # 4. Write bytes to file
            log.debug(f"YamlHandler: Writing {len(bytes_to_write)} bytes to {filepath}")
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(bytes_to_write)
            except IOError as e:
                log.error(f"YamlHandler: File write error for {filepath}: {e}")
                raise HandlerError(f"Failed to write configuration file {filepath}: {e}") from e
            except Exception as e:
                log.error(f"YamlHandler: Unexpected error writing file {filepath}: {e}", exc_info=True)
                raise HandlerError(f"Unexpected error writing file {filepath}: {e}") from e

            log.info(f"YamlHandler: Successfully saved to {filepath} {status_log} (mode: {mode}).")

        except (EncryptionError, HandlerError, ValueError):
            raise
        except Exception as e:
            log.error(f"YamlHandler: Unexpected error saving to {filepath}: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error saving YAML file {filepath}: {e}") from e