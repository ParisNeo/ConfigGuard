# -*- coding: utf-8 -*-
# Project: ConfigMaster
# File: examples/basic_usage.py
# Author: ParisNeo with Gemini 2.5
# Date: 30/04/2025
# Description: Demonstrates the core functionalities of the ConfigMaster library,
#              including schema definition, validation, loading/saving (values/full),
#              versioning, migration, encryption, import/export, and attribute/item access.

import json
import os
from pathlib import Path
import time # Used only for file cleanup timing, not core logic
import typing

# Import necessary components from the ConfigMaster library
from configmaster import (
    ConfigMaster,
    ValidationError,
    SchemaError,
    HandlerError,
    SettingNotFoundError,
    EncryptionError,
    generate_encryption_key,
    set_log_level,
    log # Import the logger instance
)

def run_basic_usage_example() -> None:
    """Executes the main demonstration of ConfigMaster features."""

    # Set log level for more verbose output during example run
    set_log_level("DEBUG")
    log.info("Starting ConfigMaster Basic Usage Example...")

    # --- Configuration Constants ---
    CONFIG_VERSION = "1.1.0" # Define the current version for the schema/instance
    BASE_FILENAME = "my_app_config"
    SECRET_KEY_FILE = Path("config.secret")
    SCHEMA_DEFINITION_FILE = Path("my_app_schema_definition.json") # For saving schema definition

    # --- 1. Define Schema ---
    # Schema for V1.1.0 (adds timeout, makes database_uri nullable)
    my_schema: typing.Dict[str, typing.Any] = {
        "__version__": CONFIG_VERSION,
        "database_uri": {
            "type": "str",
            "default": None, # Changed default from previous examples
            "nullable": True, # Made nullable
            "help": "Database connection string (e.g., 'postgresql://user:pass@host:port/dbname')."
        },
        "port": {
            "type": "int",
            "default": 8080,
            "min_val": 1024,
            "max_val": 65535,
            "help": "The network port the application should listen on."
        },
        "log_level": {
            "type": "str",
            "default": "INFO",
            "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "help": "Set the application's logging verbosity."
        },
        "feature_flags": {
            "type": "list",
            "default": ["feature_a", "new_dashboard"],
            "help": "List of experimental features to enable."
        },
        "enabled": {
            "type": "bool",
            "default": True,
            "help": "Globally enable or disable the service."
        },
        "api_key": {
            "type": "str",
            "default": None,
            "nullable": True,
            "help": "API key for external service integration (optional)."
        },
        "retry_attempts": {
             "type": "int",
             "default": 3,
             "min_val": 0,
             "help": "Number of times to retry failed operations."
        },
        "timeout_seconds": { # New setting in V1.1.0
             "type": "float",
             "default": 30.0,
             "min_val": 0.5,
             "help": "Request timeout in seconds."
        }
    }

    # --- Save schema definition to file (optional, for reference) ---
    log.info(f"--- Saving schema definition (v{CONFIG_VERSION}) to {SCHEMA_DEFINITION_FILE} ---")
    try:
        SCHEMA_DEFINITION_FILE.write_text(json.dumps(my_schema, indent=4), encoding='utf-8')
        log.info(f"Schema definition saved successfully.")
    except Exception as e:
        log.error(f"Error saving schema definition: {e}")

    # --- Dynamically create filenames based on version ---
    # Using simple version format in filename for this example
    version_str_file = CONFIG_VERSION.replace('.', '_')
    config_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_values.json")
    full_state_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_full.json")
    encrypted_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_encrypted.bin")

    log.info(f"--- Using Config Version: {CONFIG_VERSION} ---")
    log.info(f"--- Values Config file: {config_file_path} ---")
    log.info(f"--- Full State file: {full_state_file_path} ---")
    log.info(f"--- Encrypted file: {encrypted_file_path} ---")

    # Ensure config files don't exist from previous runs for a clean start
    for f in [config_file_path, full_state_file_path, encrypted_file_path, SECRET_KEY_FILE]:
        if f.exists():
            log.debug(f"Removing existing file: {f}")
            f.unlink()

    try:
        # --- 2. Initialize ConfigMaster ---
        log.info(f"\n--- Initializing ConfigMaster (V{CONFIG_VERSION}) ---")
        # Initialize using the schema dictionary directly
        config = ConfigMaster(
            schema=my_schema,
            config_path=config_file_path, # Default path for loading/saving values
            autosave=False # Explicit saves in this example
        )

        # --- 3. Accessing Default Values ---
        log.info("\n--- Accessing Default Values ---")
        log.info(f"Database URI (Default): {config.database_uri}") # Should be None
        log.info(f"Port (Default): {config.port}")
        log.info(f"Enabled Status (Default): {config.enabled}")
        log.info(f"Feature Flags (Default): {config.feature_flags}")
        log.info(f"API Key (Default): {config.api_key}") # Should be None
        log.info(f"Timeout Seconds (Default): {config.timeout_seconds}") # New default

        # Check a default value
        assert config.timeout_seconds == 30.0

        # --- 4. Accessing Schema Details ---
        log.info("\n--- Accessing Schema Details ---")
        log.info(f"Help for 'port': {config.sc_port.help}")
        log.info(f"Type for 'enabled': {config.sc_enabled.type_str}")
        log.info(f"Is 'database_uri' nullable? {config.sc_database_uri.nullable}")
        log.info(f"Default for 'log_level': {config.sc_log_level.default_value}")
        log.info(f"Min value for 'retry_attempts': {config['sc_retry_attempts'].min_val}") # Dict access
        log.info(f"Allowed options for 'log_level': {config.sc_log_level.options}")

        assert config.sc_database_uri.nullable is True

        # --- 5. Modifying Values (Validation Triggered) ---
        log.info("\n--- Modifying Values ---")
        config.port = 9000
        config['log_level'] = "DEBUG" # Dict access modification
        config.feature_flags.append("beta_feature") # Modify list in-place (careful with autosave)
        config.enabled = False
        config.api_key = "secret-api-key-v1.1"
        config.timeout_seconds = 15.5
        config.database_uri = "sqlite:///test_db_v1_1.db" # Set non-null value

        log.info(f"Set port to: {config.port}")
        log.info(f"Set log_level to: {config.log_level}")
        log.info(f"Updated feature flags: {config.feature_flags}")
        log.info(f"Set enabled to: {config.enabled}")
        log.info(f"Set API key: {config.api_key}")
        log.info(f"Set timeout: {config.timeout_seconds}")
        log.info(f"Set database URI: {config.database_uri}")

        # --- 6. Testing Validation Errors ---
        log.info("\n--- Testing Validation ---")
        try:
            config.port = 80 # Below min_val
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")

        try:
            config.log_level = "TRACE" # Not in options
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")

        try:
             config.enabled = "yes" # Invalid type for bool
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")

        try:
             config.database_uri = None # This is now allowed due to nullable=True
             log.info(f"Successfully set database_uri back to None (allowed). Value: {config.database_uri}")
        except ValidationError as e:
            log.error(f"Caught UNEXPECTED validation error setting nullable field to None: {e}")

        # Reset database_uri for subsequent steps
        config.database_uri = "sqlite:///test_db_v1_1.db"


        # --- 7. Saving Configuration (Values vs Full) ---
        log.info("\n--- Saving Configuration ---")
        # Save only values to the default path
        log.info(f"Saving mode='values' to {config_file_path}...")
        config.save(mode='values') # Uses config._config_path
        log.info(f"Content of {config_file_path} (values only):")
        log.info(config_file_path.read_text(encoding='utf-8'))

        # Save full state (schema + values + version) to a different path
        log.info(f"\nSaving mode='full' to {full_state_file_path}...")
        config.save(filepath=full_state_file_path, mode='full')
        log.info(f"Content of {full_state_file_path} (full state - first ~300 chars):")
        log.info(full_state_file_path.read_text(encoding='utf-8')[:300] + "...")

        # --- 8. Loading Configuration ---
        log.info("\n--- Loading Configuration (from values-only file) ---")
        # Load from the file saved with mode='values' into a new instance
        config_load_values = ConfigMaster(schema=my_schema, config_path=config_file_path)
        log.info(f"Loaded Port: {config_load_values.port}")
        log.info(f"Loaded DB URI: {config_load_values.database_uri}")
        log.info(f"Loaded Timeout: {config_load_values.timeout_seconds}") # Should be default
        assert config_load_values.port == 9000
        assert config_load_values.database_uri == "sqlite:///test_db_v1_1.db"
        assert config_load_values.timeout_seconds == 15.5 # Default for V1.1.0 instance schema
        assert config_load_values.loaded_file_version is None # Values-only file has no version info

        log.info("\n--- Loading Configuration (from full state file) ---")
        # Load from the file saved with mode='full'
        config_load_full = ConfigMaster(schema=my_schema, config_path=full_state_file_path)
        log.info(f"Loaded Port: {config_load_full.port}")
        log.info(f"Loaded DB URI: {config_load_full.database_uri}")
        log.info(f"Loaded Timeout: {config_load_full.timeout_seconds}") # Should have loaded value
        assert config_load_full.port == 9000
        assert config_load_full.database_uri == "sqlite:///test_db_v1_1.db"
        assert config_load_full.timeout_seconds == 15.5 # Value loaded from full state file
        assert config_load_full.loaded_file_version == CONFIG_VERSION # Version loaded correctly

        # --- 9. Version Handling Simulation ---
        log.info("\n--- Version Handling Simulation ---")
        # Create a fake older config file (V1.0.0) saved in 'full' mode
        older_version = "1.0.0"
        older_config_full_state = {
            "version": older_version,
            "schema": { # Represents the schema as it *was* in V1.0.0
                 "database_uri": {"type": "str", "nullable": False, "default":"default.db", "help":"Old help"},
                 "port": {"type": "int", "default":8000},
                 "log_level": {"type": "str", "default":"WARN", "options":["INFO","WARN"]},
                 "enabled": {"type": "bool"},
                 "api_key": {"type": "str", "nullable": True},
                 "retry_attempts": {"type": "int"}
                 # Missing feature_flags, timeout_seconds
            },
            "values": {
                "database_uri": "old_db.sqlite", # Had value, was not nullable
                "port": 7000,
                "log_level": "INFO", # Valid against old options
                "enabled": True,
                "api_key": "secret-v1.0",
                "retry_attempts": 5,
                "removed_setting": "abc" # A setting removed in v1.1.0
            }
        }
        older_file = Path(f"{BASE_FILENAME}_v{older_version.replace('.','_')}_full_simulated.json")
        try:
            log.info(f"Creating simulated older 'full' config file ({older_version}) at {older_file}...")
            older_file.write_text(json.dumps(older_config_full_state, indent=4), encoding='utf-8')

            log.info(f"\nLoading older config ({older_version}) into current instance (V{CONFIG_VERSION})...")
            # Initialize a new instance with the CURRENT schema (V1.1.0) and load the older file
            config_migrate = ConfigMaster(schema=my_schema, config_path=older_file)
            # The load() method within __init__ handles the migration

            log.info("\n--- Configuration State After Loading Older Version ---")
            log.info(f"Loaded File Version: {config_migrate.loaded_file_version}")
            log.info(f"Instance Version: {config_migrate.version}")
            log.info(f"Port: {config_migrate.port}") # Should load from old file's values
            log.info(f"Log Level: {config_migrate.log_level}") # Should load (valid in new options too)
            log.info(f"Enabled: {config_migrate.enabled}") # Should load
            log.info(f"API Key: {config_migrate.api_key}") # Should load
            log.info(f"Retry Attempts: {config_migrate.retry_attempts}") # Should load
            log.info(f"Database URI: {config_migrate.database_uri}") # Should load (now nullable)
            log.info(f"Timeout Seconds: {config_migrate.timeout_seconds}") # Should use V1.1.0 default
            log.info(f"Feature Flags: {config_migrate.feature_flags}") # Should use V1.1.0 default

            # Assertions for migration results
            assert config_migrate.loaded_file_version == older_version
            assert config_migrate.port == 7000
            assert config_migrate.log_level == "INFO"
            assert config_migrate.api_key == "secret-v1.0"
            assert config_migrate.database_uri == "old_db.sqlite" # Loaded ok
            assert config_migrate.timeout_seconds == 30.0 # V1.1.0 default
            # 'feature_flags' uses V1.1.0 default as it wasn't in the older 'values' dict
            assert config_migrate.feature_flags == ["feature_a", "new_dashboard"]
            # 'removed_setting' should have been logged as skipped during migration

        except (ValidationError, SchemaError, HandlerError, SettingNotFoundError, FileNotFoundError) as e:
            log.error(f"\n*** Error during version handling simulation: {e} ***")
        finally:
            # Clean up the simulated older file immediately
            if older_file.exists():
                older_file.unlink()
                log.debug(f"Cleaned up simulated file: {older_file}")


        # --- 10. Export Schema with Values ---
        log.info("\n--- Exporting Schema with Current Values (V1.1.0 Instance) ---")
        # Use the config_load_full instance which reflects the loaded V1.1.0 state
        exported_state = config_load_full.export_schema_with_values()
        log.info("Full Config State (Schema + Values) for Frontend/API:")
        try:
            # Print as nicely formatted JSON
            log.info(json.dumps(exported_state, indent=2, ensure_ascii=False))
            # Check version in export
            assert exported_state.get("version") == CONFIG_VERSION
            assert "timeout_seconds" in exported_state.get("settings", {})
        except TypeError as e:
             log.error(f"Error serializing exported state to JSON: {e}")
             # Fallback print using pprint
             import pprint
             pprint.pprint(exported_state)


        # --- 11. Import Configuration Values from Dictionary ---
        log.info("\n--- Importing Configuration Values from Dictionary ---")
        # Create a dictionary with new values to import
        import_data = {
            "port": 5005,                   # Valid change
            "log_level": "WARNING",         # Valid change
            "enabled": "true",              # Valid string -> bool coercion expected
            "retry_attempts": -1,           # Invalid (below min_val) - should be skipped
            "database_uri": None,           # Valid (now nullable)
            "new_setting": "some_value",    # Unknown key - should be ignored/warned
            "feature_flags": ["core_v2"]    # Valid change
            # timeout_seconds not included, should remain unchanged
        }
        log.info(f"Importing data via import_config: {import_data}")

        try:
            # Use the config_load_full instance to import into
            current_timeout = config_load_full.timeout_seconds # Store before import
            config_load_full.import_config(import_data, ignore_unknown=True) # Ignore unknown keys

            log.info("\n--- Configuration State After Dictionary Import ---")
            log.info(f"Imported Port: {config_load_full.port}")
            log.info(f"Imported Log Level: {config_load_full.log_level}")
            log.info(f"Imported Enabled: {config_load_full.enabled}") # Should be True
            log.info(f"Imported Retry Attempts: {config_load_full.retry_attempts}") # Should remain unchanged
            log.info(f"Imported Database URI: {config_load_full.database_uri}") # Should be None
            log.info(f"Imported Feature Flags: {config_load_full.feature_flags}")
            log.info(f"Timeout (Should be unchanged): {config_load_full.timeout_seconds}")

            # Verify values after import
            assert config_load_full.port == 5005
            assert config_load_full.log_level == "WARNING"
            assert config_load_full.enabled is True # Coerced from "true"
            # retry_attempts should be skipped due to validation error, keeping previous value (5 from migration example?) - Let's re-run load full state first
            # Re-load full state to have a predictable starting point before import test
            config_load_full.load(filepath=full_state_file_path)
            assert config_load_full.retry_attempts == 3 # Should be 3 after re-load
            config_load_full.import_config(import_data, ignore_unknown=True)
            assert config_load_full.retry_attempts == 3 # Should remain 3 as import value was invalid

            assert config_load_full.database_uri is None # Set to None by import
            assert config_load_full.feature_flags == ["core_v2"]
            assert config_load_full.timeout_seconds == 15.5 # Unchanged by import

            # Example: Importing with ignore_unknown=False (should raise error)
            try:
                 log.info("\n--- Testing import_config with ignore_unknown=False ---")
                 config_load_full.import_config({"port": 8888, "unknown_import": True}, ignore_unknown=False)
            except SettingNotFoundError as e:
                 log.info(f"Caught expected error for unknown key during import: {e}")
            except Exception as e: # Catch others just in case
                 log.error(f"Caught UNEXPECTED error during ignore_unknown=False test: {e}")

        except (ValidationError, SchemaError, HandlerError, SettingNotFoundError) as e:
            log.error(f"\n*** An error occurred during import_config example: {e} ***")


        # --- 12. Encryption Example ---
        log.info(f"\n--- Encryption Example (V{CONFIG_VERSION}) ---")
        # Generate a key or load if exists (for consistency if run multiple times)
        if SECRET_KEY_FILE.exists():
             key = SECRET_KEY_FILE.read_bytes()
             log.info("Loaded existing encryption key.")
        else:
             key = generate_encryption_key()
             SECRET_KEY_FILE.write_bytes(key)
             log.info(f"Generated and saved new encryption key to {SECRET_KEY_FILE}")

        try:
            # Initialize with encryption key and specific path
            enc_config = ConfigMaster(
                schema=my_schema,
                config_path=encrypted_file_path,
                encryption_key=key
            )
            # Initial load will fail as file doesn't exist, defaults used.

            # Modify some values
            log.info("Modifying values in encrypted config instance.")
            enc_config.database_uri = "postgresql://prod_user:prod_pass@db.example.com/prod_db"
            enc_config.port = 4443 # Valid port
            enc_config.log_level = "WARNING"
            enc_config.timeout_seconds = 60.0

            # Save encrypted (try both modes)
            log.info(f"Saving encrypted config (mode='full') to {encrypted_file_path}...")
            enc_config.save(mode='full')
            log.info("Encrypted 'full' configuration saved.")
            log.info("File content (encrypted - first 100 bytes):")
            log.info(f"{encrypted_file_path.read_bytes()[:100]}...")

            # Save encrypted (values only) - Overwrites previous save
            log.info(f"\nSaving encrypted config (mode='values') to {encrypted_file_path}...")
            enc_config.save(mode='values')
            log.info("Encrypted 'values' configuration saved.")
            log.info("File content (encrypted - first 100 bytes):")
            log.info(f"{encrypted_file_path.read_bytes()[:100]}...")

            # Load encrypted into a new instance
            log.info("\n--- Loading Encrypted Configuration ---")
            # Read key from file for loading instance
            loaded_key = SECRET_KEY_FILE.read_bytes()
            enc_config_load = ConfigMaster(
                schema=my_schema,
                config_path=encrypted_file_path,
                encryption_key=loaded_key
            )
            # Load happens in __init__

            log.info(f"Loaded Database URI: {enc_config_load.database_uri}")
            log.info(f"Loaded Port: {enc_config_load.port}")
            log.info(f"Loaded Log Level: {enc_config_load.log_level}")
            log.info(f"Loaded Timeout: {enc_config_load.timeout_seconds}")
            # Note: Since we last saved 'values', version/schema info wasn't in the file
            log.info(f"Loaded File Version (from values save): {enc_config_load.loaded_file_version}")

            # Assert values loaded correctly from the 'values' save
            assert enc_config_load.database_uri == "postgresql://prod_user:prod_pass@db.example.com/prod_db"
            assert enc_config_load.port == 4443
            assert enc_config_load.log_level == "WARNING"
            assert enc_config_load.timeout_seconds == 60.0
            assert enc_config_load.loaded_file_version is None # No version in values-only file

        except ImportError:
             log.warning("\n*** Encryption example skipped: 'cryptography' library not installed. ***")
             log.warning("*** Please install it: pip install cryptography ***")
        except (ValidationError, SchemaError, HandlerError, EncryptionError, SettingNotFoundError) as e:
            log.error(f"\n*** An error occurred during encryption example: {e} ***")


    # --- Main Exception Handling for the whole example ---
    except (ValidationError, SchemaError, HandlerError, SettingNotFoundError, EncryptionError) as e:
        log.error(f"\n*** A ConfigMaster error occurred during basic usage: {e} ***", exc_info=True)
    except Exception as e:
         log.error(f"\n*** An unexpected error occurred: {e} ***", exc_info=True)

    # --- Final Cleanup ---
    finally:
         log.info("\n--- Cleaning up generated files ---")
         files_to_remove = [
             config_file_path,
             full_state_file_path,
             encrypted_file_path,
             SECRET_KEY_FILE,
             SCHEMA_DEFINITION_FILE,
             # older_file is cleaned up in its own block
         ]
         for f_path in files_to_remove:
             if f_path.exists():
                 try:
                     f_path.unlink()
                     log.debug(f"Removed {f_path}")
                 except OSError as e:
                     log.error(f"Error removing {f_path}: {e}")
             else:
                 log.debug(f"File not found for cleanup (already removed or never created): {f_path}")
         log.info("Cleanup finished.")


if __name__ == "__main__":
    # Run the example function when the script is executed directly
    run_basic_usage_example()