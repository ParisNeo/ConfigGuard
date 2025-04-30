# Project: ConfigGuard
# File: handlers/__init__.py
# Author: ParisNeo with Gemini 2.5
# Date: 30/04/2025
# Description: Initializes the handlers package for ConfigGuard.
#              Provides a factory function `get_handler` to instantiate the appropriate
#              StorageHandler based on file extension and manages the mapping of
#              extensions to handler classes.

import typing
from pathlib import Path

# TODO: Import other handlers here when they are implemented
# from .yaml_handler import YamlHandler
# from .toml_handler import TomlHandler
# from .sqlite_handler import SqliteHandler
# Import necessary exceptions and logging from the parent package
from ..exceptions import HandlerError
from ..log import log

# Import the abstract base class
from .base import StorageHandler

# Import concrete handler implementations
from .json_handler import JsonHandler

# Type hint for the Fernet object (can be Any if cryptography is optional)
FernetInstance = typing.Optional[typing.Any]

# Map file extensions (lowercase) to their corresponding handler *classes*.
# This allows the factory function `get_handler` to instantiate the correct type.
HANDLER_MAP: typing.Dict[str, typing.Type[StorageHandler]] = {
    ".json": JsonHandler,
    # Assume JSON as the underlying format for these encrypted files
    ".bin": JsonHandler,
    ".enc": JsonHandler,
    # TODO: Add mappings for other handlers when implemented
    # ".yaml": YamlHandler,
    # ".yml": YamlHandler, # Common alternative extension for YAML
    # ".toml": TomlHandler,
    # ".db": SqliteHandler, # Example for SQLite
    # ".sqlite": SqliteHandler,
    # ".sqlite3": SqliteHandler,
}


def get_handler(
    filepath: typing.Union[str, Path], fernet: FernetInstance = None
) -> StorageHandler:
    """
    Factory function to get an initialized storage handler instance.

    Determines the appropriate handler class based on the file extension of the
    provided path and instantiates it, passing the optional Fernet instance
    for encryption/decryption capabilities.

    Args:
        filepath: The path (string or Path object) to the configuration file.
                  The file extension is used to select the handler.
        fernet: An optional initialized Fernet instance (from the 'cryptography' library).
                This is passed to the handler's constructor. Defaults to None.

    Returns:
        An initialized instance of a concrete StorageHandler subclass appropriate
        for the file type.

    Raises:
        HandlerError: If no handler is found for the file extension or if the
                      handler fails to instantiate.
    """
    path = Path(filepath)
    # Normalize extension to lowercase for reliable mapping lookup
    extension = path.suffix.lower()

    log.debug(
        f"Handler Factory: Determining handler for file: {filepath} (extension: '{extension}')"
    )

    handler_class: typing.Optional[typing.Type[StorageHandler]] = HANDLER_MAP.get(
        extension
    )

    if handler_class:
        try:
            # Instantiate the found handler class, passing the Fernet instance
            handler_instance = handler_class(fernet=fernet)
            encryption_status = "with" if fernet else "without"
            log.debug(
                f"Handler Factory: Instantiated handler: {handler_class.__name__} {encryption_status} encryption support."
            )
            return handler_instance
        except Exception as e:
            # Catch potential errors during handler initialization
            log.error(
                f"Handler Factory: Failed to instantiate handler {handler_class.__name__} for extension '{extension}': {e}",
                exc_info=True,
            )
            raise HandlerError(
                f"Failed to initialize handler for extension '{extension}': {e}"
            ) from e
    else:
        # No handler class was found in the map for this extension
        supported_extensions = list(HANDLER_MAP.keys())
        log.error(
            f"Handler Factory: No storage handler found for file extension '{extension}'. Supported extensions: {supported_extensions}"
        )
        raise HandlerError(
            f"Unsupported configuration file extension: '{extension}'. Supported extensions: {supported_extensions}"
        )


# Define what gets exported when 'from .handlers import *' is used
# Typically includes the base class, concrete classes, and the factory function.
__all__ = [
    "StorageHandler",  # Base class
    "JsonHandler",  # Concrete handler
    # TODO: Add other concrete handler classes here
    # "YamlHandler",
    # "TomlHandler",
    # "SqliteHandler",
    "get_handler",  # Factory function
    "HANDLER_MAP",  # The mapping itself (might be useful for introspection)
]
