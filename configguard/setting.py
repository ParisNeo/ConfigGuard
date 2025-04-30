# Project: ConfigGuard
# File: configguard/setting.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Updated for nesting/autosave)
# Description: Represents a single configuration setting, holding its schema, current value, and parent reference.

import typing

from .exceptions import ValidationError
from .log import log
from .schema import SettingSchema

# Forward declarations for type hinting
if typing.TYPE_CHECKING:
    from .config import ConfigGuard
    from .section import ConfigSection


class ConfigSetting:
    """Represents a single configuration setting, holding its schema, current value, and parent reference."""

    def __init__(
        self,
        schema: SettingSchema,
        parent: typing.Optional[typing.Union["ConfigGuard", "ConfigSection"]] = None,
    ):
        """
        Initializes a ConfigSetting.

        Args:
            schema: The SettingSchema defining this setting.
            parent: A reference to the containing ConfigGuard or ConfigSection instance,
                    used primarily for triggering autosave. Defaults to None.
        """
        if not isinstance(schema, SettingSchema):
            raise TypeError("schema must be an instance of SettingSchema")
        self._schema = schema
        # Store the parent reference
        self._parent = parent
        # Initialize with the default value from the schema
        # We need to coerce the default value *before* assigning it here
        # to ensure the initial state is correct, but validation was already done
        # by SettingSchema during its own init.
        try:
            self._value = schema._coerce_value(schema.default_value)
        except Exception as e:
            # This should ideally not happen if SettingSchema validation passed
            log.error(
                f"Error coercing default value for '{self.name}' during init: {e}"
            )
            self._value = schema.default_value  # Fallback to uncoerced default

        log.debug(
            f"Initialized ConfigSetting '{self.name}' with default value: {self._value!r} (Parent: {type(parent).__name__ if parent else 'None'})"
        )

    @property
    def name(self) -> str:
        """The name of the setting."""
        return self._schema.name

    @property
    def schema(self) -> SettingSchema:
        """The schema definition for this setting."""
        return self._schema

    @property
    def value(self) -> typing.Any:
        """The current value of the setting."""
        return self._value

    @value.setter
    def value(self, new_value: typing.Any):
        """
        Sets the value of the setting after validation and coercion.

        Triggers autosave via the parent reference if the value changes successfully.

        Args:
            new_value: The new value to set.

        Raises:
            ValidationError: If the new value fails schema validation.
        """
        log.debug(
            f"Attempting to set value for '{self.name}' to: {new_value!r} (type: {type(new_value).__name__})"
        )
        try:
            # 1. Validate before setting
            self._schema.validate(new_value)
            # 2. Coerce the value after successful validation
            coerced_value = self._schema._coerce_value(new_value)

            # 3. Check if value actually changed before assigning and triggering autosave
            # Use simple comparison, handle potential type differences after coercion if needed
            # (e.g., comparing int 1 and float 1.0 might need care depending on desired behavior)
            # For now, direct comparison should work for most cases after coercion.
            if self._value != coerced_value:
                old_value = self._value
                self._value = coerced_value
                log.debug(
                    f"Successfully set value for '{self.name}' from {old_value!r} to: {self._value!r}"
                )
                # 4. Trigger autosave via parent *after* successful update
                if self._parent:
                    # Delegate the trigger call to the parent (ConfigGuard or ConfigSection)
                    self._parent._trigger_autosave(self.name)
            else:
                log.debug(
                    f"Value for '{self.name}' is already {coerced_value!r}. No change applied."
                )

        except ValidationError as e:
            log.error(f"Validation failed for setting '{self.name}': {e}")
            raise e  # Re-raise the validation error

    def to_dict(self) -> dict:
        """Returns a dictionary representation (schema + value), maybe useful but be careful."""
        # Usually, we want either the schema dict OR the value, not combined like this.
        # ConfigGuard will provide separate methods for schema and config values.
        return {"name": self.name, "value": self.value, "schema": self.schema.to_dict()}

    def __repr__(self) -> str:
        return f"ConfigSetting(name='{self.name}', value={self.value!r}, type='{self.schema.type_str}')"
