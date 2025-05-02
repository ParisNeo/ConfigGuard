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

**ConfigGuard** transforms your Python application's configuration management from a potential source of bugs and security risks into a robust, reliable, and developer-friendly system. Moving beyond simple dictionaries or basic file parsing, ConfigGuard introduces a **schema-driven fortress** for your settings, offering unparalleled control and safety.

Leverage a comprehensive suite of features designed for modern applications:

*   Define strict **Type Safety** and complex **Validation Rules** (`min`, `max`, `options`, `nullable`).
*   Protect sensitive data effortlessly with built-in, handler-transparent **Encryption**.
*   Manage configuration changes across application updates with seamless **Versioning** (optionally override instance version) and automated **Migration**.
*   Choose your preferred **Storage Format** (JSON, YAML, TOML, SQLite included) without altering your core logic.
*   Organize complex configurations intuitively using **Nested Sections**.
*   Accommodate unpredictable structures with flexible **Dynamic Sections**.

**Why waste time debugging subtle configuration typos or managing insecure secrets manually?** ConfigGuard catches errors early, simplifies maintenance, and secures your sensitive data, allowing you to focus on building great features.

**Adopt ConfigGuard and configure with confidence!**

---

## ✨ Key Features

*   📝 **Schema-Driven:** Define your configuration's expected structure, types, defaults, and validation rules within a Python dictionary or a JSON file. This acts as the single source of truth, ensuring consistency and enabling static analysis benefits. Schema definitions should ideally include a `__version__` key for robust version tracking, but the instance version can also be set explicitly.
*   <0xF0><0x9F><0xA7><0xB1> **Nested Configuration:** Structure complex settings logically using **sections**, defined directly within your schema (`"type": "section"`). Access nested settings intuitively through standard attribute or dictionary notation (e.g., `config.database.connection.pool_size`, `config['server']['ssl']['enabled']`), promoting code readability and maintainability.
*   <0xF0><0x9F><0x94><0x91> **Dynamic Sections:** For scenarios requiring flexibility (like plugin settings or user-defined mappings), define sections with an empty schema (`"schema": {}`). These sections behave like standard Python dictionaries, allowing the addition, modification, and deletion of arbitrary key-value pairs at runtime, while still benefiting from ConfigGuard's saving, loading, and encryption mechanisms.
*   🔒 **Built-in Encryption:** Secure sensitive configuration values (API keys, passwords, tokens) transparently using Fernet symmetric encryption (requires the `cryptography` library). Encryption is handled automatically by the storage backend during save/load operations, meaning your application code always interacts with plain, decrypted values.
*   💾 **Multiple Backends:** Persist your configurations in various formats through an extensible handler system. ConfigGuard automatically detects the desired format based on the file extension (`.json`, `.yaml`, `.yml`, `.toml`, `.db`, `.sqlite`, `.sqlite3`). Default handlers are provided for JSON, YAML, TOML, and SQLite.
*   🔄 **Versioning & Migration:** Embed a version string (e.g., `"1.2.0"`) in your schema's `__version__` key *or* provide it via the `instance_version` parameter during initialization. When loading configuration files, ConfigGuard compares the file's version with the instance's version. It prevents loading configurations newer than the application expects and gracefully handles older versions by merging existing values, applying new defaults, and skipping settings/sections no longer present in the current schema. This migration logic operates **recursively through nested sections**.
*   <0xF0><0x9F><0x97><0x84>️ **Flexible Save Modes:** Control the granularity of saved data:
    *   `mode='values'` (default): Saves only the current configuration values. Ideal for runtime updates, preserving the structure (including nesting and dynamic content) according to the chosen handler's capabilities.
    *   `mode='full'`: Saves the complete state: the current **instance version**, the full schema *definition* (including nested structures and empty schemas for dynamic sections), and the current values. Best for backups, transferring configurations between environments, or providing comprehensive state to external tools or UIs.
*   <0xF0><0x9F><0xA7><0xB1> **Supported Types:** Define standard settings with common Python types: `str`, `int`, `float`, `bool`, or `list`. *(Note: Validation of individual element types within lists is not currently implemented)*. Dynamic sections can store any value that is serializable by the chosen backend handler (typically JSON-serializable types).
*   🐍 **Intuitive Access:** Interact with your configuration naturally. Access values using attribute (`config.section.setting`, `config.dynamic_section.key`) or dictionary (`config['section']['setting']`, `config['dynamic_section']['key']`) syntax. Retrieve schema details for *defined* settings using the `sc_` prefix (`config.sc_section.sc_setting`).
*   ✔️ **Automatic Validation:** ConfigGuard automatically validates values against the schema rules (type, `nullable`, `options`, `min_val`, `max_val`) whenever a standard setting is modified or when data is loaded. This prevents invalid data from entering your configuration state. **Values added to dynamic sections bypass this schema validation.**
*   📤 **Easy Export/Import:**
    *   `export_schema_with_values()`: Get a snapshot of the entire configuration state (schema definition + current values, including dynamic content) as a dictionary, suitable for populating UIs, sending over APIs, or debugging. The exported `version` reflects the current *instance* version.
    *   `import_config(data, ignore_unknown=True)`: Update the configuration *values* from a (potentially nested) dictionary. This merges data into the existing structure, applying validation for standard settings and adding/updating keys in dynamic sections. The `ignore_unknown` flag controls whether unexpected keys cause errors.
*   🧩 **Extensible:** Built with a clear `StorageHandler` interface, allowing developers to easily implement and register support for additional storage backends (e.g., databases, cloud services, environment variables).

---

## 🤔 Why Choose ConfigGuard?

ConfigGuard addresses common pain points in configuration management:

*   **Eliminate Runtime Config Errors:** Instead of discovering a typo in a port number or an invalid logging level only when your application crashes, ConfigGuard catches these errors early – either when the schema is defined or when data is loaded/set – thanks to its strict validation against your predefined rules.
*   **Secure Your Secrets with Ease:** Stop storing sensitive API keys, database passwords, or tokens in plain text files or insecure environment variables. ConfigGuard's integrated encryption provides a simple, transparent mechanism to protect this data at rest, requiring only a single encryption key and the `cryptography` library.
*   **Future-Proof Your Application:** As your application evolves, so will its configuration needs. ConfigGuard's versioning system (using schema `__version__` or explicit `instance_version`) allows you to update your schema confidently. When loading older config files, it automatically attempts to migrate the data, preserving user settings where possible and applying new defaults, significantly reducing the friction of application updates.
*   **Improve Code Clarity and Maintainability:** Schemas act as self-documentation for your configuration settings. The explicit definition of types, defaults, validation rules, and help strings makes it much easier for developers (including your future self) to understand what each setting does and how to configure it correctly. Nested sections further enhance organization.
*   **Manage Complexity Effectively:** Modern applications often have numerous configuration options. ConfigGuard allows you to tame this complexity by organizing settings into logical, hierarchical sections (both predefined and dynamic), making the overall configuration easier to navigate and manage.
*   **Increase Developer Productivity:** Eliminate the need to write repetitive, error-prone boilerplate code for parsing different config file formats, validating data types, checking ranges, handling defaults for missing values, and managing encryption. ConfigGuard handles these common tasks robustly.
*   **Gain Storage Freedom:** Start with JSON for simplicity, move to YAML for readability, use TOML if preferred, or leverage SQLite for transactional saves – all without changing how your application code interacts with the configuration object. The backend is abstracted away by the handler system.

---

## 🚀 Installation

ConfigGuard requires Python 3.8 or later.

**Base Installation (includes JSON and SQLite support):**

```bash
pip install configguard
```

**With Optional Features (Extras):**

ConfigGuard uses "extras" to manage dependencies for optional features like encryption and specific file format handlers.

*   **Encryption:** Requires the `cryptography` library.
    ```bash
    pip install configguard[encryption]
    ```

*   **YAML Support:** Requires the `PyYAML` library.
    ```bash
    pip install configguard[yaml]
    ```

*   **TOML Support:** Requires the `toml` library.
    ```bash
    pip install configguard[toml]
    ```

*   *(SQLite support uses Python's built-in `sqlite3` and needs no extra pip install).*

**Installing Multiple Extras:**

```bash
pip install configguard[encryption,yaml,toml]
```

**Installing All Optional Features:**

```bash
pip install configguard[all]
```

**For Development:**

```bash
git clone https://github.com/ParisNeo/ConfigGuard.git
cd ConfigGuard
pip install -e .[dev]
```
This installs ConfigGuard itself, plus tools like `pytest`, `black`, `ruff`, `mypy`, and the dependencies needed for all built-in handlers, encryption, and the GUI example.

---

## ⚡ Quick Start

This example demonstrates defining a schema, initializing ConfigGuard (showing different ways to set the version), accessing/modifying values, and saving.

```python
from configguard import ConfigGuard, ValidationError, generate_encryption_key
from pathlib import Path
import typing # Required for type hinting the schema dict

# 1. Define your schema: Includes version, standard section, dynamic section, top-level setting.
SCHEMA_VERSION = "1.1.0"
my_schema: typing.Dict[str, typing.Any] = {
    "__version__": SCHEMA_VERSION, # Standard way to define version
    "server": { # Standard section
        "type": "section", "help": "Core web server settings.",
        "schema": {
            "host": { "type": "str", "default": "127.0.0.1", "help": "IP address to bind to." },
            "port": { "type": "int", "default": 8080, "min_val": 1024, "max_val": 65535, "help": "Port number." }
        }
    },
    "plugin_data": { # DYNAMIC section
        "type": "section", "help": "Stores runtime data or settings for plugins.",
        "schema": {} # Empty schema marks it as dynamic
    },
    "log_level": { # Standard top-level setting
        "type": "str", "default": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR"], "help": "Logging verbosity."
    }
}

# Schema without explicit version
my_schema_no_version = my_schema.copy(); del my_schema_no_version["__version__"]

# 2. Setup file path and optional encryption key
config_file = Path("my_app_config.yaml") # Using YAML handler (requires PyYAML)
encryption_key = generate_encryption_key() # Store securely!

# 3. Initialize ConfigGuard instance (Different Versioning Examples)
try:
    # Option A: Explicitly set instance version (overrides schema version)
    explicit_version = "1.2.0-dev"
    config = ConfigGuard(
        schema=my_schema,
        instance_version=explicit_version, # <-- Explicit version
        config_path=config_file,
        encryption_key=encryption_key
    )
    print(f"Initialized with Explicit Version: {config.version}") # -> 1.2.0-dev

    # Option B: Use version from schema (most common)
    # config = ConfigGuard(schema=my_schema, config_path=config_file, encryption_key=encryption_key)
    # print(f"Initialized with Schema Version: {config.version}") # -> 1.1.0

    # Option C: No version in schema or parameter (defaults to 0.0.0)
    # config = ConfigGuard(schema=my_schema_no_version, config_path=config_file, encryption_key=encryption_key)
    # print(f"Initialized with Default Version: {config.version}") # -> 0.0.0

# Handle missing dependencies for the chosen handler
except ImportError as e:
    print(f"ERROR: Missing dependency for {config_file.suffix} files: {e}")
    exit()
except Exception as e:
    print(f"ERROR: Failed to initialize ConfigGuard: {e}")
    exit()

# 4. Access values (defaults initially, unless file existed)
print(f"Initial Server Host: {config.server.host}") # -> '127.0.0.1'
print(f"Initial Log Level: {config['log_level']}") # -> 'INFO'
print(f"Initial Plugin Data: {config.plugin_data.get_config_dict()}") # -> {}

# 5. Access schema details
print(f"Help for server port: {config.server.sc_port.help}")

# 6. Modify values
try:
    config.server.port = 9090
    config['log_level'] = 'DEBUG'
    config.plugin_data['active_plugin'] = 'analyzer_v2' # Dynamic add
    config.plugin_data.user_prefs = {'theme': 'dark'} # Dynamic add
except ValidationError as e:
    print(f"VALIDATION ERROR: {e}")

print(f"Updated Port: {config.server.port}") # -> 9090
print(f"Active Plugin: {config.plugin_data['active_plugin']}") # -> 'analyzer_v2'

# 7. Save configuration (mode='values' is default, saves to config_file)
# The file will contain the version set during init (explicit_version in this case)
# if saved with mode='full'. Mode='values' does not save version info.
config.save()
print(f"Configuration saved to {config_file} (encrypted).")

# To save with version and schema:
# config.save(mode='full', filepath='my_app_config_full.yaml')

```

---

## 📚 Core Concepts Detailed

*   **Schema:** The cornerstone of ConfigGuard.
    *   **Structure:** A Python dictionary defining the entire configuration layout.
    *   **Versioning:** Determined by the `instance_version` parameter passed to the constructor, which takes precedence. If not provided, it falls back to the `__version__` key within the schema dictionary. If neither is present, it defaults to `"0.0.0"`. The version must be parseable by the `packaging` library.
    *   **Settings:** Keys in the schema dictionary represent setting names. Each setting has a definition dictionary specifying its properties.
    *   **Sections (`"type": "section"`):** Allows hierarchical grouping. Requires a nested `"schema"` dictionary which defines the contents of the section.
    *   **Dynamic Sections (`"schema": {}`):** A special type of section defined with an empty schema dictionary. These sections allow runtime addition/modification/deletion of arbitrary key-value pairs without schema validation for those pairs.
    *   **Setting Definition Keys:** (`type`, `default`, `help`, `nullable`, `options`, `min_val`, `max_val`). See previous sections for details.

*   **ConfigGuard Object:** The main object you interact with.
    *   **Initialization:** Created with the schema definition, optionally `instance_version`, `config_path`, `encryption_key`, `autosave`, and `handler`. The instance version is determined based on parameter/schema precedence. Automatically attempts to load data from `config_path` if provided.
    *   **`version` Attribute:** Stores the determined instance version (`config.version`).
    *   **Access:** Provides attribute (`config.setting`) and dictionary (`config['setting']`) access to top-level settings and sections.
    *   **Schema Access:** Use `config.sc_setting` or `config['sc_setting']` to get the `SettingSchema` object for a *defined* setting, or the schema dictionary for a section.

*   **ConfigSection Object:** Represents a nested section defined in the schema.
    *   **Access:** Provides the same attribute (`section.nested_setting`) and dictionary (`section['nested_setting']`) access for items defined within its schema, or for dynamic keys if it's a dynamic section.
    *   **Modification Rules:** Interact with the *contents* of a `ConfigSection`. You **cannot replace the section itself** via assignment.

*   **Dynamic Sections (`"schema": {}`):**
    *   **Purpose:** Flexibility for unknown keys (plugins, runtime data).
    *   **Behavior:** Acts like a nested dictionary. Add/update/delete keys freely.
    *   **Trade-off:** No schema validation for dynamic content.
    *   **Integration:** Dynamic content included in save/load/export/encryption.

*   **Storage Handlers:** Abstraction layer for persistence.
    *   **Selection:** Automatic based on `config_path` suffix (`.json`, `.yaml`, `.yml`, `.toml`, `.db`, `.sqlite`, `.sqlite3`, `.bin`, `.enc`).
    *   **Encryption:** Managed transparently if `encryption_key` is provided.
    *   **Structure Handling:** JSON/YAML/TOML preserve nesting. SQLite flattens keys (`server.port`) and stores values as encrypted JSON strings.

*   **Save Modes (`values` vs `full`):**
    *   `mode='values'`: Saves current *values* only (structured per handler). No version/schema info.
    *   `mode='full'`: Saves a complete snapshot: the current `instance_version`, the schema *definition*, and current *values*.

*   **Versioning & Migration:** Facilitates managing configuration changes.
    *   **Mechanism:** Compares loaded file's version (if present) with the `config.version` (instance version).
    *   **Loading Newer:** Raises `SchemaError`.
    *   **Loading Older:** Merges data recursively (loads matching, applies new defaults, skips removed).
    *   **Logging:** Warnings logged for skipped keys/coercion failures.

*   **Encryption:** Provides confidentiality using Fernet.
    *   **Key Management:** Use `configguard.generate_encryption_key()`. **Store the key securely.**
    *   **Transparency:** Handled by the storage handler. Application code sees plain data.

---

## 📖 Detailed Usage

### 1. Defining the Schema


(See Core Concepts section for key details)

```python
# More complex schema example
import typing
CONFIG_VERSION = "3.0.0"

complex_schema: typing.Dict[str, typing.Any] = {
    "__version__": CONFIG_VERSION,
    "network": {
        "type": "section", "help": "Network settings",
        "schema": {
            "hostname": {"type": "str", "default": "auto", "help": "System hostname (or 'auto')"},
            "port": {"type": "int", "default": 8000, "min_val": 1, "max_val": 65535},
            "allowed_ips": {"type": "list", "default": ["127.0.0.1", "::1"], "help": "List of allowed client IPs"},
        }
    },
    "performance": {
        "type": "section", "help": "Performance tuning",
        "schema": {
            "worker_threads": {"type": "int", "default": 4, "min_val": 1, "max_val": 64},
            "cache": {
                "type": "section", "help": "Caching options",
                "schema": {
                    "enabled": {"type": "bool", "default": True},
                    "max_size_mb": {"type": "int", "default": 1024, "min_val": 0},
                    "strategy": {"type": "str", "default": "LRU", "options": ["LRU", "FIFO", "LFU"]},
                }
            }
        }
    },
    "user_scripts": { # Dynamic section
        "type": "section", "help": "Paths to user-provided scripts.",
        "schema": {}
    },
    "enable_analytics": { "type": "bool", "default": False, "help": "Enable anonymous usage analytics."}
}

# Optionally save schema to JSON for reuse or distribution
# import json
# with open("app_schema_v3.json", "w") as f:
#     json.dump(complex_schema, f, indent=2)
```


### 2. Initializing ConfigGuard

Load schema from dictionary or file path. Provide `config_path`, `encryption_key`, and optionally `instance_version`.

```python
from configguard import ConfigGuard, generate_encryption_key, SchemaError, HandlerError, EncryptionError
from pathlib import Path

schema_source = complex_schema # Or Path("app_schema_v3.json")
config_file = Path("app_config_v3.db") # Using SQLite
enc_key = generate_encryption_key() # Store this securely!
instance_v = "3.1.0" # Explicit version

try:
    # Initialize with explicit version overriding any schema version
    config = ConfigGuard(
        schema=schema_source,
        config_path=config_file,
        encryption_key=enc_key,
        instance_version=instance_v # Provide the version here
    )
    print(f"ConfigGuard initialized with version: {config.version}")

    # Or, initialize using schema version (if instance_version=None)
    # config = ConfigGuard(schema=schema_source, config_path=config_file, ...)
    # print(f"ConfigGuard initialized with version: {config.version}") # Would use schema's __version__

except FileNotFoundError as e: print(f"Schema file error: {e}")
except SchemaError as e: print(f"Schema/Version error: {e}") # Catches invalid version format
except (HandlerError, ImportError) as e: print(f"Configuration handler error: {e}")
except EncryptionError as e: print(f"Encryption error: {e}")
except Exception as e: print(f"Unexpected initialization error: {e}")

```

### 3. Accessing Settings and Schema

(Usage remains identical to previous examples)

```python
cache_strategy = config.performance.cache.strategy
print(f"Cache Strategy: {cache_strategy}")
# ... etc ...
```

### 4. Modifying Settings

(Usage remains identical to previous examples)

```python
config.performance.worker_threads = 8
config.user_scripts['on_shutdown'] = '/opt/scripts/shutdown.sh'
# ... etc ...
```

### 5. Saving & Loading

`save()` persists the current state. `load()` reads from disk. `mode='full'` saves the current *instance* version.

```python
# Save current values (encrypted to SQLite DB)
config.save() # Defaults to mode='values'

# Save a full backup (will include instance_version="3.1.0" in this example)
try:
    backup_path = Path("config_v3.1_backup.json")
    config.save(filepath=backup_path, mode='full')
    print(f"Full backup saved to {backup_path}")
except Exception as e:
    print(f"Failed to save backup: {e}")

# Manual Load
try:
    config.load() # Reloads from the path config was initialized with
    print("Reload complete.")
except Exception as e:
    print(f"Error during manual load: {e}")

```

### 6. Versioning & Migration

Handled automatically during load based on `__version__`. Check logs for warnings about skipped keys or sections from older files.

```python
# --- Simulation ---
# Imagine current schema is V2.0.0
# Load a config file saved with schema V1.0.0:
# config_v1_path = Path("old_config_v1.json")
# try:
#    config_v2_instance = ConfigGuard(schema=schema_v2_dict, config_path=config_v1_path)
#    # ConfigGuard logs warnings for settings in v1 file not in v2 schema.
#    # Settings in v2 schema but not v1 file get v2 defaults.
#    # Matching settings have their values loaded from v1 file.
#    # Dynamic section content (if section exists in both) is loaded from v1 file.
# except SchemaError as e: # e.g. if v1 file version > v2 schema version
#    print(f"Version mismatch: {e}")
```

### 7. Encryption

Provide `encryption_key` at init. Generation and storage are key.

```python
from configguard import generate_encryption_key, ConfigGuard

# Generate key (DO THIS ONCE and store securely!)
# new_key = generate_encryption_key()
# print(f"Store this key safely: {new_key.decode()}")

# Use stored key
stored_key = b'YOUR_SECURELY_STORED_32_BYTE_URLSAFE_BASE64_KEY'

secure_config = ConfigGuard(
    schema=complex_schema,
    config_path="secure_app.bin", # Use .bin or .enc for encrypted files
    encryption_key=stored_key
)

# Modify sensitive and non-sensitive data
secure_config.network.hostname = "prod.server.local"
secure_config.user_scripts.deploy_key = "ssh-rsa AAA..." # Dynamic sensitive data

# Save - data is encrypted on disk
secure_config.save()

# Loading automatically decrypts
# loaded_config = ConfigGuard(...)
# print(loaded_config.user_scripts.deploy_key) # -> Prints plain key
```

### 8. Handling Nested Configurations

Define sections within sections in your schema. Access follows the structure naturally. Modification rules apply at each level.

```python
# Accessing deeply nested setting (from complex_schema)
cache_size = config.performance.cache.max_size_mb
print(f"Cache size: {cache_size}")

# Modifying deeply nested setting
config.performance.cache.enabled = False
config['performance']['cache']['strategy'] = 'FIFO' # Item access also works

# Cannot assign to nested section
# config.performance.cache = {"enabled": False} # INVALID
```

### 9. Import/Export

`export_schema_with_values()` provides a full snapshot. `import_config()` merges value updates.

```python
# --- Export ---
full_state = config.export_schema_with_values()

# Example structure of full_state['settings']:
# {
#   "network": { "schema": { ... }, "value": { "hostname": "auto", ... } },
#   "performance": {
#     "schema": { ... },
#     "value": {
#       "worker_threads": 8,
#       "cache": { "enabled": False, "max_size_mb": 1024, "strategy": "FIFO" } # Value is nested
#     }
#   },
#   "user_scripts": { # Dynamic section
#      "schema": { "type": "section", "help": "...", "schema": {} },
#      "value": { # Value contains the dynamic keys
#          "on_shutdown": "/opt/scripts/shutdown.sh",
#          "data_processor": { "type": "python", "path": "~/scripts/process.py" }
#      }
#   },
#   "enable_analytics": { "schema": { ... }, "value": False }
# }

import json
# print(json.dumps(full_state, indent=2))

# --- Import ---
update_data = {
    "performance": {
        "cache": {
            "max_size_mb": 2048, # Update nested standard setting
            "unknown_cache_param": True # Ignored if ignore_unknown=True
        }
    },
    "user_scripts": { # Add/update dynamic keys
        "new_report_script": "/usr/local/bin/report.py",
        "data_processor": { "type": "rust", "path": "/opt/bin/process_rs" } # Update dynamic value
    },
    "unknown_section": True # Ignored if ignore_unknown=True
}

try:
    # Merge updates, ignore keys not in schema (unless in dynamic section)
    config.import_config(update_data, ignore_unknown=True)
    print(f"Cache size after import: {config.performance.cache.max_size_mb}") # -> 2048
    print(f"Data processor after import: {config.user_scripts.data_processor}")
except SettingNotFoundError as e:
     print(f"Import failed (ignore_unknown=False): {e}")
except Exception as e:
    print(f"Import failed: {e}")
```

---

## 💡 Use Cases

*   **Robust Application Settings:** Define and manage essential parameters like server ports, file paths, feature flags, logging levels with guaranteed type safety and validation. Organize settings by application component (e.g., `server`, `database`, `ui`, `tasks`) using nested sections.
*   **Secure Credential Storage:** Store sensitive data like API keys, database connection strings with passwords, OAuth tokens, or encryption keys within specific sections (e.g., `credentials.database`, `credentials.external_api`). Enable encryption (`encryption_key`) to protect this data at rest transparently.
*   **User Preferences:** Manage user-specific application settings like themes, language choices, layout configurations, notification preferences. A standard section can enforce known preference keys, while a dynamic section could store UI state or less critical, user-defined preferences.
*   **Microservice Configuration:** Each service can have its own `ConfigGuard` schema defining its unique requirements (database connections, message queue endpoints, cache settings, service discovery URLs). Shared settings could potentially be managed through includes or layering if needed (though not a built-in feature).
*   **Multi-Environment Deployment:** Maintain consistency across development, staging, and production environments by using the same schema but different configuration files (`dev.yaml`, `staging.db`, `prod.toml`). Use encryption for production secrets. Versioning helps manage updates across environments.
*   **Plugin and Extension Systems:** Use dynamic sections (`"schema": {}`) to allow plugins or extensions to store their own configuration data without requiring modifications to the core application schema. The core app can load/save the dynamic section content, while the plugin interprets its own keys/values.
*   **Generating Configuration UIs:** Use the output of `export_schema_with_values()` to dynamically generate web forms or GUI elements for editing configurations. The schema provides field types, help text, options (for dropdowns), and validation rules (min/max) to build intelligent editors.
*   **Complex Workflow/Pipeline Configuration:** Define parameters for multi-step processes, data pipelines, or scientific workflows, potentially using nested sections for different stages and dynamic sections for stage-specific parameters.

---

## 🔧 Advanced Topics

*   **Custom Storage Handlers:** Extend ConfigGuard's capabilities by creating your own storage backend.
    1.  Subclass `configguard.handlers.StorageHandler`.
    2.  Implement the abstract `load(self, filepath)` and `save(self, filepath, data, mode)` methods.
        *   Your `load` must return a `LoadResult` dictionary (`{'version': Optional[str], 'schema': Optional[dict], 'values': dict}`).
        *   Your `save` must handle the `data` payload (`{'instance_version', 'schema_definition', 'config_values'}`) and the `mode` ('values' or 'full').
        *   If your handler should support encryption, use `self._encrypt(bytes)` and `self._decrypt(bytes)` internally, which leverage the Fernet instance passed during `__init__`.
        *   Consider how your format represents nested structures and dynamic section content.
    3.  Register your handler by adding its file extension(s) and class to the `configguard.handlers.HANDLER_MAP` dictionary, or provide an instance directly during `ConfigGuard` initialization using the `handler` argument.
*   **(Potential Future) Custom Migration Functions:** For complex schema changes between versions (e.g., renaming keys, splitting sections, complex type transformations), a future enhancement could allow users to register custom Python functions to handle specific version-to-version migrations beyond the default key matching and default filling.
*   **(Potential Future) Schema Includes/Composition:** For very large configurations, a mechanism to include or compose schemas from multiple files could be considered.

---

## 🤝 Contributing

Contributions are highly welcome and appreciated! Help make ConfigGuard even better.

1.  **Found a Bug or Have an Idea?** Check the [Issue Tracker](https://github.com/ParisNeo/ConfigGuard/issues) to see if it's already reported. If not, please open a new issue, providing as much detail as possible (code examples, error messages, expected vs. actual behavior).
2.  **Ready to Contribute Code?**
    *   **Fork the Repository:** Create your own fork on GitHub.
    *   **Create a Branch:** Make a new branch in your fork for your changes (e.g., `feature/add-new-handler`, `bugfix/fix-validation-edge-case`).
    *   **Develop:** Write your code, ensuring it adheres to the project's quality standards:
        *   **Style:** Follow PEP 8 guidelines. Use **Black** for code formatting (`black .`).
        *   **Linting:** Use **Ruff** for linting (`ruff check .`). Address reported issues.
        *   **Typing:** Add **Type Hints** (`typing`) to all functions and methods. Check with **Mypy** (`mypy configguard`).
        *   **Docstrings:** Write clear, informative docstrings (Google style preferred) for all public modules, classes, functions, and methods. Explain parameters, return values, raised exceptions, and usage.
    *   **Testing:** Add **unit tests** using `pytest` in the `tests/` directory for any new features or bug fixes. Ensure existing tests pass. Aim for high test coverage (`pytest --cov=configguard`).
    *   **Commit:** Write clear, concise commit messages explaining your changes.
    *   **Push & Pull Request:** Push your branch to your fork and open a Pull Request against the `main` branch of the original `ParisNeo/ConfigGuard` repository. Describe your changes in the PR description and link any relevant issues.
3.  **Code of Conduct:** Please note that this project is released with a Contributor Code of Conduct. By participating, you are expected to uphold this code. (A formal CODE_OF_CONDUCT.md file may be added later).

---

## 📜 License

ConfigGuard is distributed under the terms of the **Apache License 2.0**.

This means you are free to use, modify, and distribute the software for commercial or non-commercial purposes, but you must include the original copyright notice and license text. See the [LICENSE](LICENSE) file in the repository for the full license text.

---

<p align="center">
  Built with ❤️ by ParisNeo with the help of Gemini 2.5
</p>