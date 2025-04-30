# ConfigMaster

[![PyPI version](https://img.shields.io/pypi/v/configmaster.svg)](https://pypi.org/project/configmaster/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/configmaster.svg)](https://pypi.org/project/configmaster/)
[![PyPI license](https://img.shields.io/pypi/l/configmaster.svg)](https://github.com/ParisNeo/ConfigMaster/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/configmaster)](https://pepy.tech/project/configmaster)
<!-- [![Build Status](https://github.com/ParisNeo/ConfigMaster/actions/workflows/ci.yml/badge.svg)](https://github.com/ParisNeo/ConfigMaster/actions/workflows/ci.yml) Placeholder -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<!-- [![Documentation Status](https://parisneo.github.io/ConfigMaster/badge/?version=latest)](https://parisneo.github.io/ConfigMaster/) Placeholder -->

---

**Tired of fragile, untyped, and insecure configuration files in your Python projects?**

**ConfigMaster** is here to revolutionize how you manage application settings. Move beyond basic dictionaries and `.ini` files to a robust, schema-driven system that offers **type safety, validation, encryption, versioning, multiple storage backends, and effortless migration.**

Built for developers who demand reliability and flexibility, ConfigMaster ensures your configurations are always valid, secure, and easy to manage, saving you debugging time and preventing runtime errors.

**Level up your configuration game. Gain control, ensure safety, and embrace flexibility.**

---

## ✨ Key Features

*   📝 **Schema-Driven:** Define your configuration structure with types (`str`, `int`, `float`, `bool`, `list`), defaults, help text, and validation rules (`min_val`, `max_val`, `options`, `nullable`). Includes schema versioning!
*   🔒 **Built-in Encryption:** Secure sensitive configuration values transparently using Fernet encryption (requires `cryptography`).
*   💾 **Multiple Backends:** Store configurations in various formats (JSON included, YAML/TOML/SQLite planned) through an extensible handler system. Handlers manage format specifics and encryption.
*   🔄 **Versioning & Migration:** Embed versions in your schema. ConfigMaster automatically handles loading older configuration versions, applying compatible values and using defaults for new settings. Protects against loading newer-than-expected configs.
*   ⚙️ **Flexible Save Modes:** Choose to save only the configuration *values* (default) or the *full state* including version, schema, and values – perfect for standalone configuration tools or backups.
*   🐍 **Intuitive Access:** Access configuration values naturally using attribute (`config.my_setting`) or dictionary (`config['my_setting']`) syntax. Access schema details easily (`config.sc_my_setting`).
*   ✔️ **Automatic Validation:** Values are automatically validated against the schema upon setting or loading, preventing invalid states.
*   📤 **Easy Export/Import:** Export the current schema and values (`export_schema_with_values()`) for UIs or APIs. Import values from dictionaries (`import_config()`).
*   🧩 **Extensible:** Designed with a clear handler interface to easily add support for new storage backends.

---

## 🤔 Why Choose ConfigMaster?

*   **Reduce Runtime Errors:** Catch configuration mistakes early with schema validation, not when your application crashes.
*   **Improve Maintainability:** Self-documenting schemas (`help` text) make configurations easier to understand and manage.
*   **Enhance Security:** Protect API keys, database credentials, and other secrets with built-in, easy-to-use encryption.
*   **Simplify Updates:** Effortlessly handle configuration changes between application versions with automatic migration logic.
*   **Boost Developer Experience:** Focus on your application logic, not boilerplate configuration parsing and validation code.
*   **Adaptable Storage:** Choose the storage format that best suits your needs, without changing your application code.

---

## 🚀 Installation

```bash
pip install configmaster
```

For encryption features, you also need `cryptography`:

```bash
pip install configmaster[encryption]
# or
pip install cryptography
```

---

## ⚡ Quick Start

```python
from configmaster import ConfigMaster, ValidationError, generate_encryption_key
from pathlib import Path

# 1. Define your schema (including a version!)
CONFIG_VERSION = "1.0.0"
my_schema = {
    "__version__": CONFIG_VERSION,
    "database_uri": {
        "type": "str",
        "nullable": True, # Allow None
        "default": None,
        "help": "Database connection string."
    },
    "port": {
        "type": "int",
        "default": 8080,
        "min_val": 1024,
        "help": "Network port to listen on."
    },
    "log_level": {
        "type": "str",
        "default": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
        "help": "Logging level."
    },
    "api_key": { # Sensitive data
        "type": "str",
        "nullable": True,
        "default": None,
        "help": "API Key for external service."
    }
}

# 2. Setup paths and optional encryption key
config_file = Path("app_settings.json")
# secret_key = generate_encryption_key() # Generate once and store securely
# print(f"Generated Key: {secret_key.decode()}")
# Example key (DO NOT use this in production)
secret_key = b'qXJDWAdLgXpPTN8DRk8nL9zptC0qd-ed352hGjFfaH4='

# 3. Initialize ConfigMaster
# config = ConfigMaster(schema=my_schema, config_path=config_file) # Without encryption
config = ConfigMaster(
    schema=my_schema,
    config_path=config_file,
    encryption_key=secret_key # Enable encryption
)

# 4. Access values (defaults initially, loaded from file if exists)
print(f"Port: {config.port}")
print(f"Log Level: {config['log_level']}") # Dict access works too

# 5. Access schema details
print(f"Help for port: {config.sc_port.help}")
print(f"Is API Key nullable? {config.sc_api_key.nullable}")

# 6. Modify values (validation happens automatically)
try:
    config.port = 9000
    config.log_level = "DEBUG"
    config.api_key = "very_secret_key_123"
    # config.port = 80 # This would raise ValidationError
except ValidationError as e:
    print(f"Error setting value: {e}")

print(f"New Port: {config.port}")
print(f"API Key set: {'Yes' if config.api_key else 'No'}")

# 7. Save the configuration
# Save only the current values (encrypted if key was provided)
config.save(mode='values')
print(f"Configuration values saved to {config_file}")

# Or save the full state (version, schema, values)
# config.save(mode='full', filepath="app_settings_full_state.json")
# print("Full configuration state saved.")

# Config is automatically loaded on next initialization if file exists
# config_reloaded = ConfigMaster(schema=my_schema, config_path=config_file, encryption_key=secret_key)
# print(f"Reloaded Port: {config_reloaded.port}")
```

---

## 📚 Core Concepts

*   **Schema (`__version__`, Settings Definitions):** The heart of ConfigMaster. A Python dictionary defining the structure, types, defaults, validation rules (`nullable`, `options`, `min_val`, `max_val`), and help text for each configuration setting. It **must** include a top-level `__version__` key (e.g., `"1.0.0"`) for version tracking.
*   **ConfigMaster Object:** The main object you interact with. It holds the schema, the current configuration values, and provides methods for loading, saving, validation, and access. Access values like attributes (`config.setting`) or dictionary items (`config['setting']`). Access schema details using the `sc_` prefix (`config.sc_setting` or `config['sc_setting']`).
*   **Storage Handlers:** Internal components responsible for reading/writing configuration data to specific formats (JSON, YAML, etc.) and handling encryption/decryption transparently if an `encryption_key` is provided to `ConfigMaster`. You don't usually interact with handlers directly; `ConfigMaster` selects the correct one based on the `config_path` file extension.
*   **Save Modes (`values` vs `full`):**
    *   `config.save(mode='values')`: Saves *only* the current key-value pairs. This is the typical mode for runtime configuration. The file structure depends on the handler (e.g., a simple JSON dict).
    *   `config.save(mode='full')`: Saves the instance version, the schema definition, *and* the current values. Useful for backups, transferring state, or feeding configuration UIs. The file structure includes specific keys like `version`, `schema`, `values`.
*   **Versioning & Migration:** When `ConfigMaster` loads a configuration file (especially one saved in `full` mode), it compares the version in the file (`loaded_file_version`) with the version defined in the schema it was initialized with (`config.version`).
    *   **File Newer:** Raises `SchemaError` (prevents loading incompatible future configs).
    *   **File Older:** Loads values for settings that still exist in the *current* schema, logs warnings for removed settings, and uses *current* defaults for new settings. Basic type coercion (e.g., int <-> float <-> numeric string) is attempted if types differ between loaded schema and instance schema.
    *   **Versions Match:** Loads values. Issues a warning if the schema definition in the file differs from the instance's schema, but proceeds using the instance's schema for validation.
    *   **No Version in File:** Assumes a `values-only` file or legacy format; loads values directly against the current schema.
*   **Encryption:** When an `encryption_key` is provided during `ConfigMaster` initialization, the selected storage handler automatically encrypts data *before* writing to the file and decrypts it *after* reading. The file content itself will be unreadable ciphertext. Uses Fernet symmetric encryption (requires `cryptography`).

---

## 📖 Detailed Usage

### 1. Defining the Schema

The schema is a Python dictionary. The top level must contain a `__version__` key. Other keys are the names of your configuration settings.

```python
# Example Schema Dictionary
CONFIG_VERSION = "2.1.0"

my_app_schema = {
    "__version__": CONFIG_VERSION,

    "service_name": {
        "type": "str",
        "default": "DefaultApp",
        "help": "Identifier for the service."
    },
    "listen_port": {
        "type": "int",
        "default": 9090,
        "min_val": 1024,
        "max_val": 65535,
        "help": "Port number for incoming connections."
    },
    "log_level": {
        "type": "str",
        "default": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "help": "Logging verbosity level."
    },
    "use_tls": {
        "type": "bool",
        "default": False,
        "help": "Enable TLS/SSL encryption."
    },
    "retry_delay": {
        "type": "float",
        "default": 0.5,
        "min_val": 0.0,
        "help": "Delay between retry attempts in seconds."
    },
    "allowed_origins": {
        "type": "list",
        "default": [], # Default to an empty list
        "help": "List of allowed CORS origins (strings)."
    },
    "db_connection_uri": {
        "type": "str",
        "default": None, # Explicitly no default connection
        "nullable": True, # Allow the setting to be None
        "help": "Database connection string (set to null if not used)."
    }
    # Add other settings as needed...
}
```

**Schema Definition Keys:**

*   `__version__` (str, **Required**): The semantic version (e.g., "1.0.0") of this schema definition. Used for migration.
*   `type` (str, **Required**): The expected data type. Supported: `"str"`, `"int"`, `"float"`, `"bool"`, `"list"`.
*   `default` (any, **Required unless `nullable` is True and no default is desired**): The default value used if not set or loaded. Must be valid according to `type` and other constraints. If `nullable` is True, you can omit `default` to default to `None`.
*   `help` (str, **Required**): A description of the setting, used for documentation and potentially UIs.
*   `nullable` (bool, Optional): If `True`, allows the setting's value to be `None`. Defaults to `False`.
*   `options` (list, Optional): A list of allowed values for this setting. Validation ensures the value is one of these options.
*   `min_val` (int/float, Optional): The minimum allowed numeric value (for `int` or `float` types).
*   `max_val` (int/float, Optional): The maximum allowed numeric value (for `int` or `float` types).

### 2. Initializing ConfigMaster

```python
from configmaster import ConfigMaster, generate_encryption_key
from pathlib import Path

# Schema can be a dictionary...
schema_dict = {"__version__": "1.0", "port": {"type": "int", "default": 80}}
# ...or a path to a JSON file containing the schema definition
schema_file = Path("path/to/my_schema.json")

# Config file path
cfg_path = Path("my_settings.json") # or .bin, .enc for encrypted

# --- Examples ---

# Basic: Load schema dict, save/load values to cfg_path
# config1 = ConfigMaster(schema=schema_dict, config_path=cfg_path)

# Load schema from file, save/load values
# config2 = ConfigMaster(schema=schema_file, config_path=cfg_path)

# With encryption
# key = generate_encryption_key() # Store this key securely!
# config3 = ConfigMaster(schema=schema_dict, config_path=cfg_path, encryption_key=key)

# With autosave (saves values only on change)
# config4 = ConfigMaster(schema=schema_dict, config_path=cfg_path, autosave=True)

# No config file path (in-memory config, useful for testing or defaults)
# config5 = ConfigMaster(schema=schema_dict)
# config5.port = 1234 # Changes exist only in memory unless explicitly saved later

# --- Full Example ---
try:
    # Generate key only once for the example run
    key_path = Path("example.key")
    if key_path.exists():
        enc_key = key_path.read_bytes()
    else:
        enc_key = generate_encryption_key()
        key_path.write_bytes(enc_key)

    config = ConfigMaster(
        schema=my_app_schema, # Use the detailed schema from above
        config_path=Path("app_runtime_config.json"),
        encryption_key=enc_key,
        autosave=False
    )
    print(f"ConfigMaster initialized with version: {config.version}")

except Exception as e:
    print(f"Error during initialization: {e}")
finally:
    if key_path.exists(): key_path.unlink() # Clean up key file

```

ConfigMaster automatically attempts to `load()` configuration from `config_path` during initialization if the path and a suitable handler exist.

### 3. Accessing Values & Schema

```python
# Assuming 'config' is an initialized ConfigMaster instance

# --- Accessing Values ---
current_port = config.listen_port
current_log_level = config['log_level'] # Dict access

print(f"Port: {current_port}, Level: {current_log_level}")

# --- Modifying Values (Triggers Validation) ---
config.listen_port = 8443
config['log_level'] = 'DEBUG'
config.allowed_origins.append("https://example.com") # Modify list directly

# Invalid modification will raise ValidationError
try:
    config.retry_delay = -1.0
except ValidationError as e:
    print(f"Validation Error: {e}")
    print(f"Retry delay remains: {config.retry_delay}") # Value is unchanged

# --- Accessing Schema ---
port_schema = config.sc_listen_port
log_level_schema = config['sc_log_level']

print(f"Help for port: {port_schema.help}")
print(f"Allowed log levels: {log_level_schema.options}")
print(f"Is db_connection_uri nullable? {config.sc_db_connection_uri.nullable}")
print(f"Default retry delay: {config.sc_retry_delay.default_value}")
```

### 4. Saving & Loading

Loading typically happens automatically during initialization if `config_path` points to an existing, valid file. You can manually trigger a reload using `config.load()`.

Saving requires specifying the `mode`:

```python
# --- Saving ---

# Save ONLY the current values (common use case)
# Uses the path provided in __init__ if filepath not specified
# Encrypted automatically if key was provided
# config.save(mode='values')
# config.save(filepath="other_values.json", mode='values')

# Save the FULL state (version, schema definition, values)
# Useful for backups, transferring state, or config UIs
# config.save(mode='full')
# config.save(filepath="backup_state_v{config.version}.json", mode='full')


# --- Loading (Manual Trigger) ---
# Usually not needed as it happens on init, but useful for re-loading

try:
    # config.load() # Reloads from the path specified in __init__
    # config.load(filepath="specific_config_to_load.json")
    print("Configuration reloaded successfully.")
except FileNotFoundError:
    print("Config file not found for manual load.")
except Exception as e:
    print(f"Error during manual load: {e}")

```

### 5. Versioning & Migration

Versioning is handled automatically during `load()` based on the `__version__` key in your schema and the `version` field potentially stored in the configuration file (if saved with `mode='full'`).

*   **Define Version:** Always include `"__version__": "X.Y.Z"` in your schema dictionary.
*   **Loading:**
    *   If loading a `full` file: Versions are compared. Older files trigger migration (see Core Concepts). Newer files raise `SchemaError`.
    *   If loading a `values` file (no version info): Values are applied directly to the current instance schema.
*   **Migration Logic:** When an older `full` file is loaded:
    1.  Values for settings existing in both old and new schemas are loaded (with potential type coercion warnings).
    2.  Settings present in the old file but *not* in the new schema are logged and skipped.
    3.  Settings present in the new schema but *not* in the old file retain their *new* default values.
    4.  Validation always occurs against the *new* (instance's) schema. If a migrated value fails validation against the new schema, it's reset to the new default.

You generally don't need to write migration code yourself for simple cases; just update the schema dictionary for new application versions.

### 6. Encryption

Encryption is enabled by providing a valid `encryption_key` during `ConfigMaster` initialization.

```python
from configmaster import ConfigMaster, generate_encryption_key
from pathlib import Path

schema_dict = {"__version__": "1.0", "api_secret": {"type": "str", "nullable": True, "help":"Secret Value"}}
config_path = Path("secrets.bin") # Use .bin or .enc extension convention
key_file = Path("secret.key")

# 1. Generate and store key securely (only once)
if not key_file.exists():
    secret_key = generate_encryption_key()
    key_file.write_bytes(secret_key)
    print("Generated new encryption key.")
else:
    secret_key = key_file.read_bytes()
    print("Loaded existing encryption key.")

# 2. Initialize with key
try:
    secure_config = ConfigMaster(
        schema=schema_dict,
        config_path=config_path,
        encryption_key=secret_key
    )

    # 3. Set sensitive data
    secure_config.api_secret = "my-super-secret-value"
    print("Set sensitive value.")

    # 4. Save (automatically encrypted by the handler)
    secure_config.save(mode='values') # or 'full'
    print(f"Encrypted configuration saved to {config_path}.")
    print(f"File content preview (should be ciphertext): {config_path.read_bytes()[:60]}...")

    # 5. Reload (automatically decrypted by the handler)
    secure_config_reloaded = ConfigMaster(
        schema=schema_dict,
        config_path=config_path,
        encryption_key=secret_key
    )
    print(f"Reloaded secret: {secure_config_reloaded.api_secret}")
    assert secure_config_reloaded.api_secret == "my-super-secret-value"

except ImportError:
    print("Encryption requires 'cryptography'. Please install.")
except Exception as e:
    print(f"Encryption example error: {e}")
finally:
    # Clean up example files
    if config_path.exists(): config_path.unlink()
    if key_file.exists(): key_file.unlink()

```

### 7. Importing/Exporting Data

*   **Exporting Schema + Values:** Get a snapshot of the current instance state for UIs or APIs.

    ```python
    # config is an initialized ConfigMaster instance
    current_state = config.export_schema_with_values()

    # 'current_state' dictionary structure:
    # {
    #   "version": "1.1.0", # Instance version
    #   "schema": { ... }, # Instance schema definition
    #   "settings": {
    #     "setting_name": {
    #       "schema": { ... }, # Specific setting schema dict
    #       "value": ...       # Current value
    #     },
    #     ...
    #   }
    # }

    import json
    print(json.dumps(current_state, indent=2))
    ```

*   **Importing Values from Dictionary:** Update settings from a dictionary (e.g., received from an API or UI).

    ```python
    new_values = {
        "listen_port": 8888,
        "log_level": "WARNING",
        "db_connection_uri": None,
        "unknown_setting": "ignore_me" # Will be ignored or raise error
    }

    try:
        # Update config, ignore keys not in schema, validation occurs
        config.import_config(new_values, ignore_unknown=True)
        print("Import successful.")
        print(f"Port after import: {config.listen_port}")
    except Exception as e:
        print(f"Import failed: {e}")
    ```

---

## 💡 Use Cases

*   **Standard Application Settings:** Manage ports, file paths, feature flags, logging levels reliably.
*   **Secret Management:** Securely store API keys, database credentials, tokens using encryption. Create simple "secret vaults".
*   **Theming & UI Configuration:** Define and manage UI themes, layouts, user preferences with type safety.
*   **Tool Configuration:** Provide robust configuration for command-line tools or utilities.
*   **Multi-Environment Setups:** Use separate (potentially encrypted) config files for development, staging, and production managed by the same schema.
*   **Dynamic Configuration UIs:** Use `export_schema_with_values()` to generate data for frontends (like PyQt, web UIs) that allow users to edit settings graphically, validating input based on the schema.

---

## 🔧 Advanced Topics

*   **Custom Storage Handlers:** Need to store configs in a database, Redis, or a custom format? Implement your own handler by subclassing `configmaster.handlers.StorageHandler` and implementing the `load` and `save` methods, including encryption/decryption logic if needed. Register your handler's file extension in `configmaster.handlers.HANDLER_MAP`.

---

## 🤝 Contributing

Contributions are welcome! We aim for high code quality.

1.  **Fork** the repository on GitHub.
2.  Create a **new branch** for your feature or bug fix.
3.  **Code:**
    *   Follow **PEP 8** guidelines.
    *   Use **Black** for code formatting.
    *   Add **type hints** (`typing`) to all functions and methods.
    *   Write clear **docstrings** (Google style preferred).
    *   Add **unit tests** (`pytest`) covering your changes in the `tests/` directory. Ensure high test coverage.
4.  **Lint & Test:** Run `black .`, `mypy configmaster`, and `pytest` locally to ensure checks pass.
5.  **Commit** your changes with descriptive messages.
6.  Push your branch to your fork and open a **Pull Request** against the `main` branch of the original repository.
7.  Ensure GitHub Actions CI checks pass on your PR.

Please see the (future) `CONTRIBUTING.md` file for more detailed guidelines.

---

## 📜 License

ConfigMaster is distributed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for more information.

---

<p align="center">
  Built with ❤️ by ParisNeo with the help of Gemini 2.5
</p>