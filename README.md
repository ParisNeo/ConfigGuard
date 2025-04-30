# ConfigGuard

[![PyPI version](https://img.shields.io/pypi/v/configguard.svg)](https://pypi.org/project/configguard/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/configguard.svg)](https://pypi.org/project/configguard/)
[![PyPI license](https://img.shields.io/pypi/l/configguard.svg)](https://github.com/ParisNeo/ConfigGuard/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/configguard)](https://pepy.tech/project/configguard)
[![Documentation Status](https://img.shields.io/badge/docs-latest-blue.svg)](https://parisneo.github.io/ConfigGuard/)
<!-- [![Build Status](https://github.com/ParisNeo/ConfigGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/ParisNeo/ConfigGuard/actions/workflows/ci.yml) Placeholder -->
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

**Stop fighting inconsistent, error-prone, and insecure configuration files!** 🚀

**ConfigGuard** elevates your Python configuration management from fragile text files and basic dictionaries to a powerful, **schema-driven fortress**. Gain unparalleled control with:

*   Strict **Type Safety** & **Validation Rules**
*   Built-in **Encryption** for your secrets
*   Seamless **Versioning** & **Migration**
*   Support for **Multiple Storage Formats** (JSON now, more coming!)
*   Intuitive **Nested Configuration** handling via sections

**Why settle?** Ensure your app settings are always valid, secure, and effortlessly maintainable. Prevent runtime surprises, simplify updates, and focus on building great features, not debugging config errors.

**Adopt ConfigGuard and configure with confidence!**

---

## ✨ Key Features

*   📝 **Schema-Driven:** Define your configuration structure with types, defaults, help text, and validation rules (`min_val`, `max_val`, `options`, `nullable`). Includes schema versioning!
*   <0xF0><0x9F><0xA7><0xB1> **Nested Configuration:** Organize complex settings using **sections** directly within your schema (`"type": "section"`). Access nested settings intuitively (e.g., `config.database.port`).
*   🔒 **Built-in Encryption:** Secure sensitive configuration values transparently using Fernet encryption (requires `cryptography`). Handled automatically by storage backends.
*   💾 **Multiple Backends:** Store configurations in various formats (JSON included, YAML/TOML/SQLite planned) through an extensible handler system. JSON handles nesting naturally.
*   🔄 **Versioning & Migration:** Embed versions in your schema. ConfigGuard automatically handles loading older configuration versions and migrating settings gracefully, **recursively through sections**.
*   <0xF0><0x9F><0x97><0x84>️ **Flexible Save Modes:** Choose to save only the configuration *values* (default) or the *full state* including version, schema, and values. Nested structures are preserved.
*   <0xF0><0x9F><0xA7><0xB1> **Supported Types:** Define settings as `str`, `int`, `float`, `bool`, or `list`. *(Note: List element types are not currently validated by the schema)*.
*   🐍 **Intuitive Access:** Access configuration values naturally using attribute (`config.section.setting`) or dictionary (`config['section']['setting']`) syntax. Access schema details easily (`config.sc_section.sc_setting`).
*   ✔️ **Automatic Validation:** Values are automatically validated against the schema upon setting or loading, preventing invalid states, even for nested settings.
*   📤 **Easy Export/Import:** Export the current schema and values (`export_schema_with_values()`), including nested structures, for UIs or APIs. Import values from nested dictionaries (`import_config()`).
*   🧩 **Extensible:** Designed with a clear handler interface to easily add support for new storage backends.

---

## 🤔 Why Choose ConfigGuard?

*   **Eliminate Config Errors:** Catch issues at definition or load time, not during critical runtime operations.
*   **Secure Your Secrets:** Easily encrypt API keys, passwords, and tokens without complex setup.
*   **Future-Proof Your App:** Handle config changes between versions smoothly with built-in migration, even with structural changes.
*   **Improve Code Clarity:** Self-documenting schemas and clear section structures make settings understandable and maintainable.
*   **Manage Complexity:** Tame complex configurations by organizing them into logical, nested sections.
*   **Increase Productivity:** Stop writing boilerplate config parsing/validation code.
*   **Storage Freedom:** Use JSON today, YAML/TOML/DB tomorrow, without rewriting your core logic.

---

## 🚀 Installation

```bash
pip install configguard
```

For **encryption** features:

```bash
pip install configguard[encryption]
# or separately: pip install cryptography
```

*(Support for other backends like YAML/TOML will require optional installs in the future).*

---

## ⚡ Quick Start

```python
from configguard import ConfigGuard, ValidationError, generate_encryption_key
from pathlib import Path
import typing # Required for type hinting the schema dict

# 1. Define your schema (with version and nested sections!)
CONFIG_VERSION = "1.0.0"
my_schema: typing.Dict[str, typing.Any] = { # Add type hint for clarity
    "__version__": CONFIG_VERSION,
    "server": {
        "type": "section",
        "help": "Server settings",
        "schema": {
            "host": { "type": "str", "default": "127.0.0.1", "help": "Listen host" },
            "port": { "type": "int", "default": 8080, "min_val": 1024, "help": "Listen port" }
        }
    },
    "database": {
        "type": "section",
        "help": "Database connection",
        "schema": {
            "uri": { "type": "str", "nullable": True, "default": None, "help": "Connection URI" },
            "timeout": { "type": "int", "default": 5, "help": "Connection timeout (sec)" }
        }
    },
    "api_key": { # Top-level setting
        "type": "str",
        "nullable": True,
        "default": None,
        "help": "Optional global API Key (sensitive)."
    }
}

# 2. Setup paths and optional encryption key
config_file = Path("app_settings.bin") # Use .bin for encrypted
# key = generate_encryption_key() # Generate once and store securely!
# print(f"Generated Key: {key.decode()}")
# Example key (DO NOT use this in production, generate your own!)
key = b'p4SDfnaAZFq9N5EhrNDfGVOQ1C6pShR1w7TKVmqw0rI='

# 3. Initialize ConfigGuard (with encryption)
try:
    config = ConfigGuard(
        schema=my_schema,
        config_path=config_file,
        encryption_key=key
    )
except ImportError:
    print("Encryption requires 'cryptography'. Install with: pip install configguard[encryption]")
    # Initialize without encryption as a fallback for the example
    config = ConfigGuard(schema=my_schema, config_path=Path("app_settings.json"))


# 4. Access values (attribute or item access for sections/settings)
print(f"Server Host: {config.server.host}")
print(f"Database Timeout: {config['database']['timeout']}")
print(f"API Key: {config.api_key}") # Top-level access

# 5. Access schema details
print(f"Port Help: {config.server.sc_port.help}")
print(f"Is DB URI nullable? {config['database']['sc_uri'].nullable}")

# 6. Modify values (validation happens automatically)
try:
    config.server.port = 9000
    config['database']['uri'] = "postgresql://user:pass@host/db"
    config.api_key = "my-super-secret"
    # config.server.port = 80 # This would raise ValidationError
except ValidationError as e:
    print(f"Error setting value: {e}")

print(f"New Port: {config.server.port}")
print(f"DB URI set: {'Yes' if config.database.uri else 'No'}")

# 7. Save configuration values (encrypted if key was provided)
# Use mode='values' for typical runtime saving (preserves nesting)
config.save(mode='values')
print(f"Settings saved to {config.config_path}") # Access internal attr for demo

# Load on next init is automatic! If the file exists, ConfigGuard loads it.
# Example:
# config_reloaded = ConfigGuard(schema=my_schema, config_path=config_file, encryption_key=key)
# print(f"Reloaded Port: {config_reloaded.server.port}") # Output: 9000
```

---

## 📚 Core Concepts

*   **Schema (`__version__`, Settings Definitions, Sections):** The blueprint for your configuration. A Python dictionary defining the version, settings names, types (`str`, `int`, `float`, `bool`, `list`), defaults, validation rules (`nullable`, `options`, `min_val`, `max_val`), and help text. Use `"type": "section"` with a nested `"schema": {...}` dictionary to define hierarchical structures. The top-level `__version__` key is mandatory for version control of the entire configuration.
*   **ConfigGuard Object:** Your main interface. Holds the schema and current values. Access settings and sections via attribute (`config.section.setting`) or dictionary (`config['section']['setting']`) syntax. Access schema details using the `sc_` prefix (`config.sc_section.sc_setting` or `config['section']['sc_setting']`).
*   **ConfigSection Object:** An internal object representing a defined section. It provides the same attribute/dictionary access for its contained settings and subsections.
*   **Storage Handlers:** The engine parts handling specific file formats (JSON, future YAML/TOML/DB) and transparent encryption/decryption based on the key you provide to `ConfigGuard`. Chosen based on file extension (e.g., `.json`, `.bin`, `.enc` often map to `JsonHandler`). JSON handlers naturally support nested structures.
*   **Save Modes (`values` vs `full`):**
    *   `config.save(mode='values')`: Saves *only* current configuration values. Nested structures are preserved according to the handler's format (e.g., nested JSON objects). Ideal for runtime.
    *   `config.save(mode='full')`: Saves everything: instance version, the full schema definition (including section structures), and current values (including nesting). Best for backups, transfers, or feeding external tools/UIs.
*   **Versioning & Migration:** When loading (especially `full` files), `ConfigGuard` compares versions. It prevents loading newer files, and smartly merges older files into the current schema **recursively through sections** (loading existing values, using new defaults, skipping removed settings/sections). Type coercion between compatible types (int/float/str) is attempted if types differ.
*   **Encryption:** Provide an `encryption_key` (a Fernet key) during initialization. The storage handler encrypts data before saving and decrypts after loading. Your code interacts with plain values; the file on disk is secured (requires `cryptography`). Works transparently with nested structures.

---

## 📖 Detailed Usage

### 1. Defining the Schema (with Sections)

Create a Python dictionary. The top level needs `__version__`. Other keys are your settings or sections. Define sections using `"type": "section"` and a nested `"schema"` key.

```python
# Example Schema Dictionary with Sections
import typing

CONFIG_VERSION = "2.1.0"

my_app_schema: typing.Dict[str, typing.Any] = {
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
                "default": 9090,
                "min_val": 1024,
                "max_val": 65535,
                "help": "Port number for incoming connections."
            },
            "tls": { # Nested section within 'server'
                "type": "section",
                "help": "TLS/SSL settings.",
                "schema": {
                    "enabled": { "type": "bool", "default": False, "help": "Enable TLS." },
                    "cert_path": { "type": "str", "nullable": True, "default": None, "help": "Path to certificate file." }
                }
            }
        }
    },
    "logging": {
        "type": "section",
        "help": "Application logging settings.",
        "schema": {
            "level": {
                "type": "str",
                "default": "INFO",
                "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "help": "Logging verbosity level."
            },
            "file_path": {
                "type": "str",
                "default": None,
                "nullable": True,
                "help": "Path to log file (if enabled)."
            },
        }
    },
    "credentials": { # Section for sensitive data
        "type": "section",
        "help": "External service credentials.",
        "schema": {
             "api_secret": {
                "type": "str",
                "default": None,
                "nullable": True,
                "help": "Secret API key (will be encrypted)."
            }
        }
    },
    "global_timeout": { # Top-level setting
        "type": "float",
        "default": 60.0,
        "min_val": 0.0,
        "help": "Global operation timeout in seconds."
    }
}
```

**Schema Definition Keys:**

*   `__version__` (str, **Required**): Semantic version (e.g., "1.0.0"). Applies to the entire schema.
*   For **Settings:**
    *   `type` (str, **Required**): `"str"`, `"int"`, `"float"`, `"bool"`, `"list"`.
    *   `default` (any, **Required unless `nullable=True`**): Default value. Must match `type` and constraints. Omit if `nullable=True` to default to `None`.
    *   `help` (str, **Required**): Description for docs/UIs.
    *   `nullable` (bool, Optional): `True` allows `None` value. Default: `False`.
    *   `options` (list, Optional): List of allowed values.
    *   `min_val` (int/float, Optional): Minimum numeric value.
    *   `max_val` (int/float, Optional): Maximum numeric value.
*   For **Sections:**
    *   `type` (str, **Required**): Must be `"section"`.
    *   `schema` (dict, **Required**): A nested dictionary defining the settings and subsections within this section.
    *   `help` (str, Optional): Description for the section.

### 2. Initializing ConfigGuard

Pass the schema (dict or file path) and optionally the config file path and encryption key.

```python
from configguard import ConfigGuard, generate_encryption_key
from pathlib import Path

# Assume my_app_schema is the nested dictionary defined above
schema_file = Path("path/to/my_schema.json") # Can load schema from JSON file
cfg_path = Path("my_settings.json") # or .bin, .enc for encrypted
# Assume enc_key is a valid Fernet key obtained via generate_encryption_key()

# Basic: Load schema dict, save/load values to cfg_path
# config1 = ConfigGuard(schema=my_app_schema, config_path=cfg_path)

# Load schema from file, save/load values
# config2 = ConfigGuard(schema=schema_file, config_path=cfg_path)

# With encryption (key must be bytes)
# config3 = ConfigGuard(schema=my_app_schema, config_path="cfg.bin", encryption_key=enc_key)

# With autosave (saves values only on change via setattr/setitem, including nested)
# config4 = ConfigGuard(schema=my_app_schema, config_path=cfg_path, autosave=True)

# No config file path (in-memory config)
# config5 = ConfigGuard(schema=my_app_schema)
# config5.server.port = 1234 # Exists only in memory until save() called
```

ConfigGuard automatically tries to `load()` from `config_path` during initialization.

### 3. Accessing Settings and Schema (Nested)

Use attribute or dictionary syntax to traverse sections. Use the `sc_` prefix for schema details.

```python
# Assume 'config' is an initialized ConfigGuard instance with my_app_schema

# --- Accessing Values ---
server_host = config.server.host
server_port = config['server']['port']
tls_enabled = config.server.tls.enabled # Deeper nesting
log_level = config['logging']['level']
global_to = config.global_timeout # Top-level

print(f"Host: {server_host}, Port: {server_port}, TLS: {tls_enabled}")

# --- Accessing Schema ---
port_schema = config.server.sc_port # Schema of setting in section
tls_schema = config.server.sc_tls # Schema of nested section
tls_enabled_schema = config.server.tls.sc_enabled # Schema of setting in nested section
log_level_options = config['logging']['sc_level'].options
global_to_help = config.sc_global_timeout.help # Schema of top-level

print(f"Port Help: {port_schema.help}")
print(f"TLS Section Schema Keys: {list(tls_schema.keys())}")
print(f"Log Level Options: {log_level_options}")
```

### 4. Modifying Settings (Nested)

Assign values directly using attribute or dictionary syntax. Validation occurs automatically.

```python
# Assume 'config' is an initialized ConfigGuard instance

config.server.port = 8443
config['logging']['level'] = 'WARNING'
config.server.tls.enabled = True
config.server.tls.cert_path = "/etc/ssl/certs/mycert.pem"
config.credentials.api_secret = "new-encrypted-secret"

try:
    config.server.port = 100 # Invalid: below min_val
except ValidationError as e:
    print(f"Validation failed as expected: {e}")
    # Value remains unchanged from default or previous valid value
    print(f"Server port remains: {config.server.port}")
```

### 5. Saving & Loading (Nested)

Loading usually happens automatically during initialization. Manual `load()` and `save()` work as before, handling nested structures correctly.

```python
# Assume 'config' is an initialized ConfigGuard instance

# --- Saving ---

# Save ONLY the current values (common use case, preserves nesting)
config.save(mode='values')
print(f"Values saved to {config.config_path}")

# Save the FULL state (version, nested schema definition, nested values)
backup_path = Path(f"config_backup_v{config.version}.json")
config.save(filepath=backup_path, mode='full')
print(f"Full state saved to {backup_path}")


# --- Loading (Manual Trigger) ---
try:
    print("Attempting manual reload...")
    config.load() # Reloads from the path specified in __init__
    print("Configuration reloaded successfully.")
    print(f"Reloaded TLS enabled status: {config.server.tls.enabled}")
except FileNotFoundError:
    print("Config file not found for manual load.")
except Exception as e:
    print(f"Error during manual load: {e}")

```

### 6. Versioning & Migration (Nested)

Versioning is handled automatically during `load()` based on the top-level `__version__`. Migration logic applies **recursively** through sections.

*   If a section exists in the old file but not the new schema, it's skipped (warning logged).
*   If a section is new in the schema, its settings get default values.
*   If a setting moves between sections, it will likely be treated as removed from the old location and added (with default) in the new one during migration (unless custom migration logic is added in the future).

See the `examples/basic_usage.py` for a simulation.

### 7. Encryption (Nested)

Encryption works transparently for all settings, regardless of nesting level, if an `encryption_key` is provided during initialization. The structure is preserved, but the values within the saved file are encrypted.

```python
# Assume enc_key is a valid Fernet key
# Assume schema includes sensitive fields like config.credentials.api_secret

secure_config = ConfigGuard(schema=my_app_schema, config_path="secure_cfg.bin", encryption_key=enc_key)

secure_config.credentials.api_secret = "very_secret_value"
secure_config.server.host = "secure.example.com" # Non-sensitive also saved

secure_config.save(mode='values') # Saves nested structure, encrypts values

# Reloading decrypts automatically
reloaded_secure = ConfigGuard(schema=my_app_schema, config_path="secure_cfg.bin", encryption_key=enc_key)
print(f"Reloaded secret: {reloaded_secure.credentials.api_secret}") # Output: very_secret_value
print(f"Reloaded host: {reloaded_secure.server.host}") # Output: secure.example.com
```

### 8. Handling Nested Configurations

ConfigGuard supports true hierarchical configuration through **sections**. Define sections in your schema using `"type": "section"` and a nested `"schema"` dictionary.

**Schema Definition:**

```python
schema = {
    "__version__": "1.0",
    "database": {
        "type": "section",
        "help": "Primary Database",
        "schema": {
            "host": { "type": "str", "default": "localhost" },
            "port": { "type": "int", "default": 5432 },
            "credentials": { # Nested section
                "type": "section",
                "schema": {
                    "user": { "type": "str", "default": "app_user" },
                    "password": { "type": "str", "nullable": True } # Sensitive
                }
            }
        }
    },
    "cache": {
        "type": "section",
        "help": "Caching Layer",
        "schema": {
            "host": { "type": "str", "default": "127.0.0.1" },
            "port": { "type": "int", "default": 6379 }
        }
    }
}
```

**Access and Modification:**

```python
config = ConfigGuard(schema=schema)

# Access
db_host = config.database.host
db_user = config.database.credentials.user
cache_port = config['cache']['port']

# Modify
config.database.port = 5433
config.database.credentials.password = "secure_password"
config['cache']['host'] = "redis.internal"

print(f"DB Host: {db_host}, User: {db_user}, Port: {config.database.port}")
print(f"Cache Host: {config.cache.host}, Port: {cache_port}")
```

Validation, saving, loading, migration, and encryption all work recursively through these defined sections.

### 9. Import/Export (Nested)

*   **Exporting Current State:** `export_schema_with_values()` returns a dictionary where the `value` for a section key is itself a nested dictionary representing the values within that section.

    ```python
    # config is an initialized ConfigGuard instance with nested schema
    current_state = config.export_schema_with_values()

    # 'current_state["settings"]' structure example:
    # {
    #   "database": {
    #     "schema": { ... database section schema ... },
    #     "value": { # <-- Nested dictionary of values
    #       "host": "localhost",
    #       "port": 5433,
    #       "credentials": { # <-- Deeper nesting of values
    #         "user": "app_user",
    #         "password": "secure_password"
    #       }
    #     }
    #   },
    #   "cache": {
    #      "schema": { ... cache section schema ... },
    #      "value": {
    #          "host": "redis.internal",
    #          "port": 6379
    #      }
    #   },
    #   "global_timeout": { # Top-level setting
    #       "schema": { ... },
    #       "value": 60.0
    #   }
    # }

    import json
    # print(json.dumps(current_state, indent=2))
    print(f"Exported DB host: {current_state['settings']['database']['value']['host']}")
    ```

*   **Importing Values from Dictionary:** `import_config()` accepts a nested dictionary matching the section structure. Validation and the `ignore_unknown` flag apply recursively.

    ```python
    update_data = {
        "server": { # Assuming 'server' section exists in schema
            "port": 8888,
            "tls": { "enabled": True }
        },
        "logging": {
            "level": "ERROR",
            "unknown_log_setting": "abc" # Ignored if ignore_unknown=True
        },
        "global_timeout": 120.0,
        "new_unknwon_section": {} # Ignored if ignore_unknown=True
    }

    try:
        # Update config, ignore keys/sections not in schema, validation occurs
        config.import_config(update_data, ignore_unknown=True)
        print("Import successful.")
        print(f"Port after import: {config.server.port}")
        print(f"TLS after import: {config.server.tls.enabled}")
    except SettingNotFoundError as e:
         print(f"Import failed (ignore_unknown=False): {e}")
    except Exception as e:
        print(f"Import failed: {e}")
    ```

---

## 💡 Use Cases

*   **Reliable App Settings:** Manage server ports, paths, flags, logging levels, organized by component (server, database, logging).
*   **Secure Secret Storage:** Encrypt API keys, DB credentials, tokens within dedicated sections (e.g., `credentials.database`, `credentials.service_x`).
*   **UI Configuration:** Define and manage themes, layouts, user prefs, potentially grouped by UI area.
*   **Complex Service Config:** Manage settings for microservices with distinct configurations for databases, caches, external APIs, etc.
*   **Multi-Environment Configs:** Use separate, potentially encrypted files (dev, staging, prod) with the same nested schema.
*   **Dynamic Config UIs:** Feed `export_schema_with_values()` to generate forms with sections and validation hints.

---

## 🔧 Advanced Topics

*   **Custom Storage Handlers:** Need different storage? Subclass `configguard.handlers.StorageHandler`, implement `load`/`save` (including encryption handling and potentially custom nesting logic if not JSON-like), and register the extension in `configguard.handlers.HANDLER_MAP`.

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
3.  **Testing:** Add comprehensive **unit tests** using `pytest` in the `tests/` directory. Aim for high coverage, especially for new features or bug fixes.
4.  **Local Checks:** Run `black .`, `ruff check .`, `mypy configguard`, and `pytest` before committing.
5.  **Commit & PR:** Use descriptive commit messages. Open a Pull Request against the `main` branch. Ensure CI checks pass.

*(A full CONTRIBUTING.md with detailed steps is planned).*

---

## 📜 License

ConfigGuard is distributed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by ParisNeo with the help of Gemini 2.5
</p>