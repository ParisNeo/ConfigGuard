# -*- coding: utf-8 -*-
# Project: ConfigMaster
# File: config.py
# Author: ParisNeo with Gemini 2.5
# Date: 30/04/2025
# Description: Main ConfigMaster class for managing application configurations,
#              designed to be handler-agnostic and support versioning/migration.

import typing
from pathlib import Path
import copy
from collections.abc import MutableMapping

# Use the base handler class only for type hinting and factory
from .handlers.base import StorageHandler, LoadResult
from .handlers import get_handler # Factory function is ok
# Import specific handlers ONLY for type checking if necessary, but avoid functional dependency
from .handlers.json_handler import JsonHandler # Used only in _load_schema_definition check

from .schema import SettingSchema
from .setting import ConfigSetting
from .exceptions import SchemaError, ValidationError, HandlerError, SettingNotFoundError, EncryptionError
from .log import log
from packaging.version import parse as parse_version, InvalidVersion

# Handle optional cryptography import
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None # Define Fernet as None if cryptography is not installed

# --- Type Coercion Helper ---
def _try_coerce(value: typing.Any, target_type: type, source_type_str: typing.Optional[str] = None) -> typing.Any:
    """
    Attempts basic coercion between compatible types (int, float, str, bool).

    Args:
        value: The value to coerce.
        target_type: The target Python type (e.g., int, str, bool).
        source_type_str: Optional string representation of the source type for logging.

    Returns:
        The coerced value if successful, otherwise the original value.
    """
    if isinstance(value, target_type):
        return value # Already correct type

    original_value_repr = repr(value) # For logging
    log.debug(f"Attempting coercion for {original_value_repr} to {target_type.__name__} (source type approx: {source_type_str or type(value).__name__})")

    # Bool coercion
    if target_type is bool:
        if isinstance(value, str):
            val_lower = value.lower()
            if val_lower == "true": return True
            if val_lower == "false": return False
        if isinstance(value, (int, float)):
            if value == 1: return True
            if value == 0: return False
        log.warning(f"Could not coerce {original_value_repr} to bool.")
        return value # Return original for validation to fail clearly

    # Numeric/String coercion
    if target_type in (int, float):
        if isinstance(value, (int, float)): # Already numeric, just convert type
             try: return target_type(value)
             except Exception: pass # Should not fail, but be safe
        elif isinstance(value, str):
            try:
                numeric_val = float(value) # Try float first
                if target_type is int:
                     if numeric_val.is_integer():
                         return int(numeric_val)
                     else:
                         log.warning(f"Cannot coerce string '{value}' to int (not an integer).")
                         return value # Return original string if float needed but int requested
                else: # Target is float
                     return numeric_val
            except ValueError:
                 log.warning(f"Cannot coerce string '{value}' to numeric type {target_type.__name__}.")
                 return value # Return original string if not numeric
        # else: Fall through, return original value

    elif target_type is str:
         if isinstance(value, (int, float, bool)):
             return str(value)
         # else: Fall through for other types

    elif target_type is list:
        # TODO: Consider adding optional basic coercion (e.g., comma-separated string to list)
        pass

    log.debug(f"No specific coercion rule applied for {original_value_repr} to {target_type.__name__}. Returning original.")
    return value


class ConfigMaster(MutableMapping):
    """
    Main class for managing application configurations. Agnostic of storage format.

    Handles configuration schema definition, validation, loading/saving via storage
    handlers, encryption, versioning, and basic migration. Access settings via
    attribute or dictionary syntax (e.g., `config.setting_name` or `config['setting_name']`).
    Access schema details via `config.sc_setting_name` or `config['sc_setting_name']`.
    """
    VERSION_KEY = "__version__" # Schema key for version info

    def __init__(self,
                 schema: typing.Union[dict, str, Path],
                 config_path: typing.Optional[typing.Union[str, Path]] = None,
                 encryption_key: typing.Optional[bytes] = None,
                 autosave: bool = False) -> None:
        """
        Initializes ConfigMaster.

        Args:
            schema: The configuration schema definition for this instance.
                    Can be a dictionary or a path to a schema file (JSON expected).
                    Should ideally contain a top-level '__version__' key (e.g., "1.0.0").
            config_path: Path to the configuration file for loading/saving values or full state.
            encryption_key: Optional bytes key for encrypting/decrypting the config file via the handler.
            autosave: If True, automatically save configuration values (mode='values')
                      whenever a setting is changed via attribute or item access. Defaults to False.

        Raises:
            SchemaError: If the schema definition is invalid or contains an invalid version format.
            EncryptionError: If `encryption_key` is provided but `cryptography` is not installed
                             or the key is invalid.
            HandlerError: If `config_path` is provided but no suitable handler is found.
        """
        log.info("Initializing ConfigMaster...")
        self._settings: typing.Dict[str, ConfigSetting] = {}
        self._raw_instance_schema: dict = self._load_schema_definition(schema)

        # Determine and store instance version from the provided schema
        try:
            raw_version = self._raw_instance_schema.get(self.VERSION_KEY)
            if raw_version is None:
                 log.warning(f"Schema definition missing '{self.VERSION_KEY}'. Defaulting instance version to 0.0.0.")
                 self.version: str = "0.0.0"
            else:
                 self.version = str(raw_version)
                 parse_version(self.version) # Validate format
            log.debug(f"ConfigMaster instance version set to: {self.version}")
        except InvalidVersion:
            log.error(f"Invalid version format '{raw_version}' found in schema definition.")
            raise SchemaError(f"Invalid version format in schema: {raw_version}")

        # Instance schema definition used internally (excludes the version key)
        self._instance_schema_definition: dict = {
            k: v for k, v in self._raw_instance_schema.items() if k != self.VERSION_KEY
        }

        self._config_path: typing.Optional[Path] = Path(config_path) if config_path else None
        self._handler: typing.Optional[StorageHandler] = None
        self._fernet: typing.Optional[Fernet] = None # Store Fernet instance if used
        self._autosave: bool = autosave
        self.loaded_file_version: typing.Optional[str] = None # Track version loaded from file

        # Initialize encryption if key provided
        if encryption_key:
            if Fernet is None:
                 log.error("Encryption requires 'cryptography'. Please install it: pip install cryptography")
                 raise EncryptionError("Cryptography library not found, but encryption key provided.")
            try:
                 self._fernet = Fernet(encryption_key)
                 log.info("Encryption enabled (Fernet instance created).")
            except Exception as e:
                 log.error(f"Failed to initialize encryption with provided key: {e}")
                 raise EncryptionError(f"Invalid encryption key or Fernet setup failed: {e}") from e

        # Get handler instance, passing fernet instance to it
        if self._config_path:
            try:
                # Pass the Fernet instance (if any) to the handler factory
                self._handler = get_handler(self._config_path, fernet=self._fernet)
                log.info(f"Initialized handler '{self._handler.__class__.__name__}' for path: {self._config_path}")
            except HandlerError as e:
                log.warning(f"{e}. Configuration loading/saving might be disabled for this path.")
                # Keep _config_path, but handler remains None

        # Build internal settings objects based on the instance schema (after version extracted)
        self._build_settings_from_schema()

        # Load initial config if path and handler are valid
        if self._config_path and self._handler:
            try:
                self.load() # Initial load attempt
            except FileNotFoundError:
                 log.warning(f"Configuration file {self._config_path} not found. Initializing with defaults.")
            except (HandlerError, EncryptionError, ValidationError, SchemaError) as e:
                 # Log errors during initial load but allow initialization to continue with defaults
                 log.error(f"Failed to load initial configuration from {self._config_path}: {e}. Continuing with defaults where applicable.")
            except Exception as e:
                 log.error(f"Unexpected error loading initial configuration from {self._config_path}: {e}", exc_info=True)
        else:
             log.info("No valid config_path/handler setup, or file not found. Initializing with default values.")

        log.info(f"ConfigMaster initialized successfully (Instance Version: {self.version}).")

    def _load_schema_definition(self, schema_input: typing.Union[dict, str, Path]) -> dict:
        """
        Loads the raw schema definition from a dictionary or JSON file.

        Args:
            schema_input: Dictionary or path to the schema definition file (JSON expected).

        Returns:
            The raw schema dictionary, including the version key if present.

        Raises:
            SchemaError: If loading fails or the format is invalid.
            TypeError: If schema_input is not a dict, str, or Path.
        """
        if isinstance(schema_input, dict):
            log.debug("Loading schema from dictionary.")
            return copy.deepcopy(schema_input) # Return a copy
        elif isinstance(schema_input, (str, Path)):
            schema_path = Path(schema_input)
            log.debug(f"Loading schema definition from file: {schema_path}")
            if not schema_path.exists():
                raise SchemaError(f"Schema file not found: {schema_path}")
            # We expect schema definitions to be in JSON format for simplicity
            if schema_path.suffix.lower() != ".json":
                 raise SchemaError(f"Schema file must be a JSON file (.json extension). Found: {schema_path.suffix}")
            try:
                 # Use a temporary JSON handler *without* encryption to load the schema file.
                 # Schema definition files themselves are assumed not to be encrypted.
                 temp_json_handler = JsonHandler(fernet=None)
                 # JsonHandler.load returns LoadResult; assume schema is in 'values' part
                 load_result = temp_json_handler.load(schema_path)
                 raw_schema = load_result['values']
                 if not isinstance(raw_schema, dict):
                      raise SchemaError(f"Schema file {schema_path} does not contain a valid JSON object at the root.")
                 log.info(f"Successfully loaded schema definition from {schema_path}")
                 return raw_schema
            except (HandlerError, FileNotFoundError) as e:
                 raise SchemaError(f"Failed to load schema definition from {schema_path}: {e}") from e
            except Exception as e:
                raise SchemaError(f"Unexpected error loading schema from file {schema_path}: {e}") from e
        else:
            raise TypeError("Schema input must be a dictionary or a file path (str or Path).")

    def _build_settings_from_schema(self) -> None:
        """Parses the instance schema definition (excluding version key) and creates ConfigSetting objects."""
        log.debug(f"Building ConfigSetting objects for instance version {self.version}...")
        self._settings = {}
        for name, definition in self._instance_schema_definition.items():
            try:
                schema = SettingSchema(name, definition)
                self._settings[name] = ConfigSetting(schema)
            except SchemaError as e:
                log.error(f"Schema error for setting '{name}' in instance schema: {e}")
                raise # Propagate schema errors during initialization
        log.debug(f"Finished building {len(self._settings)} ConfigSetting objects.")

    def load(self, filepath: typing.Optional[typing.Union[str, Path]] = None) -> None:
        """
        Loads configuration using the configured handler. Handles versioning and migration.

        Uses the handler determined by the `config_path` (or override `filepath`).
        Interprets the loaded data (values only or full state) and applies it to
        the current instance based on version comparison and schema compatibility.

        Args:
            filepath: Optional path to load from. Overrides the instance's config_path.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            HandlerError: If no handler is available or loading/parsing fails.
            EncryptionError: If decryption fails.
            ValidationError: If a loaded value fails validation against the instance schema after potential coercion.
            SchemaError: If version comparison fails (e.g., file is newer) or schema structure is invalid.
        """
        load_path = Path(filepath) if filepath else self._config_path
        current_handler = self._handler # Use the instance handler configured at init

        if not load_path:
            raise HandlerError("No configuration file path specified for loading.")
        if not current_handler:
             raise HandlerError(f"No valid handler available for the configured path: {self._config_path}")

        log.info(f"Attempting to load configuration from: {load_path} using {current_handler.__class__.__name__}")

        try:
            # 1. Use handler to load data (handles decryption)
            # Handler should raise FileNotFoundError if the file is genuinely missing.
            loaded_data: LoadResult = current_handler.load(load_path)

            loaded_version_str = loaded_data.get('version')
            loaded_schema_dict = loaded_data.get('schema') # Schema from file (if present)
            loaded_values_dict = loaded_data.get('values') # Values dict (should always be present)

            if loaded_values_dict is None or not isinstance(loaded_values_dict, dict):
                 log.error(f"Handler did not return a valid dictionary for 'values' from {load_path}")
                 raise HandlerError(f"Invalid 'values' data loaded from {load_path}")

            self.loaded_file_version = loaded_version_str # Store for info
            log.info(f"File loaded. Version in file: {loaded_version_str or 'N/A'}. Instance version: {self.version}.")

            # 2. Version Comparison and Application Logic
            allow_migration = False
            load_mode_desc = "values only or legacy" # Assume values only unless version is present
            if loaded_version_str is not None:
                load_mode_desc = f"full state (v{loaded_version_str})"
                try:
                    loaded_ver = parse_version(loaded_version_str)
                    instance_ver = parse_version(self.version)

                    if loaded_ver > instance_ver:
                        log.error(f"Loaded config version ({loaded_ver}) is NEWER than instance version ({instance_ver}).")
                        raise SchemaError(f"Cannot load configuration: File version {loaded_ver} is newer than instance version {instance_ver}.")
                    elif loaded_ver < instance_ver:
                        log.warning(f"Loaded config version ({loaded_ver}) is OLDER than instance version ({instance_ver}). Enabling migration logic.")
                        allow_migration = True
                    else: # loaded_ver == instance_ver
                         log.info(f"Configuration versions match ({instance_ver}).")
                         if loaded_schema_dict and loaded_schema_dict != self._instance_schema_definition:
                              log.warning("Loaded schema definition differs from instance schema definition, but versions match. Using instance schema for validation.")

                except InvalidVersion as e:
                     log.error(f"Invalid version format found in loaded file ('{loaded_version_str}'): {e}")
                     raise SchemaError(f"Invalid version format in loaded file: {loaded_version_str}") from e
            else:
                log.warning("Loaded configuration file has no version information. Applying values directly.")

            # 3. Apply values using the helper method
            log.info(f"Applying loaded values from '{load_mode_desc}' file...")
            self._apply_and_migrate_values(
                loaded_values=loaded_values_dict,
                loaded_schema=loaded_schema_dict, # Pass schema from file if available
                allow_migration=allow_migration
            )

        except FileNotFoundError:
            # Let __init__ handle logging for initial load, re-raise for manual load
            log.warning(f"Load failed: File not found at {load_path}")
            raise

        except (HandlerError, EncryptionError, ValidationError, SchemaError) as e:
             # Log and re-raise known ConfigMaster error types
             log.error(f"Failed to load/process configuration from {load_path}: {e}")
             raise
        except Exception as e:
            # Catch any other unexpected exceptions
            log.error(f"An unexpected error occurred during loading from {load_path}: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error loading configuration: {e}") from e


    def _apply_and_migrate_values(self,
                                 loaded_values: dict,
                                 loaded_schema: typing.Optional[dict],
                                 allow_migration: bool) -> None:
        """
        Applies loaded values to the instance settings, handling schema differences
        and potential type coercions. Resets to instance default on validation failure.

        Args:
            loaded_values: Dictionary of values loaded from the file.
            loaded_schema: Dictionary representing the schema loaded from the file (if any).
            allow_migration: True if loaded version is older than instance version.
        """
        applied_count = 0
        skipped_validation = 0
        skipped_migration = 0
        coercion_warnings = 0
        processed_keys = set() # Track keys from loaded_values that we processed

        log.debug(f"Applying loaded values (Migration: {allow_migration}, Loaded Schema Provided: {loaded_schema is not None})...")

        # Iterate through the settings defined in the *current instance* schema
        for setting_name, current_setting_obj in self._settings.items():
            current_schema = current_setting_obj.schema # SettingSchema object for the instance

            if setting_name in loaded_values:
                processed_keys.add(setting_name)
                loaded_value = loaded_values[setting_name]
                value_to_validate = loaded_value # Start with the loaded value
                source_type_str = None # Track source type if loaded schema available

                # --- Attempt Type Coercion if Schemas Differ (and loaded schema exists) ---
                if loaded_schema and setting_name in loaded_schema:
                    loaded_setting_schema_info = loaded_schema.get(setting_name, {}) # Use .get for safety
                    if isinstance(loaded_setting_schema_info, dict): # Ensure it's a dict
                        loaded_type_str = loaded_setting_schema_info.get('type')
                        source_type_str = loaded_type_str # For logging coercion attempt
                        if loaded_type_str and loaded_type_str != current_schema.type_str:
                            log.warning(f"Type mismatch for setting '{setting_name}': Instance expects '{current_schema.type_str}', file had '{loaded_type_str}'. Attempting coercion...")
                            coerced_value = _try_coerce(loaded_value, current_schema.type, source_type_str=loaded_type_str)

                            if coerced_value is not loaded_value: # Check if coercion actually changed the value/type
                                log.info(f"Coerced '{setting_name}' value from {type(loaded_value).__name__} to {type(coerced_value).__name__}.")
                                value_to_validate = coerced_value
                            else:
                                 log.warning(f"Coercion from '{loaded_type_str}' to '{current_schema.type_str}' did not succeed for '{setting_name}' (value: {loaded_value!r}). Proceeding with original value for validation.")
                                 coercion_warnings += 1
                    else:
                        log.debug(f"No type information found in loaded schema for '{setting_name}'. Skipping coercion.")

                # --- Validate against the *instance's* schema ---
                try:
                    # Use the ConfigSetting's setter for validation and final assignment
                    current_setting_obj.value = value_to_validate
                    applied_count += 1
                    log.debug(f"Successfully applied value for '{setting_name}': {current_setting_obj.value!r}")
                except ValidationError as e:
                    skipped_validation += 1
                    log.warning(f"Validation failed for setting '{setting_name}' with value '{value_to_validate!r}' (original loaded: '{loaded_value!r}'): {e}. RESETTING to instance default.")
                    # Reset to default if validation fails after load/migration
                    # Ensures the instance state remains valid according to its current schema.
                    try:
                        current_setting_obj.value = current_schema.default_value
                    except ValidationError as e_default:
                         # This should be rare - means the default value itself is invalid for the current schema
                         log.error(f"CRITICAL: Default value for '{setting_name}' is invalid according to its own schema: {e_default}. Setting left in potentially inconsistent state (likely previous value or initial None).")


            else:
                # Setting exists in instance schema but not in loaded values dict
                # Keep the default value (already set during _build_settings_from_schema)
                log.debug(f"Setting '{setting_name}' not found in loaded values. Using instance default: {current_setting_obj.value!r}")

        # --- Check for keys in loaded_values that are not in the instance schema ---
        unknown_or_migrated_keys = set(loaded_values.keys()) - processed_keys
        skipped_unknown = 0
        for key in unknown_or_migrated_keys:
            if allow_migration:
                skipped_migration += 1
                log.warning(f"Migration: Setting '{key}' (value: {loaded_values[key]!r}) loaded from older version is not present in current instance version ({self.version}). Skipping.")
            else:
                # If versions match or only values were loaded, these are just unknown settings
                skipped_unknown += 1
                log.warning(f"Setting '{key}' found in loaded file but not defined in current instance schema. Ignoring.")

        log.info(f"Value application finished. Applied: {applied_count}, Skipped (validation): {skipped_validation}, Skipped (migration): {skipped_migration}, Skipped (unknown): {skipped_unknown}, Coercion Warnings: {coercion_warnings}.")


    def save(self, filepath: typing.Optional[typing.Union[str, Path]] = None, mode: str = 'values') -> None:
        """
        Saves the configuration using the configured handler and specified mode.

        Args:
            filepath: Optional path to save to. Overrides the instance's config_path.
            mode: Specifies what to save:
                  - 'values': Save only the current configuration values. File structure
                              depends on the handler (e.g., simple JSON dict).
                  - 'full': Save the instance version, schema definition, and values.
                            File structure depends on the handler (e.g., specific JSON structure).

        Raises:
            HandlerError: If saving fails (no path, no handler, serialization, encryption).
            EncryptionError: If encryption specifically fails.
            ValueError: If an invalid `mode` is provided.

        """
        save_path = Path(filepath) if filepath else self._config_path
        current_handler = self._handler

        if not save_path:
            raise HandlerError("No configuration file path specified for saving.")
        if not current_handler:
             raise HandlerError(f"No valid handler available for the configured path: {self._config_path}")

        # Validate mode
        if mode not in ['values', 'full']:
            raise ValueError(f"Invalid save mode: '{mode}'. Must be 'values' or 'full'.")

        log.info(f"Saving configuration to: {save_path} using {current_handler.__class__.__name__} (mode: {mode})")

        try:
            # Prepare the data payload for the handler, always including all parts
            # The handler will decide what to use based on the 'mode'.
            data_payload = {
                "instance_version": self.version,
                # Pass the schema definition *without* the internal version key
                "schema_definition": self.get_instance_schema_definition(),
                "config_values": self.get_config_dict()
            }

            # Call the handler's save method, passing the mode
            current_handler.save(save_path, data=data_payload, mode=mode)
            # Handler logs detailed success/failure and manages file writing/encryption

        except (HandlerError, EncryptionError) as e:
             # Log and re-raise known errors from the handler
             log.error(f"Failed to save configuration to {save_path} (mode={mode}): {e}")
             raise
        except Exception as e:
            # Catch unexpected errors during payload prep or handler call
            log.error(f"An unexpected error occurred during saving to {save_path} (mode={mode}): {e}", exc_info=True)
            raise HandlerError(f"Unexpected error saving configuration: {e}") from e

    # --- Public Data Access Methods ---

    def get_instance_schema_definition(self) -> dict:
        """Returns the schema definition used by this ConfigMaster instance (excludes version key)."""
        # self._instance_schema_definition already excludes the version key
        return copy.deepcopy(self._instance_schema_definition)

    def get_config_dict(self) -> dict:
        """Returns the current configuration values as a dictionary."""
        return {name: setting.value for name, setting in self._settings.items()}

    def export_schema_with_values(self) -> dict:
        """
        Exports the *current* state (instance schema + values) for external use (e.g., UI).

        This provides a snapshot of the current instance's schema and values, along with
        its operational version. It's suitable for sending to a frontend application.

        Returns:
            A dictionary containing:
            - 'version': The version string of this ConfigMaster instance.
            - 'schema': The dictionary defining the settings structure used by this instance.
            - 'settings': A dictionary mapping setting names to their details:
                          `{ 'schema': setting_schema_dict, 'value': current_value }`
        """
        log.debug("Exporting current instance schema with current values and instance version.")
        settings_export = {}
        for name, setting in self._settings.items():
            settings_export[name] = {
                "schema": setting.schema.to_dict(), # Uses SettingSchema.to_dict()
                "value": setting.value
            }
        full_export = {
            "version": self.version, # Version of this instance
            "schema": self.get_instance_schema_definition(), # Schema defs used by instance
            "settings": settings_export # Per-setting details + current value
        }
        log.debug(f"Generated export for instance version {self.version} with {len(settings_export)} settings.")
        return full_export

    def import_config(self, data: dict, ignore_unknown: bool = True) -> None:
        """
        Imports configuration *values* from a dictionary, validating against the instance schema.

        This method only imports values. It does not handle schema or version info
        present in the dictionary. Use `load()` to load from files potentially
        containing full state with versioning and schema details.

        Args:
            data: A dictionary of {setting_name: value}.
            ignore_unknown: If True (default), ignores keys in `data` not present in the instance schema.
                            If False, raises SettingNotFoundError for unknown keys.

        Raises:
            SettingNotFoundError: If `ignore_unknown` is False and unknown keys are present.
            TypeError: If the input `data` is not a dictionary.
            ValidationError: If any value fails validation against the instance schema (logged as warning).
        """
        if not isinstance(data, dict):
            raise TypeError(f"Input data for import_config must be a dictionary, got {type(data).__name__}")

        log.info(f"Importing configuration values from dictionary ({len(data)} items)...")
        # Reuse the internal apply method. Treat the input dict as 'loaded_values'
        # with no accompanying 'loaded_schema' and disallow migration logic.
        try:
             self._apply_and_migrate_values(
                 loaded_values=data,
                 loaded_schema=None, # No schema context from dict import
                 allow_migration=False # Treat keys not in instance schema as 'unknown'
             )
             # Check for unknown keys *after* applying known ones
             unknown_keys = set(data.keys()) - set(self._settings.keys())
             if unknown_keys :
                  log.warning(f"Unknown keys found during dictionary import: {', '.join(unknown_keys)}")
                  if not ignore_unknown:
                       log.error(f"Import failed: Unknown keys found and ignore_unknown=False.")
                       raise SettingNotFoundError(f"Import failed: Unknown setting(s) encountered: {', '.join(unknown_keys)}")

        except ValidationError as e:
             # Validation errors are logged within _apply_and_migrate_values.
             # Log a summary error here.
             log.error(f"Validation errors occurred during import. See previous warnings. Last error detail: {e}")
             # Decide whether to re-raise. For import, maybe just logging is sufficient.
             # raise ValidationError("Validation errors occurred during import.") from e
        except SettingNotFoundError:
             # Re-raise if ignore_unknown was False (already raised above)
             raise             
        except Exception as e:
             log.error(f"Unexpected error during dictionary import: {e}", exc_info=True)
             # Wrap unexpected errors
             raise HandlerError(f"Unexpected error during dictionary import: {e}") from e

        log.info("Dictionary import finished.")
        # Note: Autosave is NOT triggered by this method. Call self.save() explicitly if needed.


    # --- Magic methods ---
    def __getattr__(self, name: str) -> typing.Any:
        """Allows accessing settings like attributes (e.g., config.port) or schema (config.sc_port)."""
        if name.startswith('sc_') and not name.startswith('_'):
             actual_name = name[3:]
             if actual_name in self._settings:
                 return self._settings[actual_name].schema
             else:
                  raise AttributeError(f"'{type(self).__name__}' object has no schema attribute '{name}' (setting '{actual_name}' not found)")

        if name in self._settings:
            return self._settings[name].value
        else:
            try:
                 # Check for actual methods/attributes like 'version', 'load', 'save' etc.
                 return super().__getattribute__(name)
            except AttributeError:
                 # Raise AttributeError consistent with Python behavior
                 raise AttributeError(f"'{type(self).__name__}' object has no attribute or setting '{name}'") from None

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Allows setting values like attributes (e.g., config.port = 8080), triggering validation and autosave."""
        # Prevent setting schema attributes directly
        if name.startswith('sc_') and not name.startswith('_'):
            raise AttributeError("Cannot set schema attributes directly (use 'config.sc_name' to access).")

        # Handle internal attributes carefully based on known names or leading underscore
        known_internals = {
            '_settings', '_raw_instance_schema', '_instance_schema_definition',
            'version', '_config_path', '_handler', '_fernet', '_autosave',
            'loaded_file_version'
        }
        if name.startswith('_') or name in known_internals or hasattr(type(self), name):
            super().__setattr__(name, value)
        # Handle setting configuration values via attribute access
        elif name in self._settings:
            try:
                setting = self._settings[name]
                setting.value = value # Validation and coercion happen in ConfigSetting setter
                log.debug(f"Set attribute '{name}' to {setting.value!r}")
                if self._autosave:
                    log.debug(f"Autosaving configuration (values) due to change in '{name}'...")
                    # Ensure save is called only if handler exists and path is set
                    if self._handler and self._config_path:
                         self.save(mode='values')
                    else:
                         log.warning(f"Autosave for '{name}' skipped: No valid handler or config_path.")
            except ValidationError as e:
                 raise e # Propagate validation errors
        else:
            # Block setting arbitrary (non-internal, non-setting) attributes
             raise AttributeError(f"Cannot set attribute '{name}'. It's not a defined setting or internal attribute.")


    def __getitem__(self, key: str) -> typing.Any:
        """Allows accessing settings like dictionary items (e.g., config['port']) or schema (config['sc_port'])."""
        if key.startswith('sc_'):
             actual_key = key[3:]
             if actual_key in self._settings:
                 return self._settings[actual_key].schema
             else:
                 raise SettingNotFoundError(f"Schema for setting '{actual_key}' not found.") # Use specific error

        if key in self._settings:
            return self._settings[key].value
        else:
            raise SettingNotFoundError(f"Setting '{key}' not found.") # Use specific error

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """Allows setting values like dictionary items (e.g., config['port'] = 8080), triggering validation and autosave."""
        if key.startswith('sc_'):
            raise KeyError("Cannot set schema items directly (use config['sc_name'] to access).")

        if key in self._settings:
            try:
                setting = self._settings[key]
                setting.value = value # Validation and coercion happen in ConfigSetting setter
                log.debug(f"Set item '{key}' to {setting.value!r}")
                if self._autosave:
                    log.debug(f"Autosaving configuration (values) due to change in '{key}'...")
                    if self._handler and self._config_path:
                         self.save(mode='values')
                    else:
                         log.warning(f"Autosave for '{key}' skipped: No valid handler or config_path.")
            except ValidationError as e:
                 raise e # Propagate validation errors
        else:
            raise SettingNotFoundError(f"Setting '{key}' not found. Cannot set undefined settings.")

    def __delitem__(self, key: str) -> None:
        """Prevent deleting settings."""
        raise TypeError("Deleting configuration settings is not supported.")

    def __iter__(self) -> typing.Iterator[str]:
        """Iterates over the names of the defined settings."""
        return iter(self._settings.keys())

    def __len__(self) -> int:
        """Returns the number of defined settings."""
        return len(self._settings)

    def __contains__(self, key: object) -> bool:
        """Checks if a setting name exists."""
        return isinstance(key, str) and key in self._settings

    def __repr__(self) -> str:
        """Returns a developer-friendly representation of the ConfigMaster instance."""
        path_str = f"'{self._config_path}'" if self._config_path else "None"
        handler_name = self._handler.__class__.__name__ if self._handler else "None"
        encrypted_str = ", encrypted" if self._fernet else ""
        return (f"ConfigMaster(version='{self.version}', config_path={path_str}, "
                f"handler='{handler_name}', settings={len(self._settings)}{encrypted_str})")