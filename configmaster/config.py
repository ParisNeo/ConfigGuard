import typing
from pathlib import Path
import copy
from collections.abc import MutableMapping
import json # Import json here as it's used in load/save

from .schema import SettingSchema
from .setting import ConfigSetting
from .handlers import get_handler, StorageHandler
from .exceptions import SchemaError, ValidationError, HandlerError, SettingNotFoundError, EncryptionError # Ensure EncryptionError is imported
from .log import log

class ConfigMaster(MutableMapping):
    """
    Main class for managing application configurations.
    """

    def __init__(self,
                 schema: typing.Union[dict, str, Path],
                 config_path: typing.Optional[typing.Union[str, Path]] = None,
                 encryption_key: typing.Optional[bytes] = None,
                 autosave: bool = False):
        """
        Initializes the ConfigMaster instance.

        Args:
            schema: The configuration schema. Can be a dictionary defining the schema
                    or a path (str or Path) to a file containing the schema (JSON format).
            config_path: Optional path (str or Path) to the configuration file to load/save.
                         If provided, the configuration will be loaded automatically on init.
                         The file type is determined by the extension.
            encryption_key: Optional bytes key for encrypting/decrypting the config file.
                            Requires the 'cryptography' library.
            autosave: If True, automatically save the configuration whenever a setting is changed.
                      Defaults to False.
        """
        log.info("Initializing ConfigMaster...")
        self._settings: typing.Dict[str, ConfigSetting] = {}
        self._schema_definition: dict = self._load_schema_definition(schema)
        self._config_path: typing.Optional[Path] = Path(config_path) if config_path else None
        self._handler: typing.Optional[StorageHandler] = None
        self._encryption_key: typing.Optional[bytes] = encryption_key
        self._fernet = None # Fernet instance for encryption
        self._autosave = autosave

        if self._encryption_key:
            self._initialize_encryption()

        if self._config_path:
            if self._fernet:
                # If encryption is ON, we don't need a standard handler for the specific
                # file extension immediately. Load/save will handle bytes.
                # We still need to know the underlying format for serialization *before* encryption.
                # For now, we'll assume JSON is used internally before encryption/after decryption.
                log.info(f"Encryption is enabled for {self._config_path}. Direct byte I/O will be used.")
                # No need to set self._handler in this case.
            else:
                # If encryption is OFF, get the handler based on the file extension.
                try:
                    self._handler = get_handler(self._config_path)
                    log.info(f"Using handler '{self._handler.__class__.__name__}' for file: {self._config_path}")
                except HandlerError as e:
                    # If no handler found (and not encrypted), disable loading/saving.
                    log.warning(f"{e}. Configuration loading/saving will be disabled for this path.")
                    # Set path to None to prevent load/save attempts later? Or just leave handler as None?
                    # Leaving handler as None is sufficient, load/save check for it.
                    pass # Keep _config_path, but self._handler remains None
        self._build_settings_from_schema()

        # Adjust loading condition: Load if path exists AND (a handler is set OR encryption is active)
        if self._config_path and (self._handler or self._fernet):
            try:
                self.load() # Load initial config
            except FileNotFoundError:
                 log.warning(f"Configuration file {self._config_path} not found. Initializing with defaults.")
                 # No need to call _build_settings_from_schema again, it already ran.
            except (HandlerError, EncryptionError, ValidationError) as e:
                 # Log potentially critical errors during initial load but allow init to finish
                 log.error(f"Failed to load initial configuration from {self._config_path}: {e}. Continuing with defaults where applicable.")
            except Exception as e:
                 log.error(f"Unexpected error loading initial configuration from {self._config_path}: {e}", exc_info=True)

        else:
             log.info("No valid config_path/handler/encryption setup, or file not found. Initializing with default values.")

        log.info("ConfigMaster initialized successfully.")


    def _load_schema_definition(self, schema_input: typing.Union[dict, str, Path]) -> dict:
        """Loads the schema definition from a dict or file."""
        if isinstance(schema_input, dict):
            log.debug("Loading schema from dictionary.")
            return copy.deepcopy(schema_input) # Work with a copy
        elif isinstance(schema_input, (str, Path)):
            schema_path = Path(schema_input)
            log.debug(f"Loading schema from file: {schema_path}")
            if not schema_path.exists():
                raise SchemaError(f"Schema file not found: {schema_path}")
            if schema_path.suffix.lower() != ".json":
                 raise SchemaError(f"Schema file must be a JSON file (.json extension). Found: {schema_path.suffix}")
            try:
                # Use JsonHandler internally to load schema file
                json_handler = get_handler(schema_path)
                return json_handler.load(schema_path)
            except Exception as e:
                raise SchemaError(f"Failed to load schema from file {schema_path}: {e}") from e
        else:
            raise TypeError("Schema must be a dictionary or a file path (str or Path).")

    def _initialize_encryption(self):
        """Initializes the Fernet instance if a key is provided."""
        if not self._encryption_key:
            return
        try:
            from cryptography.fernet import Fernet
            self._fernet = Fernet(self._encryption_key)
            log.info("Encryption enabled.")
        except ImportError:
            log.error("The 'cryptography' library is required for encryption but not installed.")
            log.error("Please install it: pip install cryptography")
            self._encryption_key = None # Disable encryption
            raise ImportError("Cryptography library not found, needed for encryption.")
        except Exception as e:
             log.error(f"Failed to initialize encryption: {e}")
             self._encryption_key = None # Disable encryption
             raise SchemaError(f"Invalid encryption key provided: {e}")

    def _build_settings_from_schema(self):
        """Parses the schema definition and creates ConfigSetting objects."""
        log.debug("Building ConfigSetting objects from schema definition...")
        if not isinstance(self._schema_definition, dict):
            raise SchemaError("Invalid schema format: Root must be a dictionary.")

        self._settings = {}
        for name, definition in self._schema_definition.items():
            try:
                schema = SettingSchema(name, definition)
                self._settings[name] = ConfigSetting(schema)
                log.debug(f"Created ConfigSetting for '{name}'.")
            except SchemaError as e:
                log.error(f"Schema error for setting '{name}': {e}")
                raise e # Propagate schema errors during initialization
        log.debug("Finished building ConfigSetting objects.")

    def _encrypt(self, data: bytes) -> bytes:
        """Encrypts data using the Fernet instance."""
        if not self._fernet:
            raise SchemaError("Encryption key not configured for encryption.")
        return self._fernet.encrypt(data)

    def _decrypt(self, token: bytes) -> bytes:
        """Decrypts data using the Fernet instance."""
        if not self._fernet:
            raise SchemaError("Encryption key not configured for decryption.")
        try:
            return self._fernet.decrypt(token)
        except Exception as e:
            log.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt configuration data: {e}") from e

    def load(self, filepath: typing.Optional[typing.Union[str, Path]] = None):
        """
        Loads configuration from the specified file or the default config_path.
        Handles encrypted files and missing files gracefully.

        Args:
            filepath: Optional path to load from. Overrides the instance's config_path.

        Raises:
            HandlerError: If loading fails or no handler is available for an existing, unencrypted file.
            ValidationError: If loaded data fails validation against the schema.
            EncryptionError: If decryption fails.
        """
        load_path = Path(filepath) if filepath else self._config_path
        if not load_path:
            # This might happen if called manually without a path set during init
            raise HandlerError("No configuration file path specified for loading.")

        log.info(f"Attempting to load configuration from: {load_path}")

        # Check if the file exists first
        if not load_path.exists():
            log.warning(f"Configuration file {load_path} not found. Current settings remain defaults.")
            # No error needed here, just return as defaults are already set.
            return # Nothing to load

        # --- File exists, proceed ---
        handler: typing.Optional[StorageHandler] = None
        load_method_info = f"Loading existing file: {load_path}"

        if self._fernet:
             # If encrypted, we don't need a format-specific handler for loading the bytes
             load_method_info += " (encrypted)"
        else:
            # Not encrypted, we need a handler based on the file extension
            try:
                handler = get_handler(load_path)
                load_method_info += f" using {handler.__class__.__name__}"
            except HandlerError as e:
                # If file exists but no handler (and not encrypted), it's an error
                log.error(f"Cannot load existing file {load_path}: No handler found and encryption is off: {e}")
                raise e # Re-raise error

        log.info(load_method_info) # Log how we intend to load

        try:
            # Read raw bytes from the existing file
            with open(load_path, 'rb') as f:
                raw_data = f.read()

            loaded_values: dict = {} # Initialize empty dict for loaded key-value pairs

            if self._fernet:
                # Decrypt the raw data
                log.debug("Decrypting configuration data...")
                try:
                    decrypted_data_bytes = self._decrypt(raw_data)
                    # Assume decrypted data is JSON string for now.
                    # TODO: Make internal serialization format configurable or based on original extension?
                    try:
                        loaded_values = json.loads(decrypted_data_bytes.decode('utf-8'))
                        if not isinstance(loaded_values, dict):
                            raise ValueError("Decrypted data is not a dictionary.")
                        log.debug("Decryption and JSON parsing successful.")
                    except Exception as json_e:
                        log.error(f"Failed to parse decrypted data as JSON: {json_e}")
                        raise HandlerError(f"Failed parsing decrypted data: {json_e}")
                except EncryptionError as enc_e:
                     # Propagate decryption specific errors
                     raise enc_e

            elif handler:
                # Use the determined handler to load data from the path
                # Note: Handler re-reads the file, less efficient but fits current StorageHandler API.
                log.debug(f"Using handler {handler.__class__.__name__} to parse the file content.")
                try:
                    # The handler's load method should return a dictionary
                    loaded_values = handler.load(load_path)
                    if not isinstance(loaded_values, dict):
                         log.error(f"Handler {handler.__class__.__name__} for {load_path} did not return a dictionary.")
                         raise HandlerError(f"Handler {handler.__class__.__name__} returned invalid type: {type(loaded_values).__name__}")
                except FileNotFoundError:
                     # Should not happen as we checked existence, but handle defensively
                     log.error(f"Handler failed to find file {load_path} even though it exists.")
                     raise HandlerError(f"Inconsistent file state for {load_path}")
            else:
                 # This state (exists, not encrypted, no handler) should have been caught above.
                 log.error(f"Internal load logic error: Reached unexpected state for existing file {load_path}.")
                 raise HandlerError(f"Cannot load {load_path}: Inconsistent state.")

            # --- Validate and update settings from loaded_values dictionary ---
            log.debug("Validating and applying loaded configuration values...")
            loaded_settings_count = 0
            skipped_settings = []
            for name, value in loaded_values.items():
                if name in self._settings:
                    try:
                        # Use the setter which includes validation and coercion
                        self._settings[name].value = value
                        loaded_settings_count += 1
                    except ValidationError as e:
                        log.warning(f"Validation failed for loaded setting '{name}' with value '{value}': {e}. Using default or previous value.")
                        # Value remains unchanged (default or previous loaded value)
                else:
                    skipped_settings.append(name)

            if skipped_settings:
                 log.warning(f"Ignoring unknown settings found in config file: {', '.join(skipped_settings)}")

            log.info(f"Successfully loaded and applied {loaded_settings_count} setting(s) from {load_path}.")

        except (HandlerError, EncryptionError, ValidationError) as e:
             # Log and re-raise known ConfigMaster error types
             log.error(f"Failed to load configuration from {load_path}: {e}")
             raise e
        except Exception as e:
            # Catch any other unexpected exceptions during the loading process
            log.error(f"An unexpected error occurred during loading from {load_path}: {e}", exc_info=True)
            raise HandlerError(f"Unexpected error loading configuration: {e}") from e

    def save(self, filepath: typing.Optional[typing.Union[str, Path]] = None):
        """
        Saves the current configuration to the specified file or the default config_path.
        Handles encryption if configured.

        Args:
            filepath: Optional path to save to. Overrides the instance's config_path.

        Raises:
            HandlerError: If saving fails (e.g., no handler available for unencrypted save, serialization issues).
            EncryptionError: If encryption fails.
        """
        save_path = Path(filepath) if filepath else self._config_path
        if not save_path:
            raise HandlerError("No configuration file path specified for saving.")

        # We don't technically need the handler instance itself for saving if encrypting,
        # as we write raw bytes. But we log the intent.
        save_method_info = f"Saving configuration to: {save_path}"
        if self._fernet:
             save_method_info += " (encrypted)"
        else:
             # If not encrypting, check if a handler is available for the path.
             # This check prevents saving to an unsupported file type when not encrypting.
             try:
                 # This call just checks if a handler exists, doesn't store it
                 handler_class_name = get_handler(save_path).__class__.__name__
                 save_method_info += f" using inferred handler {handler_class_name}"
             except HandlerError as e:
                  log.error(f"Cannot save to {save_path} (unencrypted): {e}")
                  raise e # Re-raise error if no handler and not encrypting

        log.info(save_method_info)

        try:
            # Get the current configuration values as a dictionary
            config_data = self.get_config_dict()

            # Serialize the dictionary to bytes.
            # Assume JSON serialization internally before encryption or for direct write.
            # TODO: Make internal serialization format configurable or handler-dependent based on save_path extension.
            try:
                 data_bytes = json.dumps(config_data, indent=4, ensure_ascii=False).encode('utf-8')
            except TypeError as e:
                 log.error(f"Failed to serialize configuration data to JSON bytes: {e}")
                 # Wrap serialization error in HandlerError for consistency
                 raise HandlerError(f"Serialization error: {e}") from e

            # Encrypt the serialized bytes if encryption is enabled
            if self._fernet:
                log.debug("Encrypting configuration data...")
                try:
                    data_to_write = self._encrypt(data_bytes)
                except Exception as e:
                    # Catch potential errors during encryption
                    log.error(f"Encryption failed: {e}")
                    raise EncryptionError(f"Encryption failed: {e}") from e
            else:
                # Not encrypting, use the plain serialized bytes
                data_to_write = data_bytes

            # Write the resulting bytes (either encrypted or plain JSON) to the file
            log.debug(f"Writing {len(data_to_write)} bytes to {save_path}")
            # Ensure parent directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(data_to_write)

            # Log success message clearly indicating encryption status
            status = "(encrypted)" if self._fernet else "(unencrypted)"
            log.info(f"Configuration successfully saved to {save_path} {status}.")

        # Catch specific ConfigMaster errors from serialization or encryption
        except (HandlerError, EncryptionError) as e:
             log.error(f"Failed to save configuration to {save_path}: {e}")
             raise e
        # Catch any other unexpected exceptions during file writing or data preparation
        except Exception as e:
            log.error(f"An unexpected error occurred during saving to {save_path}: {e}", exc_info=True)
            # Wrap unexpected errors in HandlerError
            raise HandlerError(f"Unexpected error saving configuration: {e}") from e

    def export_schema_with_values(self) -> dict:
        """
        Exports the complete configuration state, including the schema definition
        and the current value for each setting.

        This is useful for applications (e.g., frontends) that need both the
        structure/constraints and the current data to render forms or displays.

        Returns:
            A dictionary where keys are setting names. Each value is another
            dictionary containing a 'schema' key (with the schema definition)
            and a 'value' key (with the current setting value).
            This dictionary is suitable for JSON serialization.
        """
        log.debug("Exporting schema with current values.")
        full_export = {}
        for name, setting in self._settings.items():
            full_export[name] = {
                "schema": setting.schema.to_dict(),
                "value": setting.value
            }
        log.debug(f"Generated full export for {len(full_export)} settings.")
        return full_export        

    def get_schema_dict(self) -> dict:
        """Returns the entire configuration schema as a dictionary."""
        return {name: setting.schema.to_dict() for name, setting in self._settings.items()}

    def get_config_dict(self) -> dict:
        """Returns the current configuration values as a dictionary."""
        return {name: setting.value for name, setting in self._settings.items()}

    # --- Magic methods for MutableMapping and attribute access ---

    def __getattr__(self, name: str) -> typing.Any:
        """Allows accessing settings like attributes (e.g., config.port)."""
        # Handle schema access via 'sc_' prefix
        if name.startswith('sc_') and not name.startswith('_'): # Avoid internal attrs
             actual_name = name[3:]
             if actual_name in self._settings:
                 return self._settings[actual_name].schema
             else:
                  # Raise AttributeError for consistency with getattr
                  raise AttributeError(f"'{type(self).__name__}' object has no schema attribute '{name}' (setting '{actual_name}' not found)")

        # Access setting value
        if name in self._settings:
            return self._settings[name].value
        else:
             # Default behavior for attributes
            try:
                 return self.__getattribute__(name) # Check for actual methods/attributes
            except AttributeError:
                 raise AttributeError(f"'{type(self).__name__}' object has no attribute or setting '{name}'") from None


    def __setattr__(self, name: str, value: typing.Any):
        """Allows setting values like attributes (e.g., config.port = 8080)."""
        # Prevent setting schema attributes directly
        if name.startswith('sc_') and not name.startswith('_'):
            raise AttributeError("Cannot set schema attributes directly (e.g., 'config.sc_name = ...'). Modify the schema definition.")

        # Handle internal attributes
        if name.startswith('_') or name in self.__dict__ or hasattr(type(self), name):
            super().__setattr__(name, value)
        # Handle setting configuration values
        elif name in self._settings:
            try:
                self._settings[name].value = value # Use ConfigSetting's setter for validation
                if self._autosave:
                    self.save()
            except ValidationError as e:
                 # Convert to AttributeError or let ValidationError propagate?
                 # Let's propagate ValidationError for clarity.
                 raise e
        else:
            # Default behavior for setting new attributes (or raise error if strict?)
            # Let's prevent setting arbitrary attributes to avoid confusion with settings.
             raise AttributeError(f"Cannot set attribute '{name}'. It's not a defined setting or an internal attribute.")

    def __getitem__(self, key: str) -> typing.Any:
        """Allows accessing settings like dictionary items (e.g., config['port'])."""
         # Handle schema access via 'sc_' prefix
        if key.startswith('sc_'):
             actual_key = key[3:]
             if actual_key in self._settings:
                 return self._settings[actual_key].schema
             else:
                 raise SettingNotFoundError(f"Schema for setting '{actual_key}' not found.")

        # Access setting value
        if key in self._settings:
            return self._settings[key].value
        else:
            raise SettingNotFoundError(f"Setting '{key}' not found.")

    def __setitem__(self, key: str, value: typing.Any):
        """Allows setting values like dictionary items (e.g., config['port'] = 8080)."""
        if key.startswith('sc_'):
            raise KeyError("Cannot set schema items directly (e.g., 'config['sc_name'] = ...'). Modify the schema definition.")

        if key in self._settings:
            try:
                self._settings[key].value = value # Use ConfigSetting's setter
                if self._autosave:
                    self.save()
            except ValidationError as e:
                 # Let validation errors propagate
                 raise e
        else:
            raise SettingNotFoundError(f"Setting '{key}' not found. Cannot set undefined settings.")

    def __delitem__(self, key: str):
        """Prevent deleting settings."""
        raise TypeError("Deleting configuration settings is not supported.")

    def __iter__(self) -> typing.Iterator[str]:
        """Iterates over the names of the defined settings."""
        return iter(self._settings.keys())

    def __len__(self) -> int:
        """Returns the number of defined settings."""
        return len(self._settings)

    def __repr__(self) -> str:
        path_str = f"'{self._config_path}'" if self._config_path else "None"
        encrypted_str = ", encrypted" if self._fernet else ""
        return f"ConfigMaster(config_path={path_str}, settings={list(self._settings.keys())}{encrypted_str})"

    def __contains__(self, key):
        """Checks if a setting name exists."""
        return key in self._settings
