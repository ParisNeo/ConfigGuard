# configmaster/handlers/json_handler.py
import json
from pathlib import Path
from .base import StorageHandler
from ..exceptions import HandlerError
from ..log import log

class JsonHandler(StorageHandler):
    """Handles loading and saving configuration in JSON format."""

    def load(self, filepath: Path) -> dict:
        """Loads configuration from a JSON file."""
        if not filepath.exists():
            log.warning(f"JSON config file not found: {filepath}. Returning empty config.")
            return {} # Return empty dict if file doesn't exist, ConfigMaster will use defaults

        log.debug(f"Loading configuration from JSON file: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                 raise HandlerError(f"JSON config file '{filepath}' does not contain a valid JSON object (dictionary).")
            log.info(f"Successfully loaded configuration from {filepath}")
            return data
        except json.JSONDecodeError as e:
            log.error(f"Failed to decode JSON from {filepath}: {e}")
            raise HandlerError(f"Failed to decode JSON from {filepath}: {e}") from e
        except Exception as e:
            log.error(f"An unexpected error occurred while loading JSON from {filepath}: {e}")
            raise HandlerError(f"Error loading JSON from {filepath}: {e}") from e

    def save(self, filepath: Path, data: dict):
        """Saves configuration to a JSON file."""
        log.debug(f"Saving configuration to JSON file: {filepath}")
        try:
            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False) # Use indent for readability
            log.info(f"Configuration successfully saved to {filepath}")
        except TypeError as e:
             log.error(f"Data type error while saving JSON to {filepath}: {e}. Data: {data}")
             raise HandlerError(f"Data type error saving JSON: {e}") from e
        except Exception as e:
            log.error(f"An unexpected error occurred while saving JSON to {filepath}: {e}")
            raise HandlerError(f"Error saving JSON to {filepath}: {e}") from e
