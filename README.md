# ConfigMaster

[![PyPI version](https://img.shields.io/pypi/v/configmaster.svg)](https://pypi.org/project/configmaster/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/configmaster.svg)](https://pypi.org/project/configmaster/)
[![PyPI license](https://img.shields.io/pypi/l/configmaster.svg)](https://github.com/ParisNeo/ConfigMaster/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/configmaster)](https://pepy.tech/project/configmaster)
[![Documentation Status](https://img.shields.io/badge/docs-latest-blue.svg)](https://parisneo.github.io/ConfigMaster/)
<!-- [![Build Status](https://github.com/ParisNeo/ConfigMaster/actions/workflows/ci.yml/badge.svg)](https://github.com/ParisNeo/ConfigMaster/actions/workflows/ci.yml) Placeholder -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

**Stop fighting inconsistent, error-prone, and insecure configuration files!** 🚀

**ConfigMaster** elevates your Python configuration management from fragile text files and basic dictionaries to a powerful, **schema-driven fortress**. Gain unparalleled control with:

*   Strict **Type Safety** & **Validation Rules**
*   Built-in **Encryption** for your secrets
*   Seamless **Versioning** & **Migration**
*   Support for **Multiple Storage Formats** (JSON now, more coming!)
*   Intuitive **Nested Configuration** handling

**Why settle?** Ensure your app settings are always valid, secure, and effortlessly maintainable. Prevent runtime surprises, simplify updates, and focus on building great features, not debugging config errors.

**Adopt ConfigMaster and configure with confidence!**

---

## ✨ Key Features

*   📝 **Schema-Driven:** Define your configuration structure with types, defaults, help text, and validation rules (`min_val`, `max_val`, `options`, `nullable`). Includes schema versioning!
*   🔒 **Built-in Encryption:** Secure sensitive configuration values transparently using Fernet encryption (requires `cryptography`). Handled automatically by storage backends.
*   💾 **Multiple Backends:** Store configurations in various formats (JSON included, YAML/TOML/SQLite planned) through an extensible handler system.
*   🔄 **Versioning & Migration:** Embed versions in your schema. ConfigMaster automatically handles loading older configuration versions and migrating settings gracefully.
*   <0xF0><0x9F><0x97><0x84>️ **Flexible Save Modes:** Choose to save only the configuration *values* (default) or the *full state* including version, schema, and values.
*   <0xF0><0x9F><0xA7><0xB1> **Supported Types:** Define settings as `str`, `int`, `float`, `bool`, or `list`. *(Note: List element types are not currently validated by the schema)*.
*   <0xF0><0x9F><0x94><0x8E> **Nested Configuration:** Manage complex settings using dot notation naming conventions (e.g., `database.host`, `database.port`). *(True nested schema validation planned)*.
*   🐍 **Intuitive Access:** Access configuration values naturally using attribute (`config.my_setting`) or dictionary (`config['my_setting']`) syntax. Access schema details easily (`config.sc_my_setting`).
*   ✔️ **Automatic Validation:** Values are automatically validated against the schema upon setting or loading, preventing invalid states.
*   📤 **Easy Export/Import:** Export the current schema and values (`export_schema_with_values()`) for UIs or APIs. Import values from dictionaries (`import_config()`).
*   🧩 **Extensible:** Designed with a clear handler interface to easily add support for new storage backends.

---

## 🤔 Why Choose ConfigMaster?

*   **Eliminate Config Errors:** Catch issues at definition or load time, not during critical runtime operations.
*   **Secure Your Secrets:** Easily encrypt API keys, passwords, and tokens without complex setup.
*   **Future-Proof Your App:** Handle config changes between versions smoothly with built-in migration.
*   **Improve Code Clarity:** Self-documenting schemas make settings understandable and maintainable.
*   **Increase Productivity:** Stop writing boilerplate config parsing/validation code.
*   **Storage Freedom:** Use JSON today, YAML/TOML/DB tomorrow, without rewriting your core logic.

---

## 🚀 Installation

```bash
pip install configmaster
```

For **encryption** features:

```bash
pip install configmaster[encryption]
# or separately: pip install cryptography
```

*(Support for other backends like YAML/TOML will require optional installs in the future).*

---

## ⚡ Quick Start

```python
from configmaster import ConfigMaster, ValidationError, generate_encryption_key
from pathlib import Path
import typing # Required for type hinting the schema dict

# 1. Define your schema (with version!)
CONFIG_VERSION = "1.0.0"
my_schema: typing.Dict[str, typing.Any] = { # Add type hint for clarity
    "__version__": CONFIG_VERSION,
    "database.uri": { # Use dot notation for logical nesting
        "type": "str",
        "nullable": True,
        "default": "sqlite:///default.db",
        "help": "Database connection string."
    },
    "server.port": {
        "type": "int",
        "default": 8080,
        "min_val": 1024,
        "help": "Network port."
    },
    "security.api_key": { # Sensitive data
        "type": "str",
        "nullable": True,
        "default": None,
        "help": "API Key (leave null if unused)."
    }
}

# 2. Setup paths and optional encryption key
config_file = Path("app_settings.bin") # Use .bin for encrypted
# key = generate_encryption_key() # Generate once and store securely!
# print(f"Generated Key: {key.decode()}")
# Example key (DO NOT use this in production, generate your own!)
key = b'p4SDfnaAZFq9N5EhrNDfGVOQ1C6pShR1w7TKVmqw0rI='

# 3. Initialize ConfigMaster (with encryption)
try:
    config = ConfigMaster(
        schema=my_schema,
        config_path=config_file,
        encryption_key=key
    )
except ImportError:
    print("Encryption requires 'cryptography'. Install with: pip install configmaster[encryption]")
    # Initialize without encryption as a fallback for the example
    config = ConfigMaster(schema=my_schema, config_path=Path("app_settings.json"))


# 4. Access values (dot notation works for simple names, dict for complex)
# Use dictionary access for names containing dots
print(f"Database: {config['database.uri']}")
print(f"Port: {config['server.port']}")

# 5. Access schema details (use dict access for dotted names)
print(f"Port Help: {config['sc_server.port'].help}")
print(f"Is API Key nullable? {config['sc_security.api_key'].nullable}")

# 6. Modify values (validation happens automatically)
try:
    config['server.port'] = 9000
    config['security.api_key'] = "my-super-secret"
    # config['server.port'] = 80 # This would raise ValidationError
except ValidationError as e:
    print(f"Error setting value: {e}")

print(f"New Port: {config['server.port']}")
print(f"API Key set: {'Yes' if config['security.api_key'] else 'No'}")

# 7. Save configuration values (encrypted if key was provided)
# Use mode='values' for typical runtime saving
config.save(mode='values')
print(f"Settings saved to {config.config_path}") # Access internal attr for demo

# Load on next init is automatic! If the file exists, ConfigMaster loads it.
# Example:
# config_reloaded = ConfigMaster(schema=my_schema, config_path=config_file, encryption_key=key)
# print(f"Reloaded Port: {config_reloaded['server.port']}") # Output: 9000
```

---

## 📚 Core Concepts

*   **Schema (`__version__`, Settings Definitions):** The blueprint for your configuration. A Python dictionary defining the version, settings names (use dot notation like `database.host` for logical grouping), types (`str`, `int`, `float`, `bool`, `list`), defaults, validation rules (`nullable`, `options`, `min_val`, `max_val`), and help text. The `__version__` key is mandatory for version control.
*   **ConfigMaster Object:** Your main interface. Holds the schema and current values. Access settings via dictionary syntax (`config['database.host']`) especially when using dot notation in names, or attribute syntax (`config.simple_setting`) for names without dots. Access schema via `config['sc_database.host']` or `config.sc_simple_setting`.
*   **Storage Handlers:** The engine parts handling specific file formats (JSON, future YAML/TOML/DB) and transparent encryption/decryption based on the key you provide to `ConfigMaster`. Chosen based on file extension (e.g., `.json`, `.bin`, `.enc` often map to `JsonHandler`).
*   **Save Modes (`values` vs `full`):**
    *   `config.save(mode='values')`: Saves *only* current `{setting_name: value}` pairs. Ideal for runtime. The structure is handler-dependent (e.g., simple JSON dict).
    *   `config.save(mode='full')`: Saves everything: instance version, the schema definition itself, and current values. Best for backups, transfers, or feeding external tools/UIs. The structure is handler-dependent but contains distinct version/schema/values information.
*   **Versioning & Migration:** When loading (especially `full` files), `ConfigMaster` compares versions. It prevents loading newer files, and smartly merges older files into the current schema (loading existing values, using new defaults, skipping removed settings). Type coercion between compatible types (int/float/str) is attempted if types differ.
*   **Encryption:** Provide an `encryption_key` (a Fernet key) during initialization. The storage handler encrypts data before saving and decrypts after loading. Your code interacts with plain values; the file on disk is secured (requires `cryptography`).

---

## 📖 Detailed Usage

### 1. Defining the Schema

Create a Python dictionary. The top level needs `__version__`. Other keys are your settings. Use dot notation (`.` ) in setting names for logical grouping.

```python
# Example Schema Dictionary
import typing

CONFIG_VERSION = "2.1.0"

my_app_schema: typing.Dict[str, typing.Any] = {
    "__version__": CONFIG_VERSION,

    "service.name": {
        "type": "str",
        "default": "DefaultApp",
        "help": "Identifier for the service."
    },
    "server.listen_port": {
        "type": "int",
        "default": 9090,
        "min_val": 1024,
        "max_val": 65535,
        "help": "Port number for incoming connections."
    },
    "logging.level": {
        "type": "str",
        "default": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "help": "Logging verbosity level."
    },
    "security.use_tls": {
        "type": "bool",
        "default": False,
        "help": "Enable TLS/SSL encryption."
    },
    "network.retry_delay": {
        "type": "float",
        "default": 0.5,
        "min_val": 0.0,
        "help": "Delay between retry attempts in seconds."
    },
    "web.allowed_origins": {
        "type": "list",
        "default": [], # Default to an empty list
        "help": "List of allowed CORS origins (strings)."
    },
    "database.connection_uri": {
        "type": "str",
        "default": None, # Explicitly no default connection
        "nullable": True, # Allow the setting to be None
        "help": "Database connection string (set to null if not used)."
    },
    "credentials.api_secret": { # Sensitive data
        "type": "str",
        "default": None,
        "nullable": True,
        "help": "Secret API key for external service."
    }
}
```

**Schema Definition Keys:**

*   `__version__` (str, **Required**): Semantic version (e.g., "1.0.0").
*   `type` (str, **Required**): `"str"`, `"int"`, `"float"`, `"bool"`, `"list"`.
*   `default` (any, **Required unless `nullable=True`**): Default value. Must match `type` and constraints. Omit if `nullable=True` to default to `None`.
*   `help` (str, **Required**): Description for docs/UIs.
*   `nullable` (bool, Optional): `True` allows `None` value. Default: `False`.
*   `options` (list, Optional): List of allowed values.
*   `min_val` (int/float, Optional): Minimum numeric value.
*   `max_val` (int/float, Optional): Maximum numeric value.

### 2. Initializing ConfigMaster

Pass the schema (dict or file path) and optionally the config file path and encryption key.

```python
from configmaster import ConfigMaster, generate_encryption_key
from pathlib import Path

# Assume my_app_schema is the dictionary defined above
schema_file = Path("path/to/my_schema.json") # Can load schema from JSON file
cfg_path = Path("my_settings.json") # or .bin, .enc for encrypted
# Assume enc_key is a valid Fernet key obtained via generate_encryption_key()

# Basic: Load schema dict, save/load values to cfg_path
# config1 = ConfigMaster(schema=my_app_schema, config_path=cfg_path)

# Load schema from file, save/load values
# config2 = ConfigMaster(schema=schema_file, config_path=cfg_path)

# With encryption (key must be bytes)
# config3 = ConfigMaster(schema=my_app_schema, config_path="cfg.bin", encryption_key=enc_key)

# With autosave (saves values only on change via setattr/setitem)
# config4 = ConfigMaster(schema=my_app_schema, config_path=cfg_path, autosave=True)

# No config file path (in-memory config)
# config5 = ConfigMaster(schema=my_app_schema)
# config5['server.listen_port'] = 1234 # Exists only in memory until save() called
```

ConfigMaster automatically tries to `load()` from `config_path` during initialization.

### 3. Accessing Settings and Schema

Use attribute syntax for simple names, dictionary syntax for names with dots (`.`). Use the `sc_` prefix for schema details.

```python
# Assume 'config' is an initialized ConfigMaster instance with my_app_schema

# --- Accessing Values ---
service_name = config.service_name # Attribute access for simple name
listen_port = config['server.listen_port'] # Dict access required for dotted name

print(f"Service: {service_name}, Port: {listen_port}")

# --- Accessing Schema ---
port_schema = config['sc_server.listen_port'] # Dict access for schema of dotted name
service_schema = config.sc_service_name       # Attribute access for schema of simple name

print(f"Port Help: {port_schema.help}")
print(f"Default Service Name: {service_schema.default_value}")
```

### 4. Modifying Settings

Assign values directly. Validation occurs automatically. Use dictionary syntax for names with dots.

```python
# Assume 'config' is an initialized ConfigMaster instance

config['server.listen_port'] = 8443
config['logging.level'] = 'WARNING'
config['web.allowed_origins'].append("https://myfrontend.com") # Modifying lists works directly

try:
    config['network.retry_delay'] = -1.0 # Invalid: below min_val
except ValidationError as e:
    print(f"Validation failed as expected: {e}")
    # Value remains unchanged from default or previous valid value
    print(f"Retry delay remains: {config['network.retry_delay']}")
```

### 5. Saving & Loading

Loading usually happens automatically during initialization. You can manually trigger a reload using `config.load()`. Saving requires specifying the `mode`.

```python
# Assume 'config' is an initialized ConfigMaster instance

# --- Saving ---

# Save ONLY the current values (common use case)
# Uses the path provided in __init__ if filepath not specified
# Encrypted automatically if key was provided
config.save(mode='values')
print(f"Values saved to {config.config_path}") # Access internal attr for demo

# Save values to a different file
# config.save(filepath="other_values.json", mode='values')

# Save the FULL state (version, schema definition, values)
backup_path = Path(f"config_backup_v{config.version}.json")
config.save(filepath=backup_path, mode='full')
print(f"Full state saved to {backup_path}")


# --- Loading (Manual Trigger) ---
# Useful for reloading after external changes or testing

try:
    print("Attempting manual reload...")
    config.load() # Reloads from the path specified in __init__
    # config.load(filepath="specific_config_to_load.json") # Load specific file
    print("Configuration reloaded successfully.")
except FileNotFoundError:
    print("Config file not found for manual load.")
except Exception as e:
    print(f"Error during manual load: {e}")

```

### 6. Versioning & Migration

Versioning is handled automatically during `load()` based on the `__version__` key in your schema and the `version` field potentially stored in the configuration file (if saved with `mode='full'`). See Core Concepts for details.

**Example Simulation:** Loading a V1.0.0 file into a V1.1.0 instance.

```python
# Assume current ConfigMaster instance 'config_v110' uses my_app_schema (V1.1.0)
# Assume 'older_file_path' points to a simulated V1.0.0 'full' config file:
# Content of older_file_path (simplified):
# {
#   "version": "1.0.0",
#   "schema": { "server.listen_port": {...}, "removed_setting": {...}, ... },
#   "values": { "server.listen_port": 7000, "removed_setting": "old", ... }
# }

try:
    print("\nLoading older config into V1.1.0 instance...")
    # Initialize NEW instance with CURRENT schema, load OLD file path
    config_migrated = ConfigMaster(schema=my_app_schema, config_path=older_file_path)
    # Load happens in __init__, migration logic applied

    print(f"Loaded file version: {config_migrated.loaded_file_version}") # Output: 1.0.0
    print(f"Instance version: {config_migrated.version}")         # Output: 1.1.0

    # Value from old file is loaded (key exists in V1.1.0)
    print(f"Port loaded from old: {config_migrated['server.listen_port']}") # Output: 7000

    # New setting in V1.1.0 gets its default value
    print(f"Timeout (new in V1.1.0): {config_migrated['network.timeout_seconds']}") # Output: 30.0 (V1.1.0 default)

    # 'removed_setting' from old file is skipped (warning logged during load)

except SchemaError as e:
    print(f"Schema error (e.g., file version too new): {e}")
except Exception as e:
    print(f"Other loading error: {e}")
```

### 7. Encryption

Provide a valid `encryption_key` (bytes) during `ConfigMaster` initialization.

```python
from configmaster import ConfigMaster, generate_encryption_key
from pathlib import Path

schema_dict = {"__version__": "1.0", "service.api_secret": {"type": "str", "nullable": True, "help":"Secret Value"}}
config_path = Path("secrets.bin") # Use .bin or .enc extension convention
key_file = Path("secret.key")

# 1. Generate and store key securely (only once per environment/deployment)
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
    # Load will fail if file doesn't exist, defaults used

    # 3. Set sensitive data
    secure_config['service.api_secret'] = "my-super-secret-value"
    print("Set sensitive value.")

    # 4. Save (automatically encrypted by the handler)
    secure_config.save(mode='values') # or 'full'
    print(f"Encrypted configuration saved to {config_path}.")
    print(f"File content preview (should be ciphertext): {config_path.read_bytes()[:60]}...")

    # 5. Reload (automatically decrypted by the handler)
    # Create a new instance or call secure_config.load()
    secure_config_reloaded = ConfigMaster(
        schema=schema_dict,
        config_path=config_path,
        encryption_key=secret_key
    )
    print(f"Reloaded secret: {secure_config_reloaded['service.api_secret']}")
    assert secure_config_reloaded['service.api_secret'] == "my-super-secret-value"

except ImportError:
    print("Encryption requires 'cryptography'. Please install.")
except Exception as e:
    print(f"Encryption example error: {e}")
finally:
    # Clean up example files
    if config_path.exists(): config_path.unlink()
    if key_file.exists(): key_file.unlink()

```

### 8. Handling Nested Configurations (Naming Convention)

ConfigMaster currently supports logical nesting through a **dot notation convention** in setting names. True nested schema validation is planned for a future release.

**Define using dot notation:**

```python
schema = {
    "__version__": "1.0",
    "database.host": {
        "type": "str",
        "default": "localhost",
        "help": "Database server hostname or IP address."
    },
    "database.port": {
        "type": "int",
        "default": 5432,
        "min_val": 1,
        "max_val": 65535,
        "help": "Database server port."
    },
    "database.credentials.user": { # Deeper nesting
        "type": "str",
        "default": "app_user",
        "help": "Database username."
    },
    "database.credentials.password": { # Sensitive
        "type": "str",
        "nullable": True,
        "default": None,
        "help": "Database password (encrypted if key provided)."
    },
    "server.timeout": {
        "type": "int",
        "default": 30,
        "help": "Server request timeout."
    }
}
config = ConfigMaster(schema=schema)

# Access requires dictionary style for names with dots
db_host = config['database.host']
db_user = config['database.credentials.user']

# Modify using dictionary style
config['database.port'] = 5433
config['database.credentials.password'] = "secure_password"

print(f"DB Host: {db_host}, User: {db_user}, Port: {config['database.port']}")
```

**Limitation:** Validation currently applies only to the final value (e.g., `"localhost"`, `5433`). The structure (`database`, `credentials`) is purely conventional based on the name.

### 9. Import/Export

*   **Exporting Current State (Schema + Values):** Get a snapshot for UIs or APIs.

    ```python
    # config is an initialized ConfigMaster instance
    current_state = config.export_schema_with_values()

    # 'current_state' dictionary structure:
    # {
    #   "version": "1.1.0", # Instance version
    #   "schema": { ... }, # Instance schema definition (without version key)
    #   "settings": {
    #     "setting.name": {
    #       "schema": { ... }, # Specific setting schema dict
    #       "value": ...       # Current value for this setting
    #     },
    #     # Includes entries for all settings defined in instance schema
    #     "database.host": { ... },
    #     ...
    #   }
    # }

    import json
    # print(json.dumps(current_state, indent=2)) # Print the full structure
    print(f"Exported version: {current_state.get('version')}")
    print(f"Number of settings exported: {len(current_state.get('settings', {}))}")
    ```

*   **Importing Values from Dictionary:** Update settings from a dictionary (e.g., received from an API or UI). Only *values* are imported; version/schema info in the dict is ignored.

    ```python
    update_data = {
        "server.listen_port": 8888, # Assuming this key exists in schema
        "logging.level": "WARNING",
        "database.credentials.user": "importer_user",
        "unknown_setting": "ignore_me" # Will be ignored or raise error
    }

    try:
        # Update config, ignore keys not in schema, validation occurs
        config.import_config(update_data, ignore_unknown=True)
        print("Import successful.")
        print(f"Port after import: {config['server.listen_port']}")
        print(f"DB User after import: {config['database.credentials.user']}")
    except Exception as e:
        print(f"Import failed: {e}")
    ```

---

## 💡 Use Cases

*   **Reliable App Settings:** Manage ports, paths, flags, levels.
*   **Secure Secret Storage:** Encrypt API keys, DB credentials, tokens. Build simple secret vaults.
*   **UI Configuration:** Define and manage themes, layouts, user prefs.
*   **CLI Tool Settings:** Provide robust configuration for your tools.
*   **Multi-Environment Configs:** Use separate, potentially encrypted files (dev, staging, prod) with the same schema.
*   **Dynamic Config UIs:** Feed `export_schema_with_values()` to PyQt/Web UIs for graphical editing with schema-based validation hints.

---

## 🔧 Advanced Topics

*   **Custom Storage Handlers:** Need different storage? Subclass `configmaster.handlers.StorageHandler`, implement `load`/`save` (including encryption handling if desired), and register the extension in `configmaster.handlers.HANDLER_MAP`.
*   **Nested Schemas (Future):** Planned support for defining schemas within schemas for true hierarchical validation and potentially attribute-style access (`config.database.port`).

---

## 🤝 Contributing

Contributions are highly welcome! We strive for clean, reliable, well-tested code.

1.  **Fork & Branch:** Fork the repo and create a new branch for your work.
2.  **Code Quality:**
    *   Adhere to **PEP 8**.
    *   Format code using **Black**.
    *   Use **Ruff** for linting (see `pyproject.toml` for config).
    *   Add **Type Hints** (`typing`) to all functions/methods.
    *   Write clear **Docstrings** (Google style preferred).
3.  **Testing:** Add comprehensive **unit tests** using `pytest` in the `tests/` directory. Aim for high coverage.
4.  **Local Checks:** Run `black .`, `ruff check .`, `mypy configmaster`, and `pytest` before committing.
5.  **Commit & PR:** Use descriptive commit messages. Open a Pull Request against the `main` branch. Ensure CI checks pass.

*(A full CONTRIBUTING.md with detailed steps is planned).*

---

## 📜 License

ConfigMaster is distributed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by ParisNeo with the help of Gemini 2.5
</p>