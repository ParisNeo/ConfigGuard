# configmaster/handlers/base.py
import abc
from pathlib import Path
import typing

class StorageHandler(abc.ABC):
    """Abstract base class for configuration storage handlers."""

    @abc.abstractmethod
    def load(self, filepath: Path) -> dict:
        """
        Load configuration data from the specified file.

        Args:
            filepath: The path to the configuration file.

        Returns:
            A dictionary containing the loaded configuration data {setting_name: value}.

        Raises:
            FileNotFoundError: If the file does not exist.
            HandlerError: If loading fails due to format or other issues.
        """
        pass

    @abc.abstractmethod
    def save(self, filepath: Path, data: dict):
        """
        Save configuration data to the specified file.

        Args:
            filepath: The path to the configuration file.
            data: A dictionary containing the configuration data to save {setting_name: value}.

        Raises:
            HandlerError: If saving fails.
        """
        pass