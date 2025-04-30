#############
Usage Guide
#############

This guide walks through the primary features of ConfigMaster using examples.

Core Concepts Recap
===================
Before diving in, remember these key ideas:

*   **Schema**: A Python dictionary defining your settings (types, defaults, validation, version).
*   **ConfigMaster Instance**: The main object holding the schema and current values.
*   **Handlers**: Internal components for reading/writing different file formats (e.g., JSON) and handling encryption.
*   **Save Modes**: ``mode='values'`` (default, saves only values) or ``mode='full'`` (saves version, schema, and values).
*   **Versioning**: Automatic comparison during ``load()``; handles older versions via migration, raises errors for newer versions.

1. Defining Your Schema
=======================
Create a Python dictionary. The top level needs ``__version__``. Other keys are your settings.

.. literalinclude:: ../examples/basic_usage.py
   :language: python
   :lines: 22-67
   :caption: Example Schema Definition (v1.1.0)

See the schema definition keys in the main README or API docs for `SettingSchema`.

2. Initializing ConfigMaster
============================
Pass the schema (dict or file path) and optionally the config file path and encryption key.

.. code-block:: python

   from configmaster import ConfigMaster, generate_encryption_key
   from pathlib import Path

   # Assume my_app_schema is the dictionary defined above
   # Assume config_file_path points to "my_settings.json"
   # Assume full_state_file_path points to "my_settings_full.json"
   # Assume enc_key is a valid Fernet key

   # Basic initialization (values mode, no encryption)
   config_basic = ConfigMaster(schema=my_app_schema, config_path=config_file_path)

   # With encryption
   config_encrypted = ConfigMaster(
       schema=my_app_schema,
       config_path="encrypted_settings.bin", # Use appropriate extension
       encryption_key=enc_key
   )

   # With autosave (saves values automatically on change)
   # config_autosave = ConfigMaster(schema=my_app_schema, config_path=config_file_path, autosave=True)

ConfigMaster automatically tries to ``load()`` from ``config_path`` if it exists.

3. Accessing Settings and Schema
================================
Use attribute or dictionary syntax. Use the ``sc_`` prefix for schema details.

.. code-block:: python

   # Access value
   port = config_basic.port
   log_level = config_basic['log_level']

   # Access schema
   port_help = config_basic.sc_port.help
   is_db_nullable = config_basic['sc_database_uri'].nullable

   print(f"Port: {port} (Help: {port_help})")
   print(f"Is DB Nullable? {is_db_nullable}")

4. Modifying Settings
=====================
Assign values directly. Validation occurs automatically.

.. code-block:: python

   config_basic.port = 8443
   config_basic['log_level'] = 'WARNING'
   config_basic.feature_flags.append('new_feature_x') # Modifying lists works directly

   try:
       config_basic.port = 100 # Below min_val
   except ValidationError as e:
       print(f"Validation failed: {e}")

5. Saving Configuration
=======================
Specify the ``mode``: ``'values'`` or ``'full'``.

.. code-block:: python

   # Save only values to the default path
   config_basic.save(mode='values')
   print(f"Values saved to {config_basic._config_path}") # Access internal for demo

   # Save full state to a different file
   config_basic.save(filepath="config_backup.json", mode='full')
   print("Full state saved to config_backup.json")

6. Loading and Version Handling
===============================
Loading usually happens on initialization. Manual ``config.load()`` is possible. Versioning is automatic.

Let's simulate loading an older version:

.. literalinclude:: ../examples/basic_usage.py
   :language: python
   :lines: 240-270
   :caption: Simulating Older Version File Creation

.. code-block:: python

   # Assume my_app_schema is the V1.1.0 schema
   # Assume older_file path points to the simulated V1.0.0 file

   try:
       print("\\nLoading older config into V1.1.0 instance...")
       # Initialize with CURRENT schema, load OLD file
       config_migrated = ConfigMaster(schema=my_app_schema, config_path=older_file)

       print(f"Loaded file version: {config_migrated.loaded_file_version}") # Should be "1.0.0"
       print(f"Instance version: {config_migrated.version}")         # Should be "1.1.0"

       # Values from old file are loaded if key exists in V1.1.0 schema
       print(f"Port loaded from old: {config_migrated.port}") # e.g., 7000

       # New settings get V1.1.0 defaults
       print(f"Timeout (new in V1.1.0): {config_migrated.timeout_seconds}") # e.g., 30.0

       # Settings only in old file are skipped (warning logged)

   except SchemaError as e:
       print(f"Schema error (e.g., file version too new): {e}")
   except Exception as e:
       print(f"Other loading error: {e}")


7. Encryption
=============
Provide a `encryption_key` during initialization. Saving and loading become transparently encrypted/decrypted by the handler.

.. literalinclude:: ../examples/basic_usage.py
   :language: python
   :pyobject: run_basic_usage_example
   :lines: 344-391
   :dedent: 8
   :caption: Encryption Example Snippet

8. Import/Export
================

Export Current State (Schema + Values)
--------------------------------------
Useful for UIs or sending state over APIs.

.. code-block:: python

   current_state = config_basic.export_schema_with_values()
   import json
   print(json.dumps(current_state, indent=2))

Import Values from Dictionary
-----------------------------
Update settings from a dict (e.g., from a web form). Only affects values, ignores schema/version.

.. code-block:: python

    update_data = {"port": 9999, "log_level": "ERROR", "unknown": "skipped"}
    try:
        config_basic.import_config(update_data, ignore_unknown=True)
        print(f"Port after import: {config_basic.port}")
    except Exception as e:
        print(f"Import failed: {e}")

This covers the main workflows for using ConfigMaster effectively. Check the :doc:`api` reference for detailed class and method information.