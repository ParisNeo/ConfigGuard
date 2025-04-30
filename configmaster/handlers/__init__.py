    # configmaster/handlers/__init__.py
from pathlib import Path
import typing

from .base import StorageHandler
from .json_handler import JsonHandler
# Import other handlers here when added
# from .yaml_handler import YamlHandler
# from .toml_handler import TomlHandler
# from .sqlite_handler import SqliteHandler
from ..exceptions import HandlerError
from ..log import log

# Map file extensions (lowercase) to handler classes
HANDLER_MAP: typing.Dict[str, typing.Type[StorageHandler]] = {
    ".json": JsonHandler,
    # ".yaml": YamlHandler,
    # ".yml": YamlHandler,
    # ".toml": TomlHandler,
    # ".db": SqliteHandler,
    # ".sqlite": SqliteHandler,
    # ".sqlite3": SqliteHandler,
}

def get_handler(filepath: typing.Union[str, Path]) -> StorageHandler:
    """
    Gets the appropriate storage handler based on the file extension.

    Args:
        filepath: The path to the configuration file.

    Returns:
        An instance of the appropriate StorageHandler subclass.

    Raises:
        HandlerError: If no handler is found for the file extension.
    """
    path = Path(filepath)
    extension = path.suffix.lower()

    log.debug(f"Determining handler for file: {filepath} (extension: '{extension}')")

    handler_class = HANDLER_MAP.get(extension)

    if handler_class:
        log.debug(f"Found handler: {handler_class.__name__}")
        return handler_class()
    else:
        log.error(f"No storage handler found for file extension '{extension}' in {filepath}.")
        raise HandlerError(f"Unsupported configuration file extension: '{extension}'. Supported extensions: {list(HANDLER_MAP.keys())}")

# Expose handlers directly if needed
__all__ = [
    "StorageHandler",
    "JsonHandler",
    # "YamlHandler",
    # "TomlHandler",
    # "SqliteHandler",
    "get_handler",
    "HANDLER_MAP"
]