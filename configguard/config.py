# Project: ConfigGuard
# File: configguard/config.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Updated for nesting)
# Description: Main ConfigGuard class for managing application configurations,
#              designed to be handler-agnostic, support versioning/migration,
#              and handle nested configuration structures.

import copy
import typing
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from packaging.version import InvalidVersion
from packaging.version import parse as parse_version

from .exceptions import (
    EncryptionError,
    HandlerError,
    SchemaError,
    SettingNotFoundError,
    ValidationError,
)
from .handlers import get_handler  # Factory function
from .handlers.base import LoadResult, StorageHandler
from .handlers.json_handler import JsonHandler  # Used only in _load_schema_definition
from .log import log
from .schema import SUPPORTED_TYPES, SettingSchema
from .section import ConfigSection  # Import the new ConfigSection class
from .setting import ConfigSetting

# Handle optional cryptography import
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # Define Fernet as None if cryptography is not installed


# --- Type Coercion Helper ---
def _try_coerce(
    value: typing.Any, target_type: type, source_type_str: typing.Optional[str] = None
) -> typing.Any:
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
        return value  # Already correct type

    original_value_repr = repr(value)  # For logging
    log.debug(
        f"Attempting coercion for {original_value_repr} to {target_type.__name__} (source type approx: {source_type_str or type(value).__name__})"
    )

    # Bool coercion
    if target_type is bool:
        if isinstance(value, str):
            val_lower = value.lower()
            if val_lower == "true":
                return True
            if val_lower == "false":
                return False
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
        log.warning(f"Could not coerce {original_value_repr} to bool.")
        return value  # Return original for validation to fail clearly

    # Numeric/String coercion
    if target_type in (int, float):
        if isinstance(value, (int, float)):  # Already numeric, just convert type
            try:
                return target_type(value)
            except Exception:
                pass  # Should not fail, but be safe
        elif isinstance(value, str):
            try:
                numeric_val = float(value)  # Try float first
                if target_type is int:
                    if numeric_val.is_integer():
                        return int(numeric_val)
                    else:
                        log.warning(
                            f"Cannot coerce string '{value}' to int (not an integer)."
                        )
                        return value  # Return original string if float needed but int requested
                else:  # Target is float
                    return numeric_val
            except ValueError:
                log.warning(
                    f"Cannot coerce string '{value}' to numeric type {target_type.__name__}."
                )
                return value  # Return original string if not numeric
        # else: Fall through, return original value

    elif target_type is str:
        if isinstance(value, (int, float, bool)):
            return str(value)
        # else: Fall through for other types

    elif target_type is list:
        # TODO: Consider adding optional basic coercion (e.g., comma-separated string to list)
        pass

    log.debug(
        f"No specific coercion rule applied for {original_value_repr} to {target_type.__name__}. Returning original."
    )
    return value


class ConfigGuard(MutableMapping):
    """
    Main class for managing application configurations. Agnostic of storage format.

    Handles configuration schema definition (including nested sections), validation,
    loading/saving via storage handlers, encryption, versioning, and basic migration.
    Access settings via attribute (`config.setting` or `config.section.setting`) or
    dictionary syntax (`config['setting']` or `config['section']['setting']`).
    Access schema details via `config.sc_setting` or `config.sc_section.sc_setting`.
    """

    VERSION_KEY = "__version__"  # Schema key for version info
    SECTION_TYPE_KEY = "section"  # Type identifier for sections in schema

    def __init__(
        self,
        schema: typing.Union[dict, str, Path],
        config_path: typing.Optional[typing.Union[str, Path]] = None,
        encryption_key: typing.Optional[bytes] = None,
        autosave: bool = False,
    ) -> None:
        """
        Initializes ConfigGuard.

        Args:
            schema: The configuration schema definition for this instance.
                    Can be a dictionary or a path to a schema file (JSON expected).
                    Should contain a top-level '__version__' key (e.g., "1.0.0").
                    Can contain nested sections defined with `"type": "section"`.
            config_path: Path to the configuration file for loading/saving values or full state.
            encryption_key: Optional bytes key for encrypting/decrypting the config file via the handler.
            autosave: If True, automatically save configuration values (mode='values')
                      whenever a setting is changed (including nested settings). Defaults to False.

        Raises:
            SchemaError: If the schema definition is invalid or contains an invalid version format.
            EncryptionError: If `encryption_key` is provided but `cryptography` is not installed
                             or the key is invalid.
            HandlerError: If `config_path` is provided but no suitable handler is found.
        """
        log.info("Initializing ConfigGuard...")
        # Internal storage now holds settings OR sections
        self._settings: typing.Dict[str, typing.Union[ConfigSetting, ConfigSection]] = (
            {}
        )
        self._raw_instance_schema: dict = self._load_schema_definition(schema)

        # Determine and store instance version from the provided schema
        try:
            raw_version = self._raw_instance_schema.get(self.VERSION_KEY)
            if raw_version is None:
                log.warning(
                    f"Schema definition missing '{self.VERSION_KEY}'. Defaulting instance version to 0.0.0."
                )
                self.version: str = "0.0.0"
            else:
                self.version = str(raw_version)
                parse_version(self.version)  # Validate format
            log.debug(f"ConfigGuard instance version set to: {self.version}")
        except InvalidVersion:
            log.error(
                f"Invalid version format '{raw_version}' found in schema definition."
            )
            raise SchemaError(f"Invalid version format in schema: {raw_version}")

        # Instance schema definition used internally (excludes the version key)
        self._instance_schema_definition: dict = {
            k: v for k, v in self._raw_instance_schema.items() if k != self.VERSION_KEY
        }

        self._config_path: typing.Optional[Path] = (
            Path(config_path) if config_path else None
        )
        self._handler: typing.Optional[StorageHandler] = None
        self._fernet: typing.Optional[Fernet] = None  # Store Fernet instance if used
        self._autosave: bool = autosave
        self.loaded_file_version: typing.Optional[str] = (
            None  # Track version loaded from file
        )

        # Initialize encryption if key provided
        if encryption_key:
            if Fernet is None:
                log.error(
                    "Encryption requires 'cryptography'. Please install it: pip install cryptography"
                )
                raise EncryptionError(
                    "Cryptography library not found, but encryption key provided."
                )
            try:
                self._fernet = Fernet(encryption_key)
                log.info("Encryption enabled (Fernet instance created).")
            except Exception as e:
                log.error(f"Failed to initialize encryption with provided key: {e}")
                raise EncryptionError(
                    f"Invalid encryption key or Fernet setup failed: {e}"
                ) from e

        # Get handler instance, passing fernet instance to it
        if self._config_path:
            try:
                self._handler = get_handler(self._config_path, fernet=self._fernet)
                log.info(
                    f"Initialized handler '{self._handler.__class__.__name__}' for path: {self._config_path}"
                )
            except HandlerError as e:
                log.warning(
                    f"{e}. Configuration loading/saving might be disabled for this path."
                )

        # Build internal settings and sections based on the instance schema (recursive)
        self._build_internal_structure_from_schema(
            self._instance_schema_definition, self._settings, self
        )

        # Load initial config if path and handler are valid
        if self._config_path and self._handler:
            try:
                self.load()  # Initial load attempt
            except FileNotFoundError:
                log.warning(
                    f"Configuration file {self._config_path} not found. Initializing with defaults."
                )
            except (HandlerError, EncryptionError, ValidationError, SchemaError) as e:
                log.error(
                    f"Failed to load initial configuration from {self._config_path}: {e}. Continuing with defaults where applicable."
                )
            except Exception as e:
                log.error(
                    f"Unexpected error loading initial configuration from {self._config_path}: {e}",
                    exc_info=True,
                )
        else:
            log.info(
                "No valid config_path/handler setup, or file not found. Initializing with default values."
            )

        log.info(
            f"ConfigGuard initialized successfully (Instance Version: {self.version})."
        )

    # --- Autosave Trigger Method ---
    def _trigger_autosave(self, setting_name: str) -> None:
        """Internal helper to trigger autosave if enabled and possible."""
        if self._autosave:
            log.debug(
                f"Autosaving configuration (values) due to change in '{setting_name}'..."
            )
            if self._handler and self._config_path:
                try:
                    self.save(mode="values")
                except (HandlerError, EncryptionError) as e:
                    log.error(f"Autosave failed: {e}")
                except Exception as e:
                    log.error(f"Unexpected error during autosave: {e}", exc_info=True)
            else:
                log.warning(
                    f"Autosave for '{setting_name}' skipped: No valid handler or config_path."
                )

    def _load_schema_definition(
        self, schema_input: typing.Union[dict, str, Path]
    ) -> dict:
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
            return copy.deepcopy(schema_input)  # Return a copy
        elif isinstance(schema_input, (str, Path)):
            schema_path = Path(schema_input)
            log.debug(f"Loading schema definition from file: {schema_path}")
            if not schema_path.exists():
                raise SchemaError(f"Schema file not found: {schema_path}")
            if schema_path.suffix.lower() != ".json":
                raise SchemaError(
                    f"Schema file must be a JSON file (.json extension). Found: {schema_path.suffix}"
                )
            try:
                temp_json_handler = JsonHandler(fernet=None)
                load_result = temp_json_handler.load(schema_path)
                raw_schema = load_result["values"]
                if not isinstance(raw_schema, dict):
                    raise SchemaError(
                        f"Schema file {schema_path} does not contain a valid JSON object at the root."
                    )
                log.info(f"Successfully loaded schema definition from {schema_path}")
                return raw_schema
            except (HandlerError, FileNotFoundError) as e:
                raise SchemaError(
                    f"Failed to load schema definition from {schema_path}: {e}"
                ) from e
            except Exception as e:
                raise SchemaError(
                    f"Unexpected error loading schema from file {schema_path}: {e}"
                ) from e
        else:
            raise TypeError(
                "Schema input must be a dictionary or a file path (str or Path)."
            )

    def _build_internal_structure_from_schema(
        self,
        schema_definition: dict,
        target_container: typing.Dict[str, typing.Union[ConfigSetting, ConfigSection]],
        parent: typing.Union["ConfigGuard", ConfigSection],
    ) -> None:
        """
        Recursively parses the schema definition and creates ConfigSetting or ConfigSection objects.

        Args:
            schema_definition: The part of the schema to process (a dictionary).
            target_container: The dictionary (e.g., self._settings or section._settings)
                              to populate with created objects.
            parent: The parent object (either the ConfigGuard instance or the parent ConfigSection)
                    needed for context like autosave triggering.
        """
        log.debug(
            f"Building structure for schema level with keys: {list(schema_definition.keys())}"
        )
        for name, definition in schema_definition.items():
            if not isinstance(definition, dict):
                raise SchemaError(
                    f"Invalid schema format for '{name}'. Definition must be a dictionary."
                )

            item_type_str = definition.get("type")

            try:
                if item_type_str == self.SECTION_TYPE_KEY:
                    # It's a section
                    log.debug(f"Creating ConfigSection for '{name}'...")
                    nested_schema = definition.get("schema")
                    if not isinstance(nested_schema, dict):
                        raise SchemaError(
                            f"Section '{name}' must contain a 'schema' dictionary."
                        )
                    section = ConfigSection(
                        name=name, schema_definition=nested_schema, parent=parent
                    )
                    target_container[name] = section
                    # Recursively build the section's internal structure
                    self._build_internal_structure_from_schema(
                        nested_schema, section._settings, section
                    )

                elif item_type_str in SUPPORTED_TYPES:
                    # It's a setting
                    log.debug(f"Creating ConfigSetting for '{name}'...")
                    schema = SettingSchema(name, definition)
                    # Pass parent reference for autosave triggering
                    setting = ConfigSetting(schema, parent=parent)
                    target_container[name] = setting
                else:
                    # Invalid type
                    valid_types = list(SUPPORTED_TYPES.keys()) + [self.SECTION_TYPE_KEY]
                    raise SchemaError(
                        f"Invalid or missing 'type' ('{item_type_str}') for '{name}'. Must be one of {valid_types}."
                    )
            except SchemaError as e:
                log.error(f"Schema error processing '{name}': {e}")
                raise  # Propagate schema errors during initialization
            except Exception as e:
                log.error(f"Unexpected error processing schema item '{name}': {e}")
                raise SchemaError(
                    f"Unexpected error building structure for '{name}'."
                ) from e

        log.debug("Finished building structure level.")

    def load(self, filepath: typing.Optional[typing.Union[str, Path]] = None) -> None:
        """
        Loads configuration using the configured handler. Handles versioning, migration, and nesting.
        """
        load_path = Path(filepath) if filepath else self._config_path
        current_handler = self._handler

        if not load_path:
            raise HandlerError("No configuration file path specified for loading.")
        if not current_handler:
            raise HandlerError(
                f"No valid handler available for the configured path: {self._config_path}"
            )

        log.info(
            f"Attempting to load configuration from: {load_path} using {current_handler.__class__.__name__}"
        )

        try:
            loaded_data: LoadResult = current_handler.load(load_path)

            loaded_version_str = loaded_data.get("version")
            loaded_schema_dict = loaded_data.get("schema")
            loaded_values_dict = loaded_data.get("values")

            if loaded_values_dict is None or not isinstance(
                loaded_values_dict, Mapping
            ):
                log.error(
                    f"Handler did not return a valid dictionary/mapping for 'values' from {load_path}"
                )
                raise HandlerError(f"Invalid 'values' data loaded from {load_path}")

            self.loaded_file_version = loaded_version_str
            log.info(
                f"File loaded. Version in file: {loaded_version_str or 'N/A'}. Instance version: {self.version}."
            )

            # Version Comparison and Migration Logic
            allow_migration = False
            load_mode_desc = "values only or legacy"
            if loaded_version_str is not None:
                load_mode_desc = f"full state (v{loaded_version_str})"
                try:
                    loaded_ver = parse_version(loaded_version_str)
                    instance_ver = parse_version(self.version)
                    if loaded_ver > instance_ver:
                        log.error(
                            f"Loaded config version ({loaded_ver}) is NEWER than instance version ({instance_ver})."
                        )
                        raise SchemaError(
                            f"Cannot load configuration: File version {loaded_ver} is newer than instance version {instance_ver}."
                        )
                    elif loaded_ver < instance_ver:
                        log.warning(
                            f"Loaded config version ({loaded_ver}) is OLDER than instance version ({instance_ver}). Enabling migration logic."
                        )
                        allow_migration = True
                    else:
                        log.info(f"Configuration versions match ({instance_ver}).")
                        if (
                            loaded_schema_dict
                            and loaded_schema_dict != self._instance_schema_definition
                        ):
                            log.warning(
                                "Loaded schema definition differs from instance schema definition, but versions match. Using instance schema for validation."
                            )
                except InvalidVersion as e:
                    log.error(
                        f"Invalid version format found in loaded file ('{loaded_version_str}'): {e}"
                    )
                    raise SchemaError(
                        f"Invalid version format in loaded file: {loaded_version_str}"
                    ) from e
            else:
                log.warning(
                    "Loaded configuration file has no version information. Applying values directly."
                )

            # Apply values using the recursive helper method
            log.info(f"Applying loaded values from '{load_mode_desc}' file...")
            # Pass ignore_unknown=False because load should respect the schema strictly
            # (Migration handles skipping old keys, other unknowns are errors)
            self._apply_and_migrate_values(
                current_container=self._settings,
                current_schema_level=self._instance_schema_definition,
                loaded_values_level=loaded_values_dict,
                loaded_schema_level=loaded_schema_dict,
                allow_migration=allow_migration,
                ignore_unknown=False,  # Load is strict by default
                path_prefix="",
            )

        except FileNotFoundError:
            log.warning(f"Load failed: File not found at {load_path}")
            raise
        except (
            HandlerError,
            EncryptionError,
            ValidationError,
            SchemaError,
            SettingNotFoundError,
        ) as e:  # Added SettingNotFoundError
            log.error(f"Failed to load/process configuration from {load_path}: {e}")
            raise
        except Exception as e:
            log.error(
                f"An unexpected error occurred during loading from {load_path}: {e}",
                exc_info=True,
            )
            raise HandlerError(f"Unexpected error loading configuration: {e}") from e

    def _apply_and_migrate_values(
        self,
        current_container: typing.Dict[str, typing.Union[ConfigSetting, ConfigSection]],
        current_schema_level: dict,
        loaded_values_level: Mapping,
        loaded_schema_level: typing.Optional[Mapping],
        allow_migration: bool,
        ignore_unknown: bool,  # Added flag
        path_prefix: str = "",
    ) -> None:
        """
        Recursively applies loaded values, handling schema differences, coercion, migration, and unknown keys.

        Args:
            current_container: The dict (_settings) of the current level.
            current_schema_level: The schema definition dict for the current level.
            loaded_values_level: Dictionary of values loaded from the file for the current level.
            loaded_schema_level: Schema loaded from the file (if any) for the current level.
            allow_migration: True if loaded version is older than instance version.
            ignore_unknown: If False, raise SettingNotFoundError for keys in loaded_values_level
                            not defined in current_schema_level (unless allow_migration is True).
            path_prefix: String prefix for logging the path of the setting/section.
        """
        applied_count = 0
        skipped_validation = 0
        skipped_migration = 0
        coercion_warnings = 0
        processed_keys = set()

        log.debug(
            f"Applying values at level '{path_prefix or 'root'}' (Migration: {allow_migration}, IgnoreUnknown: {ignore_unknown}, Loaded Schema: {loaded_schema_level is not None})..."
        )

        # Iterate through the settings/sections defined in the *current instance* structure
        for name, current_item in current_container.items():
            full_path = f"{path_prefix}{name}"

            if isinstance(current_item, ConfigSetting):
                current_schema = current_item.schema

                if name in loaded_values_level:
                    processed_keys.add(name)
                    loaded_value = loaded_values_level[name]
                    value_to_validate = loaded_value
                    source_type_str = None

                    # Type Coercion Logic
                    if loaded_schema_level and name in loaded_schema_level:
                        loaded_item_schema_info = loaded_schema_level.get(name, {})
                        if isinstance(loaded_item_schema_info, dict):
                            loaded_type_str = loaded_item_schema_info.get("type")
                            source_type_str = loaded_type_str
                            if (
                                loaded_type_str
                                and loaded_type_str != current_schema.type_str
                            ):
                                log.warning(
                                    f"Type mismatch for '{full_path}': Instance expects '{current_schema.type_str}', file had '{loaded_type_str}'. Attempting coercion..."
                                )
                                coerced_value = _try_coerce(
                                    loaded_value,
                                    current_schema.type,
                                    source_type_str=loaded_type_str,
                                )
                                if coerced_value is not loaded_value:
                                    log.info(
                                        f"Coerced '{full_path}' value from {type(loaded_value).__name__} to {type(coerced_value).__name__}."
                                    )
                                    value_to_validate = coerced_value
                                else:
                                    log.warning(
                                        f"Coercion from '{loaded_type_str}' to '{current_schema.type_str}' did not succeed for '{full_path}' (value: {loaded_value!r}). Proceeding with original value."
                                    )
                                    coercion_warnings += 1
                        else:
                            log.debug(
                                f"No type information found in loaded schema for '{full_path}'. Skipping coercion."
                            )

                    # Validation against *instance* schema
                    try:
                        current_item.value = value_to_validate
                        applied_count += 1
                        log.debug(
                            f"Successfully applied value for '{full_path}': {current_item.value!r}"
                        )
                    except ValidationError as e:
                        skipped_validation += 1
                        log.warning(
                            f"Validation failed for '{full_path}' with value '{value_to_validate!r}' (original loaded: '{loaded_value!r}'): {e}. RESETTING to instance default."
                        )
                        try:
                            current_item.value = current_schema.default_value
                        except ValidationError as e_default:
                            log.error(
                                f"CRITICAL: Default value for '{full_path}' is invalid: {e_default}."
                            )
                else:
                    log.debug(
                        f"'{full_path}' not found in loaded values. Using instance default: {current_item.value!r}"
                    )

            elif isinstance(current_item, ConfigSection):
                processed_keys.add(name)
                nested_loaded_values = loaded_values_level.get(name)
                nested_loaded_schema = (
                    loaded_schema_level.get(name, {}).get("schema")
                    if loaded_schema_level
                    and isinstance(loaded_schema_level.get(name), dict)
                    else None
                )

                if isinstance(nested_loaded_values, Mapping):
                    log.debug(f"Recursing into section '{full_path}'...")
                    self._apply_and_migrate_values(
                        current_container=current_item._settings,
                        current_schema_level=current_schema_level[name].get(
                            "schema", {}
                        ),
                        loaded_values_level=nested_loaded_values,
                        loaded_schema_level=nested_loaded_schema,
                        allow_migration=allow_migration,
                        ignore_unknown=ignore_unknown,  # Pass flag down
                        path_prefix=f"{full_path}.",
                    )
                elif name in loaded_values_level:
                    log.warning(
                        f"Expected dictionary/mapping for section '{full_path}' in loaded values, but got {type(nested_loaded_values).__name__}. Skipping section."
                    )
                else:
                    log.debug(
                        f"Section '{full_path}' not found in loaded values. Using instance defaults."
                    )

        # Check for keys in loaded_values that are not in the instance structure at this level
        unknown_or_migrated_keys = set(loaded_values_level.keys()) - processed_keys
        skipped_unknown = 0
        for key in unknown_or_migrated_keys:
            full_unknown_path = f"{path_prefix}{key}"
            if allow_migration:
                skipped_migration += 1
                log.warning(
                    f"Migration: Item '{full_unknown_path}' (value: {loaded_values_level[key]!r}) loaded from older version is not present in current instance version ({self.version}). Skipping."
                )
            elif (
                not ignore_unknown
            ):  # Raise error if not ignoring unknowns and not migrating
                log.error(
                    f"Unknown item '{full_unknown_path}' found in input data and ignore_unknown=False."
                )
                raise SettingNotFoundError(
                    f"Unknown setting/section encountered: '{full_unknown_path}'"
                )
            else:  # Ignore unknown
                skipped_unknown += 1
                log.warning(
                    f"Item '{full_unknown_path}' found in loaded file/data but not defined in current instance schema level. Ignoring (ignore_unknown=True)."
                )

        # Log summary only if counts are non-zero for clarity
        summary_parts = []
        if applied_count:
            summary_parts.append(f"Applied: {applied_count}")
        if skipped_validation:
            summary_parts.append(f"Skipped (validation): {skipped_validation}")
        if skipped_migration:
            summary_parts.append(f"Skipped (migration): {skipped_migration}")
        if skipped_unknown:
            summary_parts.append(f"Skipped (unknown): {skipped_unknown}")
        if coercion_warnings:
            summary_parts.append(f"Coercion Warnings: {coercion_warnings}")

        if summary_parts:
            log.info(
                f"Value application finished for level '{path_prefix or 'root'}'. "
                + ", ".join(summary_parts)
                + "."
            )
        else:
            log.debug(
                f"Value application finished for level '{path_prefix or 'root'}'. No changes or issues."
            )

    def save(
        self,
        filepath: typing.Optional[typing.Union[str, Path]] = None,
        mode: str = "values",
    ) -> None:
        """
        Saves the configuration using the configured handler and specified mode. Handles nesting.

        Args:
            filepath: Optional path to save to. Overrides the instance's config_path.
            mode: Specifies what to save ('values' or 'full').
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
            raise HandlerError(
                f"No valid handler available for the configured path: {self._config_path}"
            )

        if mode not in ["values", "full"]:
            raise ValueError(
                f"Invalid save mode: '{mode}'. Must be 'values' or 'full'."
            )

        log.info(
            f"Saving configuration to: {save_path} using {current_handler.__class__.__name__} (mode: {mode})"
        )

        try:
            # Prepare data payload using recursive methods
            config_values = self.get_config_dict()  # Recursive method
            schema_definition = (
                self.get_instance_schema_definition()
            )  # Already handles nesting

            data_payload = {
                "instance_version": self.version,
                "schema_definition": schema_definition,
                "config_values": config_values,
            }

            # Call handler's save method
            current_handler.save(save_path, data=data_payload, mode=mode)

        except (HandlerError, EncryptionError, ValueError) as e:
            log.error(f"Failed to save configuration to {save_path} (mode={mode}): {e}")
            raise
        except Exception as e:
            log.error(
                f"An unexpected error occurred during saving to {save_path} (mode={mode}): {e}",
                exc_info=True,
            )
            raise HandlerError(f"Unexpected error saving configuration: {e}") from e

    # --- Public Data Access Methods (Updated for Nesting) ---

    def get_instance_schema_definition(self) -> dict:
        """Returns the schema definition used by this ConfigGuard instance (excludes version key)."""
        # self._instance_schema_definition is already the potentially nested schema
        return copy.deepcopy(self._instance_schema_definition)

    def get_config_dict(self) -> dict:
        """Returns the current configuration values as a potentially nested dictionary."""
        config_dict = {}
        for name, item in self._settings.items():
            if isinstance(item, ConfigSetting):
                config_dict[name] = item.value
            elif isinstance(item, ConfigSection):
                # Recursively get the dictionary for the section
                config_dict[name] = item.get_config_dict()
        return config_dict

    def export_schema_with_values(self) -> dict:
        """
        Exports the *current* state (instance schema + values, including nested structures)
        for external use (e.g., UI).

        Returns:
            A dictionary containing 'version', 'schema', and 'settings'.
            The 'settings' dict maps names to {'schema': ..., 'value': ...}, where
            'value' can be a nested dictionary for sections.
        """
        log.debug("Recursively exporting current instance schema with values...")
        settings_export = {}
        # Use internal recursive helper
        self._export_level(self._settings, settings_export)

        full_export = {
            "version": self.version,
            "schema": self.get_instance_schema_definition(),  # Full nested schema
            "settings": settings_export,  # Structured settings/values
        }
        log.debug(f"Generated export for instance version {self.version}.")
        return full_export

    def _export_level(self, container: dict, export_target: dict) -> None:
        """Recursive helper for export_schema_with_values."""
        for name, item in container.items():
            if isinstance(item, ConfigSetting):
                export_target[name] = {
                    "schema": item.schema.to_dict(),
                    "value": item.value,  # Export the actual value
                }
            elif isinstance(item, ConfigSection):
                # Get the section's schema and recursively get its values dict
                nested_values_dict = item.get_config_dict()  # Get nested values
                export_target[name] = {
                    "schema": item.get_schema_dict(),  # Section's schema part
                    "value": nested_values_dict,  # Export the nested dictionary of values
                }

    def import_config(self, data: Mapping, ignore_unknown: bool = True) -> None:
        """
        Imports configuration *values* from a potentially nested dictionary,
        validating against the instance schema.

        Args:
            data: A dictionary (potentially nested) of {setting_name: value} or {section_name: {sub_setting: value}}.
            ignore_unknown: If True (default), ignores keys/sections in `data` not present in the instance schema.
                            If False, raises SettingNotFoundError for unknown keys/sections.
        """
        if not isinstance(data, Mapping):
            raise TypeError(
                f"Input data for import_config must be a dictionary or mapping, got {type(data).__name__}"
            )

        log.info(
            f"Importing configuration values from dictionary ({len(data)} top-level items)..."
        )
        try:
            # Use the recursive apply method, passing the ignore_unknown flag
            self._apply_and_migrate_values(
                current_container=self._settings,
                current_schema_level=self._instance_schema_definition,
                loaded_values_level=data,
                loaded_schema_level=None,
                allow_migration=False,
                ignore_unknown=ignore_unknown,  # Pass the flag
                path_prefix="",
            )
            # No need for separate top-level unknown check, handled recursively

        except ValidationError as e:
            log.error(
                f"Validation errors occurred during import. See previous warnings. Last error detail: {e}"
            )
        except SettingNotFoundError as e:
            # This will be raised by _apply_and_migrate_values if ignore_unknown=False
            log.error(f"Import failed due to unknown setting/section: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error during dictionary import: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error during dictionary import: {e}") from e

        log.info("Dictionary import finished.")

    # --- Magic methods (Updated for Nesting) ---

    def __getattr__(self, name: str) -> typing.Any:
        """Allows accessing settings/sections like attributes (e.g., config.port, config.section)."""
        if name.startswith("_"):  # Allow internal attribute access
            return super().__getattribute__(name)

        is_schema_access = name.startswith("sc_")
        actual_name = name[3:] if is_schema_access else name

        if actual_name in self._settings:
            item = self._settings[actual_name]
            if is_schema_access:
                if isinstance(item, ConfigSetting):
                    return item.schema
                elif isinstance(item, ConfigSection):
                    # Return the section's schema definition dictionary
                    return item.get_schema_dict()
            elif isinstance(item, ConfigSetting):
                return item.value
            elif isinstance(item, ConfigSection):
                # Return the section object itself for further attribute access
                return item
        else:
            try:
                # Check for actual methods/attributes like 'version', 'load', 'save' etc.
                return super().__getattribute__(name)
            except AttributeError:
                prefix = (
                    "schema attribute"
                    if is_schema_access
                    else "attribute or setting/section"
                )
                raise AttributeError(
                    f"'{type(self).__name__}' object has no {prefix} '{name}'"
                ) from None

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Allows setting top-level settings like attributes (e.g., config.port = 8080)."""
        # Prevent setting schema attributes directly
        if name.startswith("sc_"):
            raise AttributeError(
                "Cannot set schema attributes directly (use 'config.sc_name' to access)."
            )

        # Handle internal attributes
        known_internals = {
            "_settings",
            "_raw_instance_schema",
            "_instance_schema_definition",
            "version",
            "_config_path",
            "_handler",
            "_fernet",
            "_autosave",
            "loaded_file_version",
        }
        if name.startswith("_") or name in known_internals or hasattr(type(self), name):
            super().__setattr__(name, value)
        # Handle setting top-level ConfigSettings
        elif name in self._settings and isinstance(self._settings[name], ConfigSetting):
            setting = self._settings[name]
            try:
                # Delegate to ConfigSetting's setter (handles validation, coercion, autosave trigger)
                setting.value = value
                # Autosave is triggered within ConfigSetting's setter via parent reference
            except ValidationError as e:
                raise e  # Propagate validation errors
        # Handle attempting to set a ConfigSection via attribute (Disallow direct assignment)
        elif name in self._settings and isinstance(self._settings[name], ConfigSection):
            raise AttributeError(
                f"Cannot assign directly to section '{name}'. Modify settings within the section (e.g., config.{name}.setting = value)."
            )
        else:
            # Block setting arbitrary (non-internal, non-setting, non-section) attributes
            raise AttributeError(
                f"Cannot set attribute '{name}'. It's not a defined top-level setting or internal attribute."
            )

    def __getitem__(self, key: str) -> typing.Any:
        """Allows accessing settings/sections like dictionary items (e.g., config['port'], config['section'])."""
        is_schema_access = key.startswith("sc_")
        actual_key = key[3:] if is_schema_access else key

        if actual_key in self._settings:
            item = self._settings[actual_key]
            if is_schema_access:
                if isinstance(item, ConfigSetting):
                    return item.schema
                elif isinstance(item, ConfigSection):
                    return item.get_schema_dict()  # Return schema dict for section
            elif isinstance(item, ConfigSetting):
                return item.value
            elif isinstance(item, ConfigSection):
                # Return the section object itself for further item access config['section']['setting']
                return item
        else:
            prefix = (
                "Schema for setting/section"
                if is_schema_access
                else "Setting or section"
            )
            raise SettingNotFoundError(f"{prefix} '{actual_key}' not found.")

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """Allows setting top-level settings like dictionary items (e.g., config['port'] = 8080)."""
        if key.startswith("sc_"):
            raise KeyError(
                "Cannot set schema items directly (use config['sc_name'] to access)."
            )

        if key in self._settings:
            item = self._settings[key]
            if isinstance(item, ConfigSetting):
                try:
                    # Delegate to ConfigSetting's setter (handles validation, coercion, autosave trigger)
                    item.value = value
                except ValidationError as e:
                    raise e  # Propagate validation errors
            elif isinstance(item, ConfigSection):
                raise TypeError(
                    f"Cannot assign directly to section '{key}'. Modify settings within the section (e.g., config['{key}']['setting'] = value)."
                )
        else:
            raise SettingNotFoundError(
                f"Setting '{key}' not found. Cannot set undefined top-level settings."
            )

    def __delitem__(self, key: str) -> None:
        """Prevent deleting settings or sections."""
        raise TypeError("Deleting configuration settings or sections is not supported.")

    def __iter__(self) -> typing.Iterator[str]:
        """Iterates over the names of the top-level defined settings and sections."""
        return iter(self._settings.keys())

    def __len__(self) -> int:
        """Returns the number of top-level defined settings and sections."""
        return len(self._settings)

    def __contains__(self, key: object) -> bool:
        """Checks if a top-level setting or section name exists."""
        return isinstance(key, str) and key in self._settings

    def __repr__(self) -> str:
        """Returns a developer-friendly representation of the ConfigGuard instance."""
        path_str = f"'{self._config_path}'" if self._config_path else "None"
        handler_name = self._handler.__class__.__name__ if self._handler else "None"
        encrypted_str = ", encrypted" if self._fernet else ""
        num_items = len(self._settings)
        item_types = {"settings": 0, "sections": 0}
        for item in self._settings.values():
            if isinstance(item, ConfigSetting):
                item_types["settings"] += 1
            elif isinstance(item, ConfigSection):
                item_types["sections"] += 1

        return (
            f"ConfigGuard(version='{self.version}', config_path={path_str}, "
            f"handler='{handler_name}', top_level_items={num_items} "
            f"(settings={item_types['settings']}, sections={item_types['sections']})"
            f"{encrypted_str})"
        )

    # Ensure MutableMapping abstract methods are implemented if not covered
    # keys(), items(), values() could be added for convenience if needed,
    # iterating over top-level items.
    # Example:
    # def keys(self): return self._settings.keys()
    # def items(self): return # Need careful implementation for sections
    # def values(self): return # Need careful implementation for sections
