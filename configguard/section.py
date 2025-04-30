# Project: ConfigGuard
# File: configguard/section.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01
# Description: Defines the ConfigSection class used to represent nested configuration structures within ConfigGuard.

import typing
from collections.abc import MutableMapping

from .exceptions import SettingNotFoundError, ValidationError
from .log import log

# Forward declarations for type hinting to avoid circular imports
if typing.TYPE_CHECKING:
    from .config import ConfigGuard
    from .setting import ConfigSetting


class ConfigSection(MutableMapping):
    """
    Represents a nested section within a ConfigGuard configuration.

    Acts as a container for settings (ConfigSetting) and potentially further
    nested sections (ConfigSection), providing attribute and dictionary-style access.
    """

    def __init__(
        self,
        name: str,
        schema_definition: dict,
        parent: typing.Union["ConfigGuard", "ConfigSection"],
    ) -> None:
        """
        Initializes a ConfigSection.

        Args:
            name: The name of this section.
            schema_definition: The dictionary defining the schema for items within this section.
            parent: The parent ConfigGuard instance or ConfigSection containing this section.
        """
        self._name = name
        self._schema_definition = (
            schema_definition  # Schema for *contents* of this section
        )
        self._parent = parent
        # Holds ConfigSetting or nested ConfigSection objects
        self._settings: typing.Dict[
            str, typing.Union[ConfigSetting, ConfigSection]
        ] = {}
        log.debug(
            f"Initialized ConfigSection '{name}' (parent: {type(parent).__name__})."
        )
        # Note: Population of self._settings happens via ConfigGuard._build_internal_structure_from_schema

    @property
    def name(self) -> str:
        """The name of this configuration section."""
        return self._name

    def get_schema_dict(self) -> dict:
        """Returns the schema definition dictionary for the contents of this section."""
        # Return a copy to prevent external modification
        return self._schema_definition.copy()

    def get_config_dict(self) -> dict:
        """Returns the current configuration values within this section as a nested dictionary."""
        config_dict = {}
        for name, item in self._settings.items():
            if isinstance(item, ConfigSetting):
                config_dict[name] = item.value
            elif isinstance(item, ConfigSection):
                # Recursively get the dictionary for the nested section
                config_dict[name] = item.get_config_dict()
        return config_dict

    def _trigger_autosave(self, setting_name: str) -> None:
        """Propagates the autosave trigger up to the parent."""
        # Construct the full path for logging/context if needed
        full_setting_name = f"{self._name}.{setting_name}"  # Basic path construction
        log.debug(
            f"ConfigSection '{self._name}' propagating autosave for '{setting_name}'"
        )
        # Delegate to the parent's trigger method
        self._parent._trigger_autosave(full_setting_name)

    # --- Magic methods for access ---

    def __getattr__(self, name: str) -> typing.Any:
        """Allows accessing settings/subsections like attributes (e.g., section.setting)."""
        if name.startswith("_"):  # Allow internal attribute access
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )  # Consistent with standard behavior

        is_schema_access = name.startswith("sc_")
        actual_name = name[3:] if is_schema_access else name

        if actual_name in self._settings:
            item = self._settings[actual_name]
            if is_schema_access:
                if isinstance(item, ConfigSetting):
                    return item.schema
                elif isinstance(item, ConfigSection):
                    # Return the section's schema definition dictionary
                    return item.get_schema_dict()
            elif isinstance(item, ConfigSetting):
                return item.value
            elif isinstance(item, ConfigSection):
                # Return the nested section object itself
                return item
        else:
            prefix = (
                "schema attribute"
                if is_schema_access
                else "attribute or setting/subsection"
            )
            raise AttributeError(
                f"'{type(self).__name__}' (section '{self._name}') object has no {prefix} '{name}'"
            )

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """Allows setting nested settings like attributes (e.g., section.setting = value)."""
        # Handle internal attributes prefixed with '_'
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        # Prevent setting schema attributes directly
        if name.startswith("sc_"):
            raise AttributeError(
                "Cannot set schema attributes directly (use 'section.sc_name' to access)."
            )

        # Handle setting ConfigSettings within the section
        if name in self._settings and isinstance(self._settings[name], ConfigSetting):
            setting = self._settings[name]
            try:
                # Delegate to ConfigSetting's setter (handles validation, coercion, autosave trigger via parent ref)
                setting.value = value
            except ValidationError as e:
                raise e  # Propagate validation errors
        # Handle attempting to set a ConfigSection via attribute (Disallow direct assignment)
        elif name in self._settings and isinstance(self._settings[name], ConfigSection):
            raise AttributeError(
                f"Cannot assign directly to subsection '{name}'. Modify settings within the subsection (e.g., section.{name}.setting = value)."
            )
        else:
            # Block setting arbitrary attributes not defined in the section's schema
            raise AttributeError(
                f"Cannot set attribute '{name}'. It's not a defined setting within section '{self._name}'."
            )

    def __getitem__(self, key: str) -> typing.Any:
        """Allows accessing settings/subsections like dictionary items (e.g., section['setting'])."""
        is_schema_access = key.startswith("sc_")
        actual_key = key[3:] if is_schema_access else key

        if actual_key in self._settings:
            item = self._settings[actual_key]
            if is_schema_access:
                if isinstance(item, ConfigSetting):
                    return item.schema
                elif isinstance(item, ConfigSection):
                    return item.get_schema_dict()  # Return schema dict for subsection
            elif isinstance(item, ConfigSetting):
                return item.value
            elif isinstance(item, ConfigSection):
                # Return the subsection object itself
                return item
        else:
            prefix = (
                "Schema for setting/subsection"
                if is_schema_access
                else "Setting or subsection"
            )
            raise SettingNotFoundError(
                f"{prefix} '{actual_key}' not found in section '{self._name}'."
            )

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """Allows setting nested settings like dictionary items (e.g., section['setting'] = value)."""
        if key.startswith("sc_"):
            raise KeyError(
                "Cannot set schema items directly (use section['sc_name'] to access)."
            )

        if key in self._settings:
            item = self._settings[key]
            if isinstance(item, ConfigSetting):
                try:
                    # Delegate to ConfigSetting's setter (handles validation, coercion, autosave trigger via parent ref)
                    item.value = value
                except ValidationError as e:
                    raise e  # Propagate validation errors
            elif isinstance(item, ConfigSection):
                raise TypeError(
                    f"Cannot assign directly to subsection '{key}'. Modify settings within the subsection (e.g., section['{key}']['setting'] = value)."
                )
        else:
            raise SettingNotFoundError(
                f"Setting '{key}' not found in section '{self._name}'. Cannot set undefined settings."
            )

    # --- MutableMapping required methods ---

    def __delitem__(self, key: str) -> None:
        """Prevent deleting settings or subsections."""
        raise TypeError("Deleting configuration settings or sections is not supported.")

    def __iter__(self) -> typing.Iterator[str]:
        """Iterates over the names of the defined settings and subsections within this section."""
        return iter(self._settings.keys())

    def __len__(self) -> int:
        """Returns the number of defined settings and subsections within this section."""
        return len(self._settings)

    def __contains__(self, key: object) -> bool:
        """Checks if a setting or subsection name exists directly within this section."""
        return isinstance(key, str) and key in self._settings

    def __repr__(self) -> str:
        """Returns a developer-friendly representation of the ConfigSection."""
        num_items = len(self._settings)
        child_keys = list(self._settings.keys())
        # Dynamically import ConfigSetting to avoid runtime circular import issues if needed
        # (Not strictly necessary here as type checking handles it, but safer pattern)
        # from .setting import ConfigSetting

        item_types = {"settings": 0, "sections": 0}
        for item in self._settings.values():
            # Check type dynamically if necessary, but isinstance should work with forward refs
            if isinstance(item, ConfigSetting):
                item_types["settings"] += 1
            elif isinstance(item, ConfigSection):
                item_types["sections"] += 1

        return (
            f"<ConfigSection(name='{self._name}', parent='{type(self._parent).__name__}', "
            f"items={num_items} (settings={item_types['settings']}, sections={item_types['sections']}), "
            f"keys={child_keys})>"
        )


# Make ConfigSetting available for type checking within this module
# This helps resolve the forward reference used above.
from .setting import ConfigSetting
