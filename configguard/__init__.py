# Project: ConfigGuard
# File: __init__.py
# Author: ParisNeo with Gemini 2.5
# Date: 30/04/2025
# Description: Initializes the ConfigGuard package, defining the public API.
#              This file makes key classes, exceptions, and utility functions
#              available directly under the 'configguard' namespace.

"""
ConfigGuard: A configuration management suite.

This package provides tools for defining, validating, loading, saving,
and managing application configurations with support for various storage
formats, encryption, versioning, and schema definition.
"""

import typing

# Define package version
__version__ = "0.2.0"  # Updated to reflect recent changes

# Import key components to expose them at the package level
from .config import ConfigGuard
from .exceptions import (
    ConfigMasterError,
    EncryptionError,
    HandlerError,
    SchemaError,
    SettingNotFoundError,
    ValidationError,
)
from .log import log, set_log_level  # Expose logger instance and level setter
from .schema import SettingSchema
from .setting import ConfigSetting


# Import utility functions
def generate_encryption_key() -> bytes:
    """
    Generates a new Fernet key suitable for ConfigGuard encryption.

    Requires the 'cryptography' library to be installed.

    Returns:
        A URL-safe base64-encoded 32-byte key as bytes.

    Raises:
        ImportError: If the 'cryptography' library is not installed.
    """
    try:
        from cryptography.fernet import Fernet

        return Fernet.generate_key()
    except ImportError:
        log.error(
            "Cannot generate encryption key: 'cryptography' library not installed."
        )
        log.error("Please install it: pip install cryptography")
        # Re-raise the ImportError so the caller knows the dependency is missing
        raise


# Define the public API of the package
# Specifies which names are imported when 'from configguard import *' is used.
__all__: typing.List[str] = [
    # Core class
    "ConfigGuard",
    # Schema and Setting classes
    "SettingSchema",
    "ConfigSetting",
    # Base and specific exceptions
    "ConfigMasterError",
    "SchemaError",
    "ValidationError",
    "HandlerError",
    "EncryptionError",
    "SettingNotFoundError",
    # Utility functions
    "generate_encryption_key",
    "set_log_level",
    # Logger instance (use with caution, prefer using specific loggers in applications)
    "log",
    # Package version
    "__version__",
]
