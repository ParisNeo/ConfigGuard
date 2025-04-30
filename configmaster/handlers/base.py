# -*- coding: utf-8 -*-
# Project: ConfigMaster
# File: handlers/base.py
# Author: ParisNeo with Gemini 2.5
# Date: 30/04/2025
# Description: Abstract base class definition for ConfigMaster storage handlers.
#              Defines the required interface for loading and saving configuration data,
#              potentially handling encryption.

import abc
from pathlib import Path
import typing

# Define the structured dictionary format returned by load
# This helps ensure type safety and clarity for handler implementers and users.
LoadResult = typing.TypedDict('LoadResult', {
    'version': typing.Optional[str],
    'schema': typing.Optional[dict],
    'values': dict
})

class StorageHandler(abc.ABC):
    """
    Abstract base class for all configuration storage handlers in ConfigMaster.

    Concrete handlers must implement the `load` and `save` methods to interact
    with specific storage formats (e.g., JSON, YAML, TOML, Database). They should
    also handle encryption and decryption internally if a Fernet instance is
    provided during initialization.
    """

    def __init__(self, fernet: typing.Optional[typing.Any] = None) -> None:
        """
        Initializes the storage handler.

        Args:
            fernet: An optional initialized Fernet instance from the 'cryptography' library.
                    If provided, the handler MUST use it to encrypt data before saving
                    and decrypt data after loading from the physical storage. If None,
                    data is saved/loaded in plain text.
        """
        # TODO: Consider runtime check for Fernet type if cryptography is optional install?
        self._fernet = fernet

    @abc.abstractmethod
    def load(self, filepath: Path) -> LoadResult:
        """
        Load configuration data from the specified file path.

        Implementations must handle reading the file format correctly. If the handler
        was initialized with a Fernet instance (`self._fernet`), this method MUST
        first read the raw bytes, then attempt decryption using `self._decrypt`,
        and finally parse the decrypted data according to the storage format.

        Args:
            filepath: The absolute or relative Path object pointing to the configuration file.

        Returns:
            A LoadResult dictionary containing:
            - 'version': The version string found in the file if the file represents
                         a 'full' save state, otherwise None.
            - 'schema': The schema dictionary found in the file if the file represents
                        a 'full' save state, otherwise None.
            - 'values': A dictionary containing the loaded configuration values
                        ({setting_name: value}). This key MUST always be present,
                        returning an empty dict if the file is empty or only contains
                        metadata in 'full' mode.

        Raises:
            FileNotFoundError: If the file specified by `filepath` does not exist.
            HandlerError: If loading, parsing, or data structure validation fails
                          for reasons specific to the handler or format.
            EncryptionError: If decryption fails (only applicable if initialized with Fernet).
        """
        raise NotImplementedError("Subclasses must implement the load method.")

    @abc.abstractmethod
    def save(self, filepath: Path, data: dict, mode: str = 'values') -> None:
        """
        Save configuration data to the specified file path.

        Implementations must handle serializing the data according to the storage format.
        If the handler was initialized with a Fernet instance (`self._fernet`), this method
        MUST first serialize the appropriate data to bytes, then encrypt these bytes using
        `self._encrypt`, and finally write the encrypted bytes to the file.

        Args:
            filepath: The absolute or relative Path object pointing to the target file.
                      The handler should ensure parent directories exist.
            data: A dictionary containing the full data payload from ConfigMaster.
                  Expected keys are 'instance_version', 'schema_definition', 'config_values'.
                  The handler will use parts of this payload based on the `mode`.
            mode: Specifies what to save. Accepts 'values' or 'full'.
                  If 'values' (default), saves only the current configuration key-value pairs.
                  The file structure depends on the handler (e.g., simple JSON dict).
                  If 'full', saves the instance version, schema definition, and values.
                  The file structure also depends on the handler but typically includes
                  distinct sections or keys for version, schema, and values.

        Raises:
            HandlerError: If saving, serialization, or file writing fails for reasons
                          specific to the handler or format.
            EncryptionError: If encryption fails (only applicable if initialized with Fernet).
            ValueError: If an unsupported `mode` is provided.

        """
        raise NotImplementedError("Subclasses must implement the save method.")

    def _encrypt(self, data_bytes: bytes) -> bytes:
        """
        Encrypts the provided bytes using the stored Fernet instance.

        Internal helper method for concrete handlers.

        Args:
            data_bytes: The plain bytes to encrypt.

        Returns:
            The encrypted bytes.

        Raises:
            RuntimeError: If called when no Fernet instance was provided during initialization.
            EncryptionError: If the encryption process fails.
        """
        if not self._fernet:
            # This should ideally not be reached if save logic is correct
            raise RuntimeError("Attempted to call _encrypt without a valid Fernet instance.")
        from ..exceptions import EncryptionError # Keep import local to avoid circularity at top level
        try:
            # We assume self._fernet is a valid Fernet instance if not None
            return self._fernet.encrypt(data_bytes)
        except Exception as e:
            raise EncryptionError(f"Handler encryption failed: {e}") from e

    def _decrypt(self, encrypted_bytes: bytes) -> bytes:
        """
        Decrypts the provided bytes using the stored Fernet instance.

        Internal helper method for concrete handlers.

        Args:
            encrypted_bytes: The encrypted bytes read from the file.

        Returns:
            The original plain bytes.

        Raises:
            RuntimeError: If called when no Fernet instance was provided during initialization.
            EncryptionError: If the decryption process fails (e.g., invalid token, wrong key).
        """
        if not self._fernet:
            # This should ideally not be reached if load logic is correct
            raise RuntimeError("Attempted to call _decrypt without a valid Fernet instance.")
        from ..exceptions import EncryptionError # Keep import local
        try:
            # We assume self._fernet is a valid Fernet instance if not None
            return self._fernet.decrypt(encrypted_bytes)
        except Exception as e:
            # Catch specific Fernet errors like InvalidToken if desired, or general Exception
            raise EncryptionError(f"Handler decryption failed: {e}") from e