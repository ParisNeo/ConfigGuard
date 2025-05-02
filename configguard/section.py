# Project: ConfigGuard
# File: configguard/section.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Updated for dynamic key handling in empty schemas)
# Description: Defines the ConfigSection class used to represent nested configuration structures within ConfigGuard.

import typing
from collections.abc import MutableMapping

# Import ConfigSetting dynamically only if needed for type checking or isinstance,
# to potentially alleviate import cycles during runtime if they become an issue.
# However, for method signatures and isinstance checks, direct import is usually fine if structure is correct.
from .setting import ConfigSetting
from .exceptions import SettingNotFoundError, ValidationError, SchemaError
from .log import log

# Forward declarations for type hinting to avoid circular imports
if typing.TYPE_CHECKING:
    from .config import ConfigGuard
    # Remove ConfigSetting from here if imported directly above
    # from .setting import ConfigSetting


class ConfigSection(MutableMapping):
    """
    Represents a nested section within a ConfigGuard configuration.

    Acts as a container for settings (ConfigSetting) and potentially further
    nested sections (ConfigSection), providing attribute and dictionary-style access.

    If initialized with an empty schema definition ({}), it allows adding/removing
    arbitrary key-value pairs directly, bypassing schema validation for those items.
    """
    # --- START DYNAMIC SECTION CHANGES ---
    # Add a flag to easily check if this section allows dynamic keys
    _is_dynamic: bool = False
    # --- END DYNAMIC SECTION CHANGES ---

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
                               An empty dictionary ({}) signifies a dynamic section where
                               arbitrary keys can be added.
            parent: The parent ConfigGuard instance or ConfigSection containing this section.
        """
        self._name = name
        self._schema_definition = schema_definition
        self._parent = parent
        # Holds ConfigSetting, nested ConfigSection objects, OR raw values for dynamic sections
        self._settings: typing.Dict[
            str, typing.Union[ConfigSetting, ConfigSection, typing.Any] # Allow Any for dynamic
        ] = {}
        # --- START DYNAMIC SECTION CHANGES ---
        self._is_dynamic = not bool(schema_definition) # Set flag if schema is empty
        if self._is_dynamic:
             log.debug(f"Initialized ConfigSection '{name}' as DYNAMIC (empty schema).")
        else:
             log.debug(f"Initialized ConfigSection '{name}' with defined schema (parent: {type(parent).__name__}).")
        # --- END DYNAMIC SECTION CHANGES ---
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
        """
        Returns the current configuration values within this section as a nested dictionary.
        Includes dynamically added key-value pairs if the section is dynamic.
        """
        config_dict = {}
        for name, item in self._settings.items():
            if isinstance(item, ConfigSetting):
                config_dict[name] = item.value
            elif isinstance(item, ConfigSection):
                # Recursively get the dictionary for the nested section
                config_dict[name] = item.get_config_dict()
            # --- START DYNAMIC SECTION CHANGES ---
            elif self._is_dynamic:
                # If it's dynamic and not a Setting/Section, it must be a raw value
                config_dict[name] = item
            # --- END DYNAMIC SECTION CHANGES ---
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
        """Allows accessing settings/subsections/dynamic values like attributes (e.g., section.setting)."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        is_schema_access = name.startswith("sc_")
        actual_name = name[3:] if is_schema_access else name

        if actual_name in self._settings:
            item = self._settings[actual_name]
            if is_schema_access:
                if isinstance(item, ConfigSetting):
                    return item.schema
                elif isinstance(item, ConfigSection):
                    return item.get_schema_dict()
                # --- START DYNAMIC SECTION CHANGES ---
                elif self._is_dynamic:
                    # No schema for dynamically added items
                     raise AttributeError(f"Section '{self._name}' is dynamic; no schema defined for key '{actual_name}'.")
                else: # Should not happen if internal state is consistent
                     raise AttributeError(f"Cannot access schema for unexpected item type '{type(item).__name__}' in section '{self._name}'.")
                # --- END DYNAMIC SECTION CHANGES ---
            elif isinstance(item, (ConfigSetting, ConfigSection)):
                # Return value for setting, or section object itself
                 return item.value if isinstance(item, ConfigSetting) else item
            # --- START DYNAMIC SECTION CHANGES ---
            elif self._is_dynamic:
                 # Return the raw dynamically added value
                 return item
            else: # Should not happen
                 raise AttributeError(f"Unexpected item type '{type(item).__name__}' found for key '{actual_name}' in section '{self._name}'.")
            # --- END DYNAMIC SECTION CHANGES ---
        else:
            prefix = "schema attribute" if is_schema_access else "attribute or setting/subsection/key"
            raise AttributeError(
                f"'{type(self).__name__}' (section '{self._name}') object has no {prefix} '{name}'"
            )

    def __setattr__(self, name: str, value: typing.Any) -> None:
        """
        Allows setting nested settings or dynamic values like attributes.
        Raises AttributeError if trying to set an unknown key in a non-dynamic section,
        or trying to overwrite a section.
        """
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        if name.startswith("sc_"):
            raise AttributeError("Cannot set schema attributes directly.")

        # Handle existing ConfigSettings
        if name in self._settings and isinstance(self._settings[name], ConfigSetting):
            setting = self._settings[name]
            try:
                setting.value = value # Validation handled by ConfigSetting
            except ValidationError as e:
                raise e
        # Handle attempt to overwrite a ConfigSection
        elif name in self._settings and isinstance(self._settings[name], ConfigSection):
            raise AttributeError(f"Cannot assign directly to subsection '{name}'. Modify settings within it.")
        # --- START DYNAMIC SECTION CHANGES ---
        # Handle adding/updating in a dynamic section
        elif self._is_dynamic:
             # Allow setting any attribute not starting with '_'
             log.debug(f"Dynamically setting '{self.name}.{name}' = {value!r}")
             self._settings[name] = value # Store raw value
             self._trigger_autosave(name) # Trigger autosave
        # Handle trying to set an unknown key in a non-dynamic section
        elif name not in self._settings:
             raise AttributeError(
                f"Cannot set attribute '{name}'. It's not a defined setting within non-dynamic section '{self._name}'."
            )
        # Handle existing dynamic raw value (should be covered by _is_dynamic case above)
        # else: # Should only be hit if name exists, schema is not dynamic, and it's not Setting/Section (error state?)
        #    log.error(f"Internal state error: Attempting to set unexpected item '{name}' in section '{self.name}'")
        #    raise AttributeError(f"Cannot set unexpected attribute '{name}' in section '{self.name}'.")
        # --- END DYNAMIC SECTION CHANGES ---


    def __getitem__(self, key: str) -> typing.Any:
        """
        Allows accessing settings/subsections/dynamic values like dictionary items.
        """
        is_schema_access = key.startswith("sc_")
        actual_key = key[3:] if is_schema_access else key

        if actual_key in self._settings:
            item = self._settings[actual_key]
            if is_schema_access:
                if isinstance(item, ConfigSetting):
                    return item.schema
                elif isinstance(item, ConfigSection):
                    return item.get_schema_dict()
                # --- START DYNAMIC SECTION CHANGES ---
                elif self._is_dynamic:
                     raise KeyError(f"Section '{self._name}' is dynamic; no schema defined for key '{actual_key}'.")
                else:
                     raise KeyError(f"Cannot access schema for unexpected item type '{type(item).__name__}' in section '{self._name}'.")
                # --- END DYNAMIC SECTION CHANGES ---
            elif isinstance(item, (ConfigSetting, ConfigSection)):
                 return item.value if isinstance(item, ConfigSetting) else item
            # --- START DYNAMIC SECTION CHANGES ---
            elif self._is_dynamic:
                 return item # Return raw dynamic value
            else:
                 raise KeyError(f"Unexpected item type '{type(item).__name__}' found for key '{actual_key}' in section '{self._name}'.")
            # --- END DYNAMIC SECTION CHANGES ---
        else:
            prefix = "Schema for setting/subsection/key" if is_schema_access else "Setting or subsection or key"
            raise SettingNotFoundError(f"{prefix} '{actual_key}' not found in section '{self._name}'.") # Keep specific error

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """
        Allows setting nested settings or dynamic values like dictionary items.
        Raises KeyError if trying to set an unknown key in a non-dynamic section.
        Raises TypeError if trying to overwrite a section.
        """
        if key.startswith("sc_"):
            raise KeyError("Cannot set schema items directly.")

        if key in self._settings:
            item = self._settings[key]
            if isinstance(item, ConfigSetting):
                try:
                    item.value = value # Validation handled by ConfigSetting
                except ValidationError as e:
                    raise e
            elif isinstance(item, ConfigSection):
                raise TypeError(f"Cannot assign directly to subsection '{key}'. Modify settings within it.")
            # --- START DYNAMIC SECTION CHANGES ---
            elif self._is_dynamic:
                 # Allow updating existing dynamic value
                 log.debug(f"Dynamically updating '{self.name}['{key}']' = {value!r}")
                 self._settings[key] = value
                 self._trigger_autosave(key)
            else: # Should not happen
                 raise TypeError(f"Cannot set unexpected existing item '{key}' of type {type(item).__name__}")
            # --- END DYNAMIC SECTION CHANGES ---
        # --- START DYNAMIC SECTION CHANGES ---
        # Key does not exist, check if section is dynamic
        elif self._is_dynamic:
             log.debug(f"Dynamically adding '{self.name}['{key}']' = {value!r}")
             self._settings[key] = value # Add new raw value
             self._trigger_autosave(key)
        # Key does not exist, and section is NOT dynamic
        else:
            raise SettingNotFoundError(
                f"Setting '{key}' not found in non-dynamic section '{self._name}'. Cannot set undefined settings."
            )
        # --- END DYNAMIC SECTION CHANGES ---

    # --- MutableMapping required methods ---

    def __delitem__(self, key: str) -> None:
        """
        Deletes a key from the section.
        Only allowed for dynamically added keys in a dynamic section.
        Raises TypeError for schema-defined settings/sections.
        Raises KeyError if the key doesn't exist.
        """
        if key not in self._settings:
            raise KeyError(f"Key '{key}' not found in section '{self._name}'.")

        item = self._settings[key]

        # --- START DYNAMIC SECTION CHANGES ---
        if self._is_dynamic and not isinstance(item, (ConfigSetting, ConfigSection)):
            # Allow deletion of dynamically added raw values
            log.debug(f"Dynamically deleting '{self.name}['{key}']'")
            del self._settings[key]
            self._trigger_autosave(key) # Trigger autosave on deletion
        elif isinstance(item, (ConfigSetting, ConfigSection)):
             # Prevent deletion of items defined by the schema (even if schema is dynamic, these were likely added specially)
             raise TypeError(f"Deleting schema-defined settings or sections ('{key}') is not supported.")
        else:
             # Trying to delete something unexpected in a non-dynamic section
             raise TypeError(f"Cannot delete unexpected item '{key}' of type {type(item).__name__}.")
        # --- END DYNAMIC SECTION CHANGES ---


    def __iter__(self) -> typing.Iterator[str]:
        """Iterates over the names of the defined settings, subsections, and dynamic keys."""
        return iter(self._settings.keys())

    def __len__(self) -> int:
        """Returns the number of defined settings, subsections, and dynamic keys."""
        return len(self._settings)

    def __contains__(self, key: object) -> bool:
        """Checks if a setting, subsection, or dynamic key name exists."""
        return isinstance(key, str) and key in self._settings

    def __repr__(self) -> str:
        """Returns a developer-friendly representation of the ConfigSection."""
        num_items = len(self._settings)
        child_keys = list(self._settings.keys())
        # Dynamically import ConfigSetting to avoid runtime circular import issues if needed
        # (Not strictly necessary here as type checking handles it, but safer pattern)
        # from .setting import ConfigSetting

        item_types = {"settings": 0, "sections": 0, "dynamic": 0}
        for item in self._settings.values():
            # Check type dynamically if necessary, but isinstance should work with forward refs
            if isinstance(item, ConfigSetting):
                item_types["settings"] += 1
            elif isinstance(item, ConfigSection):
                item_types["sections"] += 1
            # --- START DYNAMIC SECTION CHANGES ---
            elif self._is_dynamic:
                item_types["dynamic"] += 1
            # --- END DYNAMIC SECTION CHANGES ---

        dynamic_str = f", dynamic={item_types['dynamic']}" if self._is_dynamic else ""
        return (
            f"<ConfigSection(name='{self._name}', parent='{type(self._parent).__name__}', "
            f"items={num_items} (settings={item_types['settings']}, sections={item_types['sections']}{dynamic_str}), "
            f"dynamic={self._is_dynamic}, keys={child_keys})>"
        )