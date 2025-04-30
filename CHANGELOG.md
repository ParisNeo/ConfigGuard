# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-05-01

This version introduces support for nested configuration sections, allowing for more structured and organized configuration schemas.

### Added

*   **Nested Sections:** Introduced the ability to define hierarchical configuration sections within the schema using `"type": "section"` and a nested `"schema": {...}` definition.
*   **`ConfigSection` Class:** Added a new internal class (`configguard.section.ConfigSection`) to represent and manage nested sections.
*   **Recursive Operations:** Core `ConfigGuard` methods (`load`, `save`, `get_config_dict`, `import_config`, `export_schema_with_values`, `_apply_and_migrate_values`, `_build_internal_structure_from_schema`) now operate recursively to handle nested sections.
*   **Nested Access:** Settings within sections can now be accessed using attribute (`config.section.setting`) and dictionary (`config['section']['setting']`) syntax. Schema details are accessed similarly (`config.sc_section.sc_setting`).
*   **Autosave Propagation:** Autosave functionality now correctly triggers when modifying settings within nested sections.

### Changed

*   **Internal Structure:** `ConfigGuard._settings` dictionary can now hold both `ConfigSetting` and `ConfigSection` objects.
*   **Schema Parsing:** `_build_internal_structure_from_schema` is now recursive and handles the `"section"` type.
*   **Value Application:** `_apply_and_migrate_values` is now recursive, applying loaded values and migration logic within sections. It now also includes an `ignore_unknown` flag to control behavior for undefined keys during import/load.
*   **Data Retrieval:** `get_config_dict` and `export_schema_with_values` now recursively build nested dictionaries representing the configuration structure and values.
*   **Access Methods:** `__getattr__`, `__setattr__`, `__getitem__`, `__setitem__` in `ConfigGuard` updated to delegate access to `ConfigSection` objects when appropriate. Direct assignment to sections (`config.section = ...` or `config['section'] = ...`) is now disallowed.
*   **`ConfigSetting.__init__`:** Now accepts an optional `parent` argument (either `ConfigGuard` or `ConfigSection`) to facilitate autosave triggering.
*   **`ConfigGuard.load`:** Now passes `ignore_unknown=False` to `_apply_and_migrate_values` to enforce schema strictness during file loading (migration still handles skipping old keys).
*   **`ConfigGuard.import_config`:** Now passes the `ignore_unknown` flag down to the recursive `_apply_and_migrate_values` method for consistent handling of unknown keys.

### Removed

*   (No specific removals in this version related to core functionality).

## [0.2.0] - 2025-04-30

This version introduced significant refactoring for handler agnosticism, robust versioning, and integrated encryption within handlers.

### Added

*   **Schema Versioning:** Introduced mandatory `__version__` key in schema definitions for version tracking and migration.
*   **Versioning Logic:** `ConfigGuard.load()` now compares file version with instance version.
    *   Raises `SchemaError` if file version is newer.
    *   Enables basic migration logic if file version is older (loads matching keys, uses new defaults, skips removed keys).
*   **Save Modes:** `ConfigGuard.save()` now accepts a `mode` argument:
    *   `mode='values'`: Saves only the configuration key-value pairs (default behaviour).
    *   `mode='full'`: Saves version, schema definition, and values structure.
*   **Type Coercion:** Basic type coercion added (`_try_coerce`) during load/migration when schema types differ between file and instance (e.g., int <-> float <-> numeric string).
*   **Handler-Agnosticism:** `ConfigGuard` now interacts with handlers solely through the `StorageHandler` interface for core load/save operations.
*   **Encrypted File Extension Mapping:** Added default mapping for `.bin` and `.enc` extensions to `JsonHandler` in `handlers/__init__.py`, assuming JSON as the underlying format for generic encrypted files.
*   Dependency on `packaging` library for robust version parsing.

### Changed

*   **BREAKING:** Refactored `StorageHandler` interface:
    *   `__init__` now accepts an optional `fernet` instance for encryption.
    *   `load()` method now returns a structured `LoadResult` dictionary (`{'version': str|None, 'schema': dict|None, 'values': dict}`).
    *   `save()` method now accepts a `data` payload (`{'instance_version', 'schema_definition', 'config_values'}`) and a `mode` string ('values' or 'full').
    *   Added protected `_encrypt()` and `_decrypt()` helper methods to `StorageHandler` base class.
*   **BREAKING:** Encryption/Decryption logic moved from `ConfigGuard` into the `StorageHandler` implementations. Handlers are now responsible for handling the `fernet` instance passed during initialization.
*   **BREAKING:** `configguard.handlers.get_handler()` factory function now accepts an optional `fernet` argument to pass to the handler constructor.
*   `ConfigGuard.load()` implementation rewritten to use the new handler interface and incorporate versioning/migration logic via `_apply_and_migrate_values`.
*   `ConfigGuard.save()` implementation rewritten to prepare payload and call the handler's `save()` method with the specified `mode`.
*   `JsonHandler` updated to fully implement the new `StorageHandler` interface, managing save modes and internal encryption/decryption.
*   `ConfigGuard.__init__` now reads `__version__` from schema, initializes Fernet instance, and passes Fernet to `get_handler`.
*   `ConfigGuard.import_config()` refined to use the internal `_apply_and_migrate_values` logic.
*   `ConfigGuard._load_schema_definition()` adjusted to load raw schema correctly.
*   Logging improved across different modules and operations.

### Removed

*   Direct encryption/decryption logic within `ConfigGuard.load()` and `ConfigGuard.save()`.
*   `ConfigGuard.save_schema_and_values()` method (functionality replaced by `save(mode='full')`).
*   `ConfigGuard.load_schema_and_values()` method (functionality replaced by `load()` interpreting `LoadResult`).

## [0.1.0] - 2025-04-30

Initial functional release of ConfigGuard.

### Added

*   Core `ConfigGuard` class for configuration management.
*   `SettingSchema` and `ConfigSetting` classes for schema definition and value holding.
*   Support for basic types: `str`, `int`, `float`, `bool`, `list`.
*   Schema features: `default`, `help`, `nullable`, `options`, `min_val`, `max_val`.
*   Attribute (`config.setting`) and dictionary (`config['setting']`) access for values.
*   Schema access via `sc_` prefix (`config.sc_setting` or `config['sc_setting']`).
*   Validation on setting values.
*   `JsonHandler` for saving/loading configurations to/from JSON files.
*   Basic encryption support directly within `ConfigGuard` (requires `cryptography`).
*   `export_schema_with_values()` method to get schema + values for external use.
*   `import_config()` method to import values from a dictionary.
*   Logging using `ascii_colors`.
*   Basic project structure (`pyproject.toml`, `.gitignore`).
*   Example script (`examples/basic_usage.py`).
*   Initial `README.md`.

### Fixed
*   Initial boolean coercion logic issues.
*   Handler instantiation errors when loading schemas or encrypted files.
*   Validation logic for `None` values with `nullable=True`.

---