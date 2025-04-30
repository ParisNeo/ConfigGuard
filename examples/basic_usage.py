# examples/basic_usage.py

from configmaster import ConfigMaster, ValidationError, generate_encryption_key, set_log_level
from configmaster.exceptions import HandlerError,EncryptionError,SchemaError,ValidationError
from pathlib import Path
import json
import os

# Set log level for more verbose output during example run
set_log_level("DEBUG")

# --- Configuration ---
CONFIG_FILENAME = "my_app_config.json"
ENCRYPTED_CONFIG_FILENAME = "my_app_config_encrypted.bin" # Use different extension for encrypted
SECRET_KEY_FILE = "config.secret"
SCHEMA_FILE = "my_app_schema.json" # Example of loading schema from file

# --- 1. Define Schema ---
my_schema = {
    "database_uri": {
        "type": "str",
        "default": "sqlite:///default.db",
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
        "default": None, # No default key
        "nullable": True, # Explicitly allow None
        "help": "API key for external service integration (optional)."
    },
    "retry_attempts": {
         "type": "int",
         "default": 3,
         "min_val": 0,
         "help": "Number of times to retry failed operations."
    }
}

# --- Save schema to file (for demo purposes) ---
schema_path = Path(SCHEMA_FILE)
print(f"\n--- Saving schema definition to {schema_path} ---")
try:
    with open(schema_path, 'w', encoding='utf-8') as f:
        json.dump(my_schema, f, indent=4)
    print(f"Schema saved successfully.")
except Exception as e:
    print(f"Error saving schema: {e}")


# --- 2. Basic Usage (Loading Schema from File) ---
print(f"\n--- Basic Usage: Loading schema from {schema_path} ---")
config_file = Path(CONFIG_FILENAME)
# Ensure config file doesn't exist from previous runs for a clean start
if config_file.exists():
    config_file.unlink()

try:
    # Initialize using schema file and config file path
    config = ConfigMaster(schema=schema_path, config_path=config_file, autosave=False) # Autosave off for explicit save demo

    # --- 3. Accessing Values (Defaults initially) ---
    print("\n--- Accessing Default Values ---")
    print(f"Database URI: {config.database_uri}")
    print(f"Port (attribute access): {config.port}")
    print(f"Port (dict access): {config['port']}")
    print(f"Enabled status: {config.enabled}")
    print(f"Feature Flags: {config.feature_flags}")
    print(f"API Key: {config.api_key}") # Default is None

    # --- 4. Accessing Schema Details ---
    print("\n--- Accessing Schema Details ---")
    print(f"Help for 'port': {config.sc_port.help}")
    print(f"Type for 'enabled': {config.sc_enabled.type_str}")
    print(f"Default for 'log_level': {config.sc_log_level.default_value}")
    print(f"Min value for 'retry_attempts': {config.sc_retry_attempts.min_val}")
    print(f"Allowed options for 'log_level': {config['sc_log_level'].options}") # Dict access for schema

    # --- 5. Modifying Values (Validation) ---
    print("\n--- Modifying Values ---")
    config.port = 9000
    config['log_level'] = "DEBUG" # Dict access modification
    config.feature_flags.append("beta_feature") # Modify list in-place
    config.enabled = False
    config.api_key = "secret-api-key-12345"
    print(f"Set port to: {config.port}")
    print(f"Set log_level to: {config.log_level}")
    print(f"Updated feature flags: {config.feature_flags}")
    print(f"Set enabled to: {config.enabled}")
    print(f"Set API key: {config.api_key}")

    # --- Validation Errors ---
    print("\n--- Testing Validation ---")
    try:
        config.port = 80 # Below min_val
    except ValidationError as e:
        print(f"Caught expected validation error: {e}")

    try:
        config.log_level = "TRACE" # Not in options
    except ValidationError as e:
        print(f"Caught expected validation error: {e}")

    try:
         config.enabled = "yes" # Invalid type (though schema tries coercion)
    except ValidationError as e:
        print(f"Caught expected validation error: {e}")


    # --- 6. Saving Configuration ---
    print("\n--- Saving Configuration ---")
    config.save()
    print(f"Configuration saved to {config_file}")
    print("File content:")
    print(config_file.read_text())

    # --- 7. Loading Configuration ---
    print("\n--- Loading Configuration ---")
    config2 = ConfigMaster(schema=my_schema, config_path=config_file) # Use original schema dict this time
    print(f"Loaded Port: {config2.port}")
    print(f"Loaded Log Level: {config2.log_level}")
    print(f"Loaded Enabled: {config2.enabled}")
    print(f"Loaded API Key: {config2.api_key}")
    assert config2.port == 9000
    assert config2.log_level == "DEBUG"
    assert not config2.enabled
    assert "beta_feature" in config2.feature_flags

    # --- 8. Get Schema/Config Dictionaries ---
    print("\n--- Getting Schema/Config as Dictionaries ---")
    schema_for_frontend = config.get_schema_dict()
    print("Schema Dictionary:")
    print(json.dumps(schema_for_frontend, indent=2))

    current_values = config.get_config_dict()
    print("\nConfig Values Dictionary:")
    print(json.dumps(current_values, indent=2))

    # --- Iteration and Membership ---
    print("\n--- Iteration and Membership ---")
    print(f"Number of settings: {len(config)}")
    print("Settings names:")
    for setting_name in config:
        print(f"- {setting_name}")
    print(f"'port' in config? {'port' in config}")
    print(f"'nonexistent' in config? {'nonexistent' in config}")


except (ValidationError, SchemaError, HandlerError) as e:
    print(f"\n*** An error occurred during basic usage: {e} ***")
except Exception as e:
     print(f"\n*** An unexpected error occurred: {e} ***")
     import traceback
     traceback.print_exc()


# --- 9. Encryption Example ---
print(f"\n--- Encryption Example ---")
encrypted_config_path = Path(ENCRYPTED_CONFIG_FILENAME)
secret_file_path = Path(SECRET_KEY_FILE)

# Ensure clean start
if encrypted_config_path.exists():
    encrypted_config_path.unlink()
if secret_file_path.exists():
     secret_file_path.unlink()



try:
    # Generate and save a key
    key = generate_encryption_key()
    secret_file_path.write_bytes(key)
    print(f"Generated and saved encryption key to {secret_file_path}")

    # Initialize with encryption key
    enc_config = ConfigMaster(schema=my_schema, config_path=encrypted_config_path, encryption_key=key)

    # Modify some values
    enc_config.database_uri = "postgresql://prod_user:prod_pass@db.example.com/prod_db"
    enc_config.port = 4443 
    enc_config.log_level = "WARNING"
    print("Modified values in encrypted config instance.")

    # Save encrypted
    enc_config.save()
    print(f"Encrypted configuration saved to {encrypted_config_path}")
    print("File content (should be unreadable):")
    # Limit reading in case it's large binary data
    try:
        print(encrypted_config_path.read_bytes()[:100].decode('utf-8', errors='replace') + "...")
    except Exception:
         print("[Binary content, cannot display as text]")


    # Load encrypted
    print("\n--- Loading Encrypted Configuration ---")
    # Read key from file
    loaded_key = secret_file_path.read_bytes()
    enc_config_load = ConfigMaster(schema=my_schema, config_path=encrypted_config_path, encryption_key=loaded_key)

    print(f"Loaded Database URI: {enc_config_load.database_uri}")
    print(f"Loaded Port: {enc_config_load.port}")
    print(f"Loaded Log Level: {enc_config_load.log_level}")
    assert enc_config_load.database_uri == "postgresql://prod_user:prod_pass@db.example.com/prod_db"
    assert enc_config_load.port == 4443
    assert enc_config_load.log_level == "WARNING"

    # --- 10. Export Schema with Values ---
    print("\n--- Exporting Schema with Current Values ---")
    full_config_state = config.export_schema_with_values()
    print("Full Config State (Schema + Values):")
    # Print as nicely formatted JSON
    try:
        print(json.dumps(full_config_state, indent=2, ensure_ascii=False))
    except TypeError as e:
         print(f"Error serializing full config state to JSON: {e}")
         # Fallback print
         import pprint
         pprint.pprint(full_config_state)

except ImportError:
     print("\n*** Encryption example skipped: 'cryptography' library not installed. ***")
     print("*** Please install it: pip install cryptography ***")
except (ValidationError, SchemaError, HandlerError, EncryptionError) as e:
    print(f"\n*** An error occurred during encryption example: {e} ***")
except Exception as e:
     print(f"\n*** An unexpected error occurred during encryption example: {e} ***")
     import traceback
     traceback.print_exc()

finally:
     # Clean up generated files
     print("\n--- Cleaning up generated files ---")
     files_to_remove = [
         CONFIG_FILENAME,
         ENCRYPTED_CONFIG_FILENAME,
         SECRET_KEY_FILE,
         SCHEMA_FILE
     ]
     for f in files_to_remove:
         p = Path(f)
         if p.exists():
             try:
                 p.unlink()
                 print(f"Removed {p}")
             except OSError as e:
                 print(f"Error removing {p}: {e}")
