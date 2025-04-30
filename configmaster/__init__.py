# configmaster/__init__.py
"""
ConfigMaster: A configuration management suite.
"""
__version__ = "0.1.0"

from .schema import SettingSchema
from .setting import ConfigSetting
from .config import ConfigMaster
from .exceptions import (
    ConfigMasterError,
    SchemaError,
    ValidationError,
    HandlerError,
    EncryptionError,
    SettingNotFoundError
)
from .log import set_log_level, log

# Optionally generate a key for users
def generate_encryption_key() -> bytes:
    """Generates a suitable Fernet key for encryption."""
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key()
    except ImportError:
        log.error("Cannot generate encryption key: 'cryptography' library not installed.")
        log.error("Please install it: pip install cryptography")
        raise ImportError("Cryptography library not found, needed for key generation.")

__all__ = [
    "ConfigMaster",
    "SettingSchema",
    "ConfigSetting",
    "ConfigMasterError",
    "SchemaError",
    "ValidationError",
    "HandlerError",
    "EncryptionError",
    "SettingNotFoundError",
    "generate_encryption_key",
    "set_log_level",
    "log",
    "__version__",
    "export_schema_with_values",
]