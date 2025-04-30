# configguard/exceptions.py


class ConfigMasterError(Exception):
    """Base exception for all ConfigGuard errors."""

    pass


class SchemaError(ConfigMasterError):
    """Error related to schema definition or validation."""

    pass


class ValidationError(ConfigMasterError):
    """Error raised when a value fails validation against the schema."""

    pass


class HandlerError(ConfigMasterError):
    """Error related to loading or saving configuration using a handler."""

    pass


class EncryptionError(ConfigMasterError):
    """Error related to encryption or decryption."""

    pass


class SettingNotFoundError(ConfigMasterError, KeyError):
    """Error raised when trying to access a non-existent setting."""

    pass
