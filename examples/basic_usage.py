# Project: ConfigGuard
# File: examples/basic_usage.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Updated for nesting)
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
    log.info("Starting ConfigGuard Basic Usage Example (with Nesting)...")

    # --- Configuration Constants ---
    CONFIG_VERSION = "2.0.0"  # Updated version for schema with nesting
    BASE_FILENAME = "my_app_config_nested"
    SECRET_KEY_FILE = Path("config_nested.secret")
    SCHEMA_DEFINITION_FILE = Path(
        "my_app_schema_nested_definition.json"
    )  # For saving schema definition

    # --- 1. Define Schema with Nested Sections ---
    my_schema: typing.Dict[str, typing.Any] = {
        "__version__": CONFIG_VERSION,
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

    # --- Save schema definition to file (optional, for reference) ---
    log.info(
        f"--- Saving schema definition (v{CONFIG_VERSION}) to {SCHEMA_DEFINITION_FILE} ---"
    )
    try:
        SCHEMA_DEFINITION_FILE.write_text(
            json.dumps(my_schema, indent=4), encoding="utf-8"
        )
        log.info("Schema definition saved successfully.")
    except Exception as e:
        log.error(f"Error saving schema definition: {e}")

    # --- Dynamically create filenames based on version ---
    version_str_file = CONFIG_VERSION.replace(".", "_")
    config_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_values.json")
    full_state_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_full.json")
    encrypted_file_path = Path(f"{BASE_FILENAME}_v{version_str_file}_encrypted.bin")

    log.info(f"--- Using Config Version: {CONFIG_VERSION} ---")
    log.info(f"--- Values Config file: {config_file_path} ---")
    log.info(f"--- Full State file: {full_state_file_path} ---")
    log.info(f"--- Encrypted file: {encrypted_file_path} ---")

    # Ensure config files don't exist from previous runs for a clean start
    for f in [
        config_file_path,
        full_state_file_path,
        encrypted_file_path,
        SECRET_KEY_FILE,
        SCHEMA_DEFINITION_FILE,  # Also remove schema file if exists
    ]:
        if f.exists():
            log.debug(f"Removing existing file: {f}")
            f.unlink()

    try:
        # --- 2. Initialize ConfigGuard ---
        log.info(f"\n--- Initializing ConfigGuard (V{CONFIG_VERSION}) ---")
        # Initialize using the schema dictionary directly
        config = ConfigGuard(
            schema=my_schema,
            config_path=config_file_path,  # Default path for loading/saving values
            autosave=False,  # Explicit saves in this example
        )

        # --- 3. Accessing Default Values (Nested) ---
        log.info("\n--- Accessing Default Values (Nested) ---")
        log.info(f"Server Host (Default): {config.server.host}")  # Attribute access
        log.info(f"Server Port (Default): {config['server']['port']}")  # Item access
        log.info(f"Database URI (Default): {config.database.uri}")  # Should be None
        log.info(f"Logging Level (Default): {config.logging.level}")
        log.info(f"Feature Flags (Default): {config.features.flags}")
        log.info(
            f"Global Security Token (Default): {config.security}"
        )  # Top-level access

        # Check a default value
        assert config.server.timeout_seconds == 30.0
        assert config.database.uri is None

        # --- 4. Accessing Schema Details (Nested) ---
        log.info("\n--- Accessing Schema Details (Nested) ---")
        log.info(
            f"Help for 'server.port': {config.server.sc_port.help}"
        )  # Schema via attribute
        log.info(
            f"Type for 'server.enabled': {config['server']['sc_enabled'].type_str}"
        )  # Schema via item
        log.info(f"Is 'database.uri' nullable? {config.database.sc_uri.nullable}")
        log.info(
            f"Default for 'logging.level': {config.logging.sc_level.default_value}"
        )
        log.info(
            f"Min value for 'database.retry_attempts': {config.database['sc_retry_attempts'].min_val}"
        )
        log.info(
            f"Allowed options for 'logging.level': {config.logging.sc_level.options}"
        )
        log.info(f"Help for top-level 'security': {config.sc_security.help}")

        assert config.database.sc_uri.nullable is True

        # --- 5. Modifying Values (Nested) ---
        log.info("\n--- Modifying Values (Nested) ---")
        config.server.port = 9000
        config["server"]["host"] = "0.0.0.0"  # Item access modification
        config.database.uri = "sqlite:///prod_nested.db"
        config.logging.level = "DEBUG"
        config.features.flags.append("beta_feature")  # Modify list in-place
        config.features.enable_beta = True
        config.security = "top-secret-global-token"  # Modify top-level

        log.info(f"Set server port to: {config.server.port}")
        log.info(f"Set server host to: {config.server.host}")
        log.info(f"Set database URI: {config.database.uri}")
        log.info(f"Set logging level to: {config.logging.level}")
        log.info(f"Updated feature flags: {config.features.flags}")
        log.info(f"Set global security token: {config.security}")

        # --- 6. Testing Validation Errors (Nested) ---
        log.info("\n--- Testing Validation (Nested) ---")
        try:
            config.server.port = 80  # Below min_val
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")

        try:
            config.logging.level = "TRACE"  # Not in options
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")

        try:
            config.server.enabled = "yes"  # Invalid type for bool
        except ValidationError as e:
            log.info(f"Caught expected validation error: {e}")

        try:
            config.database.uri = None  # Allowed due to nullable=True
            log.info(
                f"Successfully set database.uri back to None. Value: {config.database.uri}"
            )
        except ValidationError as e:
            log.error(
                f"Caught UNEXPECTED validation error setting nullable field to None: {e}"
            )

        # Reset database_uri for subsequent steps
        config.database.uri = "sqlite:///prod_nested.db"

        # --- 7. Saving Configuration (Values vs Full - Nested) ---
        log.info("\n--- Saving Configuration (Nested) ---")
        # Save only values to the default path
        log.info(f"Saving mode='values' to {config_file_path}...")
        config.save(mode="values")
        log.info(f"Content of {config_file_path} (values only - nested):")
        log.info(
            config_file_path.read_text(encoding="utf-8")
        )  # Should show nested JSON

        # Save full state (schema + values + version) to a different path
        log.info(f"\nSaving mode='full' to {full_state_file_path}...")
        config.save(filepath=full_state_file_path, mode="full")
        log.info(
            f"Content of {full_state_file_path} (full state - nested - first ~400 chars):"
        )
        log.info(
            full_state_file_path.read_text(encoding="utf-8")[:400] + "..."
        )  # Should show nested schema and values

        # --- 8. Loading Configuration (Nested) ---
        log.info("\n--- Loading Configuration (from values-only file - nested) ---")
        # Load from the file saved with mode='values' into a new instance
        config_load_values = ConfigGuard(schema=my_schema, config_path=config_file_path)
        log.info(f"Loaded Server Port: {config_load_values.server.port}")
        log.info(f"Loaded DB URI: {config_load_values.database.uri}")
        log.info(f"Loaded Logging Level: {config_load_values.logging.level}")
        log.info(f"Loaded Global Security: {config_load_values.security}")
        assert config_load_values.server.port == 9000
        assert config_load_values.database.uri == "sqlite:///prod_nested.db"
        assert config_load_values.logging.level == "DEBUG"
        assert config_load_values.security == "top-secret-global-token"
        assert (
            config_load_values.loaded_file_version is None
        )  # Values-only file has no version

        log.info("\n--- Loading Configuration (from full state file - nested) ---")
        # Load from the file saved with mode='full'
        config_load_full = ConfigGuard(
            schema=my_schema, config_path=full_state_file_path
        )
        log.info(f"Loaded Server Port: {config_load_full.server.port}")
        log.info(f"Loaded DB URI: {config_load_full.database.uri}")
        log.info(f"Loaded Logging Level: {config_load_full.logging.level}")
        log.info(f"Loaded Global Security: {config_load_full.security}")
        assert config_load_full.server.port == 9000
        assert config_load_full.database.uri == "sqlite:///prod_nested.db"
        assert config_load_full.logging.level == "DEBUG"
        assert config_load_full.security == "top-secret-global-token"
        assert (
            config_load_full.loaded_file_version == CONFIG_VERSION
        )  # Version loaded correctly

        # --- 9. Version Handling Simulation (Nested) ---
        log.info("\n--- Version Handling Simulation (Nested) ---")
        # Create a fake older config file (V1.0.0) saved in 'full' mode
        # This older version did not have sections, just flat settings
        older_version = "1.0.0"
        older_config_full_state = {
            "version": older_version,
            "schema": {  # Flat schema from V1.0.0
                "database_uri": {
                    "type": "str",
                    "nullable": False,
                    "default": "default.db",
                },
                "port": {"type": "int", "default": 8000},
                "log_level": {
                    "type": "str",
                    "default": "WARN",
                    "options": ["INFO", "WARN"],
                },
                "enabled": {"type": "bool"},
                "api_key": {
                    "type": "str",
                    "nullable": True,
                },  # Corresponds to 'security' now? Assume yes for demo.
                "retry_attempts": {"type": "int"},
                "removed_setting": {"type": "str"},
            },
            "values": {
                "database_uri": "old_db.sqlite",
                "port": 7000,
                "log_level": "INFO",
                "enabled": True,
                "api_key": "secret-v1.0",  # Will map to 'security'
                "retry_attempts": 5,  # Will map to 'database.retry_attempts'
                "removed_setting": "abc",
            },
        }
        older_file = Path(
            f"{BASE_FILENAME}_v{older_version.replace('.','_')}_full_simulated.json"
        )
        try:
            log.info(
                f"Creating simulated older flat config file ({older_version}) at {older_file}..."
            )
            older_file.write_text(
                json.dumps(older_config_full_state, indent=4), encoding="utf-8"
            )

            log.info(
                f"\nLoading older flat config ({older_version}) into current nested instance (V{CONFIG_VERSION})..."
            )
            # Initialize a new instance with the CURRENT nested schema (V2.0.0) and load the older file
            # ConfigGuard needs to handle mapping flat keys to nested structure if possible (it won't automatically)
            # Let's adjust the older file to *pretend* it had some structure matching the new one for a better migration demo
            older_config_full_state_structured = {
                "version": older_version,
                "schema": {  # Pretend V1 had *some* structure
                    "server": {
                        "type": "section",
                        "schema": {
                            "port": {"type": "int", "default": 8000},
                            "enabled": {"type": "bool"},
                        },
                    },
                    "database": {
                        "type": "section",
                        "schema": {
                            "uri": {
                                "type": "str",
                                "nullable": False,
                                "default": "default.db",
                            },
                            "retry_attempts": {"type": "int"},
                        },
                    },
                    "logging_level": {
                        "type": "str",
                        "default": "WARN",
                        "options": ["INFO", "WARN"],
                    },  # Flat
                    "security_key": {
                        "type": "str",
                        "nullable": True,
                    },  # Flat, maps to 'security'
                    "removed_section": {
                        "type": "section",
                        "schema": {"old_val": {"type": "int"}},
                    },
                },
                "values": {
                    "server": {
                        "port": 7000,
                        "enabled": True,
                    },
                    "database": {
                        "uri": "old_db.sqlite",
                        "retry_attempts": 5,
                    },
                    "logging_level": "INFO",  # Maps to logging.level
                    "security_key": "secret-v1.0",  # Maps to security
                    "removed_section": {"old_val": 123},
                },
            }
            log.info(
                f"Creating simulated older *structured* config file ({older_version}) at {older_file}..."
            )
            older_file.write_text(
                json.dumps(older_config_full_state_structured, indent=4),
                encoding="utf-8",
            )

            config_migrate = ConfigGuard(schema=my_schema, config_path=older_file)
            # The load() method within __init__ handles the migration recursively

            log.info(
                "\n--- Configuration State After Loading Older Structured Version ---"
            )
            log.info(f"Loaded File Version: {config_migrate.loaded_file_version}")
            log.info(f"Instance Version: {config_migrate.version}")
            log.info(
                f"Server Port: {config_migrate.server.port}"
            )  # Loaded from old server section
            log.info(
                f"Server Enabled: {config_migrate.server.enabled}"
            )  # Loaded from old server section
            log.info(
                f"Server Host: {config_migrate.server.host}"
            )  # Uses V2.0.0 default
            log.info(
                f"Database URI: {config_migrate.database.uri}"
            )  # Loaded from old db section
            log.info(
                f"Database Retries: {config_migrate.database.retry_attempts}"
            )  # Loaded from old db section
            log.info(
                f"Logging Level: {config_migrate.logging.level}"
            )  # Uses V2.0.0 default (key name changed)
            log.info(
                f"Logging File: {config_migrate.logging.file_path}"
            )  # Uses V2.0.0 default
            log.info(
                f"Security Token: {config_migrate.security}"
            )  # Uses V2.0.0 default (key name changed)
            log.info(
                f"Feature Flags: {config_migrate.features.flags}"
            )  # Uses V2.0.0 default (section new)

            # Assertions for migration results
            assert config_migrate.loaded_file_version == older_version
            assert config_migrate.server.port == 7000
            assert config_migrate.server.enabled is True
            assert config_migrate.server.host == "127.0.0.1"  # Default
            assert config_migrate.database.uri == "old_db.sqlite"
            assert config_migrate.database.retry_attempts == 5
            assert (
                config_migrate.logging.level == "INFO"
            )  # Default (old key 'logging_level' ignored)
            assert (
                config_migrate.security is None
            )  # Default (old key 'security_key' ignored)
            assert config_migrate.features.flags == [
                "feature_a",
                "new_dashboard",
            ]  # Default

        except (
            ValidationError,
            SchemaError,
            HandlerError,
            SettingNotFoundError,
            FileNotFoundError,
        ) as e:
            log.error(f"\n*** Error during version handling simulation: {e} ***")
        finally:
            if older_file.exists():
                older_file.unlink()
                log.debug(f"Cleaned up simulated file: {older_file}")

        # --- 10. Export Schema with Values (Nested) ---
        log.info(
            "\n--- Exporting Schema with Current Values (V2.0.0 Instance - Nested) ---"
        )
        # Use the config_load_full instance which reflects the loaded V2.0.0 state
        exported_state = config_load_full.export_schema_with_values()
        log.info("Full Config State (Schema + Values - Nested) for Frontend/API:")
        try:
            log.info(json.dumps(exported_state, indent=2, ensure_ascii=False))
            assert exported_state.get("version") == CONFIG_VERSION
            assert "server" in exported_state.get("settings", {})
            assert isinstance(
                exported_state["settings"]["server"]["value"], dict
            )  # Value is nested dict
            assert "port" in exported_state["settings"]["server"]["value"]
        except TypeError as e:
            log.error(f"Error serializing exported state to JSON: {e}")
            import pprint

            pprint.pprint(exported_state)

        # --- 11. Import Configuration Values from Dictionary (Nested) ---
        log.info("\n--- Importing Configuration Values from Dictionary (Nested) ---")
        # Create a nested dictionary with new values to import
        import_data = {
            "server": {
                "port": 5005,  # Valid change
                "host": "192.168.1.100",
                "timeout_seconds": -10.0,  # Invalid (below min_val) - should be skipped
            },
            "logging": {
                "level": "WARNING",  # Valid change
                "file_path": "/var/log/app_nested.log",
            },
            "database": {
                "uri": None,  # Valid (nullable)
            },
            "features": {
                "flags": ["core_v2"],
                "unknown_feature": True,  # Unknown key in section - should be ignored/warned
            },
            "security": "imported-global-token",  # Top-level change
            "unknown_section": {"key": "value"},  # Unknown top-level section
        }
        log.info(f"Importing data via import_config: {import_data}")

        try:
            # Use the config_load_full instance to import into
            # Reload full state first for predictable start
            config_load_full.load(filepath=full_state_file_path)
            original_timeout = config_load_full.server.timeout_seconds
            original_db_retries = config_load_full.database.retry_attempts

            config_load_full.import_config(import_data, ignore_unknown=True)

            log.info("\n--- Configuration State After Dictionary Import (Nested) ---")
            log.info(f"Imported Server Port: {config_load_full.server.port}")
            log.info(f"Imported Server Host: {config_load_full.server.host}")
            log.info(
                f"Imported Server Timeout: {config_load_full.server.timeout_seconds}"
            )  # Should be unchanged
            log.info(f"Imported Logging Level: {config_load_full.logging.level}")
            log.info(f"Imported Logging Path: {config_load_full.logging.file_path}")
            log.info(
                f"Imported DB URI: {config_load_full.database.uri}"
            )  # Should be None
            log.info(f"Imported Feature Flags: {config_load_full.features.flags}")
            log.info(f"Imported Global Security: {config_load_full.security}")

            # Verify values after import
            assert config_load_full.server.port == 5005
            assert config_load_full.server.host == "192.168.1.100"
            assert (
                config_load_full.server.timeout_seconds == original_timeout
            )  # Invalid value skipped
            assert config_load_full.logging.level == "WARNING"
            assert config_load_full.logging.file_path == "/var/log/app_nested.log"
            assert config_load_full.database.uri is None
            assert config_load_full.features.flags == ["core_v2"]
            assert config_load_full.security == "imported-global-token"

            # Test import with ignore_unknown=False
            try:
                log.info("\n--- Testing import_config with ignore_unknown=False ---")
                config_load_full.import_config(
                    {"server": {"port": 8888}, "unknown_import": True},
                    ignore_unknown=False,
                )
            except SettingNotFoundError as e:
                log.info(f"Caught expected error for unknown key during import: {e}")
            except Exception as e:
                log.error(
                    f"Caught UNEXPECTED error during ignore_unknown=False test: {e}"
                )

        except (ValidationError, SchemaError, HandlerError, SettingNotFoundError) as e:
            log.error(f"\n*** An error occurred during import_config example: {e} ***")

        # --- 12. Encryption Example (Nested) ---
        log.info(f"\n--- Encryption Example (V{CONFIG_VERSION} - Nested) ---")
        if SECRET_KEY_FILE.exists():
            key = SECRET_KEY_FILE.read_bytes()
            log.info("Loaded existing encryption key.")
        else:
            key = generate_encryption_key()
            SECRET_KEY_FILE.write_bytes(key)
            log.info(f"Generated and saved new encryption key to {SECRET_KEY_FILE}")

        try:
            # Initialize with encryption key and specific path
            enc_config = ConfigGuard(
                schema=my_schema, config_path=encrypted_file_path, encryption_key=key
            )

            log.info("Modifying values in encrypted nested config instance.")
            enc_config.database.uri = (
                "postgresql://prod_user:prod_pass@db.example.com/prod_db"
            )
            enc_config.server.port = 4443
            enc_config.logging.level = "ERROR"
            enc_config.security = "encrypted-global-token"

            # Save encrypted (try both modes)
            log.info(
                f"Saving encrypted config (mode='full') to {encrypted_file_path}..."
            )
            enc_config.save(mode="full")
            log.info("Encrypted 'full' configuration saved.")
            log.info("File content (encrypted - first 100 bytes):")
            log.info(f"{encrypted_file_path.read_bytes()[:100]}...")

            log.info(
                f"\nSaving encrypted config (mode='values') to {encrypted_file_path}..."
            )
            enc_config.save(mode="values")
            log.info("Encrypted 'values' configuration saved.")
            log.info("File content (encrypted - first 100 bytes):")
            log.info(f"{encrypted_file_path.read_bytes()[:100]}...")

            # Load encrypted into a new instance
            log.info("\n--- Loading Encrypted Nested Configuration ---")
            loaded_key = SECRET_KEY_FILE.read_bytes()
            enc_config_load = ConfigGuard(
                schema=my_schema,
                config_path=encrypted_file_path,
                encryption_key=loaded_key,
            )

            log.info(f"Loaded Database URI: {enc_config_load.database.uri}")
            log.info(f"Loaded Server Port: {enc_config_load.server.port}")
            log.info(f"Loaded Logging Level: {enc_config_load.logging.level}")
            log.info(f"Loaded Global Security: {enc_config_load.security}")
            log.info(
                f"Loaded File Version (from values save): {enc_config_load.loaded_file_version}"
            )

            # Assert values loaded correctly from the 'values' save
            assert (
                enc_config_load.database.uri
                == "postgresql://prod_user:prod_pass@db.example.com/prod_db"
            )
            assert enc_config_load.server.port == 4443
            assert enc_config_load.logging.level == "ERROR"
            assert enc_config_load.security == "encrypted-global-token"
            assert (
                enc_config_load.loaded_file_version is None
            )  # No version in values-only file

        except ImportError:
            log.warning(
                "\n*** Encryption example skipped: 'cryptography' library not installed. ***"
            )
            log.warning(
                "*** Please install it: pip install configguard[encryption] ***"
            )
        except (
            ValidationError,
            SchemaError,
            HandlerError,
            EncryptionError,
            SettingNotFoundError,
        ) as e:
            log.error(f"\n*** An error occurred during encryption example: {e} ***")

    # --- Main Exception Handling ---
    except (
        ValidationError,
        SchemaError,
        HandlerError,
        SettingNotFoundError,
        EncryptionError,
    ) as e:
        log.error(
            f"\n*** A ConfigGuard error occurred during basic usage: {e} ***",
            exc_info=True,
        )
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
                log.debug(f"File not found for cleanup: {f_path}")
        log.info("Cleanup finished.")


if __name__ == "__main__":
    run_basic_usage_example()
