# configguard/exceptions.py


class ConfigGuardError(Exception):
    """Base exception for all ConfigGuard errors."""

    pass


class SchemaError(ConfigGuardError):
    """Error related to schema definition or validation."""

    pass


class ValidationError(ConfigGuardError):
    """Error raised when a value fails validation against the schema."""

    pass


class HandlerError(ConfigGuardError):
    """Error related to loading or saving configuration using a handler."""

    pass


class EncryptionError(ConfigGuardError):
    """Error related to encryption or decryption."""

    pass


class SettingNotFoundError(ConfigGuardError, KeyError):
    """Error raised when trying to access a non-existent setting."""

    pass
