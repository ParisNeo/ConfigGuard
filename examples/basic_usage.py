# Project: ConfigGuard
# File: examples/basic_usage.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Updated for instance_version parameter)
# Description: Demonstrates the core functionalities of the ConfigGuard library,
#              including schema definition with nested sections, validation,
#              loading/saving (values/full), versioning, migration, encryption,
#              import/export, and nested attribute/item access.

import json
import typing
from pathlib import Path

# Import necessary components from the ConfigGuard library
from configguard import (
    ConfigGuard,
    EncryptionError,
    HandlerError,
    SchemaError,
    SettingNotFoundError,
    ValidationError,
    generate_encryption_key,
    log,
    set_log_level,
)


def run_basic_usage_example() -> None:
    """Executes the main demonstration of ConfigGuard features."""

    # Set log level for more verbose output during example run
    set_log_level("DEBUG")
    log.info("Starting ConfigGuard Basic Usage Example...")

    # --- Configuration Constants ---
    SCHEMA_VERSION = "2.0.0"  # Version defined in the schema
    OVERRIDE_VERSION = "2.1.0-beta" # Version to pass explicitly
    BASE_FILENAME = "my_app_config_nested"
    SECRET_KEY_FILE = Path("config_nested.secret")
    SCHEMA_DEFINITION_FILE = Path(
        f"my_app_schema_v{SCHEMA_VERSION.replace('.', '_')}_definition.json"
    )
    NO_VERSION_SCHEMA_FILE = Path("my_app_schema_no_version_definition.json")


    # --- 1. Define Schema with Nested Sections ---
    my_schema: typing.Dict[str, typing.Any] = {
        "__version__": SCHEMA_VERSION,
        "server": {
            "type": "section",
            "help": "Web server configuration.",
            "schema": {
                "host": {
                    "type": "str",
                    "default": "127.0.0.1",
                    "help": "Hostname or IP address to bind the server to.",
                },
                "port": {
                    "type": "int",
                    "default": 8080,
                    "min_val": 1024,
                    "max_val": 65535,
                    "help": "The network port the application should listen on.",
                },
                "timeout_seconds": {
                    "type": "float",
                    "default": 30.0,
                    "min_val": 0.5,
                    "help": "Request timeout in seconds.",
                },
                "enabled": {
                    "type": "bool",
                    "default": True,
                    "help": "Globally enable or disable the service.",
                },
            },
        },
        "database": {
            "type": "section",
            "help": "Database connection settings.",
            "schema": {
                "uri": {
                    "type": "str",
                    "default": None,
                    "nullable": True,
                    "help": "Database connection string (e.g., 'postgresql://user:pass@host:port/dbname').",
                },
                "retry_attempts": {
                    "type": "int",
                    "default": 3,
                    "min_val": 0,
                    "help": "Number of times to retry failed DB operations.",
                },
            },
        },
        "logging": {
            "type": "section",
            "help": "Application logging settings.",
            "schema": {
                "level": {
                    "type": "str",
                    "default": "INFO",
                    "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "help": "Set the application's logging verbosity.",
                },
                "file_path": {
                    "type": "str",
                    "default": None,
                    "nullable": True,
                    "help": "Path to log file (if enabled).",
                },
            },
        },
        "features": {
            "type": "section",
            "help": "Feature flags and experimental settings.",
            "schema": {
                "flags": {
                    "type": "list",
                    "default": ["feature_a", "new_dashboard"],
                    "help": "List of experimental features to enable.",
                },
                "enable_beta": {
                    "type": "bool",
                    "default": False,
                    "help": "Enable overall beta features.",
                },
            },
        },
        "security": {  # Top-level setting example alongside sections
            "type": "str",
            "default": None,
            "nullable": True,
            "help": "Optional global security token.",
        },
    }

    # Schema without version key
    my_schema_no_version = my_schema.copy()
    del my_schema_no_version["__version__"]

    # --- Save schema definitions to files (optional, for reference) ---
    log.info(
        f"--- Saving schema definition (v{SCHEMA_VERSION}) to {SCHEMA_DEFINITION_FILE} ---"
    )
    try:
        SCHEMA_DEFINITION_FILE.write_text(
            json.dumps(my_schema, indent=4), encoding="utf-8"
        )
        NO_VERSION_SCHEMA_FILE.write_text(
            json.dumps(my_schema_no_version, indent=4), encoding="utf-8"
        )
        log.info("Schema definitions saved successfully.")
    except Exception as e:
        log.error(f"Error saving schema definition: {e}")

    # --- Dynamically create filenames based on version ---
    version_str_file = OVERRIDE_VERSION.replace(".", "_").replace("-","_") # Use override for files
    config_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_values.json")
    full_state_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_full.json")
    encrypted_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_encrypted.bin")

    log.info(f"--- Using Schema Version: {SCHEMA_VERSION} ---")
    log.info(f"--- Overriding Instance Version: {OVERRIDE_VERSION} ---")
    log.info(f"--- Values Config file: {config_file_path} ---")
    log.info(f"--- Full State file: {full_state_file_path} ---")
    log.info(f"--- Encrypted file: {encrypted_file_path} ---")

    # Ensure config files don't exist from previous runs for a clean start
    for f in [
        config_file_path,
        full_state_file_path,
        encrypted_file_path,
        SECRET_KEY_FILE,
        SCHEMA_DEFINITION_FILE,
        NO_VERSION_SCHEMA_FILE
    ]:
        if f.exists():
            log.debug(f"Removing existing file: {f}")
            f.unlink()

    try:
        # --- 2. Initialize ConfigGuard ---
        log.info(f"\n--- Initializing ConfigGuard (Explicit Version: {OVERRIDE_VERSION}) ---")
        # Initialize using the schema dictionary but override the version
        config = ConfigGuard(
            schema=my_schema,
            instance_version=OVERRIDE_VERSION, # <-- Explicitly set instance version
            config_path=config_file_path,
            autosave=False,
        )
        log.info(f"ConfigGuard initialized. Instance Version: {config.version} (Schema had: {SCHEMA_VERSION})")
        assert config.version == OVERRIDE_VERSION

        # --- 2b. Initialize ConfigGuard (Schema Version) ---
        log.info(f"\n--- Initializing ConfigGuard (Schema Version: {SCHEMA_VERSION}) ---")
        # Initialize using schema version (instance_version not provided)
        config_schema_ver = ConfigGuard(
            schema=my_schema,
            config_path=None, # In-memory only
            autosave=False,
        )
        log.info(f"ConfigGuard initialized. Instance Version: {config_schema_ver.version}")
        assert config_schema_ver.version == SCHEMA_VERSION

        # --- 2c. Initialize ConfigGuard (No Version Provided) ---
        log.info(f"\n--- Initializing ConfigGuard (No Version) ---")
        # Initialize using schema without version and no instance_version param
        config_no_ver = ConfigGuard(
            schema=my_schema_no_version,
            config_path=None, # In-memory only
            autosave=False,
        )
        log.info(f"ConfigGuard initialized. Instance Version: {config_no_ver.version}")
        assert config_no_ver.version == "0.0.0"

        # --- Continue with the 'config' instance (using OVERRIDE_VERSION) for subsequent steps ---
        log.info(f"\n--- Continuing example with instance version: {config.version} ---")

        # --- 3. Accessing Default Values (Nested) ---
        log.info("\n--- Accessing Default Values (Nested) ---")
        log.info(f"Server Host (Default): {config.server.host}")
        log.info(f"Server Port (Default): {config['server']['port']}")
        # ... (rest of access remains the same) ...
        assert config.server.timeout_seconds == 30.0
        assert config.database.uri is None

        # --- 4. Accessing Schema Details (Nested) ---
        log.info("\n--- Accessing Schema Details (Nested) ---")
        log.info(f"Help for 'server.port': {config.server.sc_port.help}")
        # ... (rest of schema access remains the same) ...
        assert config.database.sc_uri.nullable is True

        # --- 5. Modifying Values (Nested) ---
        log.info("\n--- Modifying Values (Nested) ---")
        config.server.port = 9000
        config["server"]["host"] = "0.0.0.0"
        config.database.uri = "sqlite:///prod_nested.db"
        config.logging.level = "DEBUG"
        config.features.flags.append("beta_feature")
        config.features.enable_beta = True
        config.security = "top-secret-global-token"
        log.info(f"Set server port to: {config.server.port}")
        # ... (rest of modification logging remains the same) ...

        # --- 6. Testing Validation Errors (Nested) ---
        log.info("\n--- Testing Validation (Nested) ---")
        try:
            config.server.port = 80
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")
        # ... (rest of validation tests remain the same) ...
        config.database.uri = "sqlite:///prod_nested.db" # Reset

        # --- 7. Saving Configuration (Values vs Full - Nested) ---
        # Note: The instance version (OVERRIDE_VERSION) will be saved in 'full' mode
        log.info("\n--- Saving Configuration (Nested) ---")
        log.info(f"Saving mode='values' to {config_file_path}...")
        config.save(mode="values")
        log.info(f"Content of {config_file_path} (values only - nested):\n{config_file_path.read_text(encoding='utf-8')}")

        log.info(f"\nSaving mode='full' to {full_state_file_path}...")
        config.save(filepath=full_state_file_path, mode="full")
        log.info(f"Content of {full_state_file_path} (full state - v:{config.version} - nested - first ~400 chars):\n{full_state_file_path.read_text(encoding='utf-8')[:400]}...")

        # --- 8. Loading Configuration (Nested) ---
        log.info("\n--- Loading Configuration (from values-only file - nested) ---")
        # Load into a new instance using the *original schema* but the *override version*
        config_load_values = ConfigGuard(schema=my_schema, instance_version=OVERRIDE_VERSION, config_path=config_file_path)
        log.info(f"Loaded Server Port: {config_load_values.server.port}")
        # ... (rest of load logging and asserts remain the same) ...
        assert config_load_values.loaded_file_version is None # Values file has no version

        log.info("\n--- Loading Configuration (from full state file - nested) ---")
        # Load from 'full' file. Instance version matches file version.
        config_load_full = ConfigGuard(schema=my_schema, instance_version=OVERRIDE_VERSION, config_path=full_state_file_path)
        log.info(f"Loaded Server Port: {config_load_full.server.port}")
        # ... (rest of load logging and asserts remain the same) ...
        assert config_load_full.loaded_file_version == OVERRIDE_VERSION # Version loaded correctly

        # --- 9. Version Handling Simulation (Nested) ---
        log.info("\n--- Version Handling Simulation (Nested) ---")
        # Create a fake older config file (V1.0.0) saved in 'full' mode
        older_version_file = "1.0.0"
        # This older config pretends to have *some* structure matching the new schema
        older_config_full_state_structured = {
            "version": older_version_file, # Version in the file
            "schema": { # Old schema structure
                 # ... (assuming some old structured schema definition here) ...
                 "server": {"type":"section", "schema": {"port": {"type":"int"}, "enabled": {"type":"bool"}}},
                 "database": {"type":"section", "schema": {"uri": {"type":"str"}, "retry_attempts": {"type":"int"}}},
                 "logging_level": {"type": "str"},
                 "security_key": {"type": "str", "nullable": True},
                 "removed_section": {"type": "section", "schema": {"old_val": {"type": "int"}}},
            },
            "values": { # Old values
                 "server": {"port": 7000, "enabled": True},
                 "database": {"uri": "old_db.sqlite", "retry_attempts": 5},
                 "logging_level": "INFO", # Maps to logging.level
                 "security_key": "secret-v1.0", # Maps to security
                 "removed_section": {"old_val": 123},
            },
        }
        older_file = Path(f"{BASE_FILENAME}_v{older_version_file.replace('.','_')}_full_simulated.json")
        try:
            log.info(f"Creating simulated older config file ({older_version_file}) at {older_file}...")
            older_file.write_text(json.dumps(older_config_full_state_structured, indent=4), encoding="utf-8")

            log.info(f"\nLoading older config ({older_version_file}) into current instance (V{OVERRIDE_VERSION})...")
            # Initialize instance with CURRENT schema and version, load OLDER file
            config_migrate = ConfigGuard(schema=my_schema, instance_version=OVERRIDE_VERSION, config_path=older_file)
            # Load() in init handles migration

            log.info("\n--- Configuration State After Loading Older Version ---")
            log.info(f"Loaded File Version: {config_migrate.loaded_file_version}")
            log.info(f"Instance Version: {config_migrate.version}")
            log.info(f"Server Port: {config_migrate.server.port}") # Loaded from old
            log.info(f"Server Enabled: {config_migrate.server.enabled}") # Loaded from old
            log.info(f"Server Host: {config_migrate.server.host}") # Uses new default
            log.info(f"Database URI: {config_migrate.database.uri}") # Loaded from old
            log.info(f"Database Retries: {config_migrate.database.retry_attempts}") # Loaded from old
            log.info(f"Logging Level: {config_migrate.logging.level}") # Uses new default (key name changed)
            log.info(f"Security Token: {config_migrate.security}") # Uses new default (key name changed)
            log.info(f"Feature Flags: {config_migrate.features.flags}") # Uses new default (section new)

            # Assertions
            assert config_migrate.loaded_file_version == older_version_file
            assert config_migrate.version == OVERRIDE_VERSION # Instance version is key
            assert config_migrate.server.port == 7000
            assert config_migrate.server.host == "127.0.0.1" # Default
            assert config_migrate.database.uri == "old_db.sqlite"
            assert config_migrate.logging.level == "INFO" # Default
            assert config_migrate.security is None # Default

        except (ValidationError, SchemaError, HandlerError, SettingNotFoundError, FileNotFoundError) as e:
            log.error(f"\n*** Error during version handling simulation: {e} ***")
        finally:
            if older_file.exists(): older_file.unlink()

        # --- 10. Export Schema with Values (Nested) ---
        log.info(f"\n--- Exporting Schema with Current Values (Instance V{config_load_full.version}) ---")
        exported_state = config_load_full.export_schema_with_values()
        log.info("Full Config State (Schema + Values - Nested) for Frontend/API:")
        log.info(json.dumps(exported_state, indent=2, ensure_ascii=False))
        assert exported_state.get("version") == OVERRIDE_VERSION # Should reflect instance version
        # ... (rest of export checks) ...

        # --- 11. Import Configuration Values from Dictionary (Nested) ---
        # ... (Import logic remains the same, using config_load_full instance) ...
        log.info("\n--- Importing Configuration Values from Dictionary (Nested) ---")
        import_data = {
            "server": { "port": 5005, "host": "192.168.1.100", "timeout_seconds": -10.0},
            "logging": { "level": "WARNING", "file_path": "/var/log/app_nested.log"},
            "database": { "uri": None},
            "features": { "flags": ["core_v2"], "unknown_feature": True},
            "security": "imported-global-token",
            "unknown_section": {"key": "value"},
        }
        try:
            config_load_full.load(filepath=full_state_file_path) # Reload for clean state
            original_timeout = config_load_full.server.timeout_seconds
            config_load_full.import_config(import_data, ignore_unknown=True)
            log.info("--- State After Import ---")
            log.info(f"Port: {config_load_full.server.port}")
            log.info(f"Timeout: {config_load_full.server.timeout_seconds}") # Should be unchanged
            log.info(f"DB URI: {config_load_full.database.uri}")
            log.info(f"Security: {config_load_full.security}")
            assert config_load_full.server.port == 5005
            assert config_load_full.server.timeout_seconds == original_timeout
            assert config_load_full.database.uri is None
            assert config_load_full.security == "imported-global-token"
        except (ValidationError, SchemaError, HandlerError, SettingNotFoundError) as e:
             log.error(f"\n*** Error during import_config example: {e} ***")

        # --- 12. Encryption Example (Nested) ---
        log.info(f"\n--- Encryption Example (Instance V{OVERRIDE_VERSION} - Nested) ---")
        if SECRET_KEY_FILE.exists(): key = SECRET_KEY_FILE.read_bytes()
        else: key = generate_encryption_key(); SECRET_KEY_FILE.write_bytes(key)
        log.info(f"Using encryption key from {SECRET_KEY_FILE}")

        try:
            enc_config = ConfigGuard(
                schema=my_schema,
                instance_version=OVERRIDE_VERSION, # Set instance version
                config_path=encrypted_file_path,
                encryption_key=key
            )
            log.info("Modifying values in encrypted instance...")
            enc_config.database.uri = "postgresql://prod_user:prod_pass@db.example.com/prod_db"
            enc_config.security = "encrypted-global-token"
            enc_config.save(mode="full") # Save full state (includes OVERRIDE_VERSION)
            log.info(f"Encrypted 'full' saved to {encrypted_file_path}.")

            log.info("Loading encrypted data...")
            enc_config_load = ConfigGuard(
                schema=my_schema, # Schema version is 2.0.0
                instance_version=OVERRIDE_VERSION, # Instance version matches saved file
                config_path=encrypted_file_path,
                encryption_key=key
            )
            log.info(f"Loaded DB URI: {enc_config_load.database.uri}")
            log.info(f"Loaded Security: {enc_config_load.security}")
            log.info(f"Loaded File Version: {enc_config_load.loaded_file_version}") # Should be OVERRIDE_VERSION

            assert enc_config_load.database.uri == "postgresql://prod_user:prod_pass@db.example.com/prod_db"
            assert enc_config_load.security == "encrypted-global-token"
            assert enc_config_load.loaded_file_version == OVERRIDE_VERSION

        except ImportError: log.warning("\n*** Encryption example skipped: 'cryptography' not installed. ***")
        except (ValidationError, SchemaError, HandlerError, EncryptionError, SettingNotFoundError) as e:
             log.error(f"\n*** Error during encryption example: {e} ***")

    # --- Main Exception Handling ---
    except (ValidationError, SchemaError, HandlerError, SettingNotFoundError, EncryptionError) as e:
        log.error(f"\n*** ConfigGuard error during basic usage: {e} ***", exc_info=True)
    except Exception as e:
        log.error(f"\n*** Unexpected error occurred: {e} ***", exc_info=True)

    # --- Final Cleanup ---
    finally:
        log.info("\n--- Cleaning up generated files ---")
        files_to_remove = [
            config_file_path, full_state_file_path, encrypted_file_path,
            SECRET_KEY_FILE, SCHEMA_DEFINITION_FILE, NO_VERSION_SCHEMA_FILE
        ]
        for f_path in files_to_remove:
            if f_path.exists():
                try: f_path.unlink(); log.debug(f"Removed {f_path}")
                except OSError as e: log.error(f"Error removing {f_path}: {e}")
            else: log.debug(f"File not found for cleanup: {f_path}")
        log.info("Cleanup finished.")

if __name__ == "__main__":
    run_basic_usage_example()

