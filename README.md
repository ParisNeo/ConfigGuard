# ConfigMaster

[![PyPI version](https://img.shields.io/pypi/v/configmaster.svg)](https://pypi.org/project/configmaster/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/configmaster.svg)](https://pypi.org/project/configmaster/)
[![PyPI license](https://img.shields.io/pypi/l/configmaster.svg)](https://github.com/ParisNeo/ConfigMaster/blob/main/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<!-- [![Documentation Status](https://parisneo.github.io/ConfigMaster/badge/?version=latest)](https://parisneo.github.io/ConfigMaster/) Placeholder -->

A configuration management suite with multiple file formats, entries typing (with a schema), nested configs etc. Built with love by ParisNeo using Gemini Pro.

## ✨ Features

*   **Schema Definition:** Define your configuration structure with types, default values, help text, and validation rules (min/max, options).
*   **Easy Access:** Access configuration values like attributes (`config.my_setting`) or dictionary items (`config['my_setting']`). Access schema details using the `sc_` prefix (`config.sc_my_setting`).
*   **JSON Serializable:** Both the configuration schema and values are easily serializable to JSON, perfect for frontends or APIs.
*   **Multiple Backends:** Load and save configurations from/to various formats (JSON, YAML, TOML, SQLite planned) through an extensible handler system.
*   **Encryption:** Optionally encrypt configuration data at rest using a secret key.
*   **Validation:** Automatic validation of values against the schema when setting or loading data.
*   **Extensible:** Designed to be easily extended with new storage formats or validation types.
*   **Logging:** Uses `ascii_colors` for informative and colorful logging.

## 🚀 Installation

```bash
pip install configmaster
```

## Quick Start

```python
from configmaster import ConfigMaster
from pathlib import Path

# 1. Define the configuration schema
my_schema = {
    "database_uri": {
        "type": "str",
        "default": "sqlite:///default.db",
        "help": "Database connection string."
    },
    "port": {
        "type": "int",
        "default": 8080,
        "min_val": 1024,
        "max_val": 65535,
        "help": "The network port to listen on."
    },
    "log_level": {
        "type": "str",
        "default": "INFO",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "help": "Logging level."
    },
    "feature_flags": {
        "type": "list",
        "default": ["feature_a"],
        "help": "List of enabled feature flags."
    },
    "enabled": {
        "type": "bool",
        "default": True,
        "help": "Enable or disable the service."
    }
}

# 2. Create or load the configuration
config_file = Path("my_app_config.json")
config = ConfigMaster(schema=my_schema, config_path=config_file)

# 3. Access values
print(f"Database URI: {config.database_uri}")
print(f"Port: {config.port}")

# 4. Access schema details
print(f"Help for port: {config.sc_port.help}")
print(f"Allowed log levels: {config.sc_log_level.options}")
print(f"Type of enabled flag: {config.sc_enabled.type}")

# 5. Modify values (validation happens automatically)
config.port = 9000
config.log_level = "DEBUG"
# config.port = 80 # Raises ValidationError

# 6. Save the configuration
config.save()
print(f"Configuration saved to {config_file}")

# 7. Load configuration again (optional)
config2 = ConfigMaster(schema=my_schema, config_path=config_file)
print(f"Loaded Port: {config2.port}")

# 8. Get schema as dict (for frontend)
schema_dict = config.get_schema_dict()
import json
print("\nSchema for Frontend:")
print(json.dumps(schema_dict, indent=2))

# 9. Get config values as dict
config_values = config.get_config_dict()
print("\nCurrent Config Values:")
print(json.dumps(config_values, indent=2))
```

*(More features like encryption, other file formats, and examples coming soon!)*

---

## 🤝 Contributing

Contributions are welcome! Please follow standard GitHub practices (fork, branch, pull request).

---

## 📜 License

Distributed under the Apache License 2.0. See `LICENSE` file for details.