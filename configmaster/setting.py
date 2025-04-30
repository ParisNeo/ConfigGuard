# configmaster/setting.py
import typing
from .schema import SettingSchema
from .exceptions import ValidationError
from .log import log

class ConfigSetting:
    """Represents a single configuration setting, holding its schema and current value."""

    def __init__(self, schema: SettingSchema):
        """
        Initializes a ConfigSetting.

        Args:
            schema: The SettingSchema defining this setting.
        """
        if not isinstance(schema, SettingSchema):
            raise TypeError("schema must be an instance of SettingSchema")
        self._schema = schema
        # Initialize with the default value from the schema
        self._value = schema.default_value
        log.debug(f"Initialized ConfigSetting '{self.name}' with default value: {self._value}")

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
        Sets the value of the setting after validation.

        Args:
            new_value: The new value to set.

        Raises:
            ValidationError: If the new value fails schema validation.
        """
        log.debug(f"Attempting to set value for '{self.name}' to: {new_value} (type: {type(new_value).__name__})")
        try:
            # Validate before setting
            self._schema.validate(new_value)
            # Coerce the value after successful validation
            coerced_value = self._schema._coerce_value(new_value)
            self._value = coerced_value
            log.debug(f"Successfully set value for '{self.name}' to: {self._value}")
        except ValidationError as e:
            log.error(f"Validation failed for setting '{self.name}': {e}")
            raise e # Re-raise the validation error

    def to_dict(self) -> dict:
        """Returns a dictionary representation (schema + value), maybe useful but be careful."""
        # Usually, we want either the schema dict OR the value, not combined like this.
        # ConfigMaster will provide separate methods for schema and config values.
        return {
            "name": self.name,
            "value": self.value,
            "schema": self.schema.to_dict()
        }

    def __repr__(self) -> str:
        return f"ConfigSetting(name='{self.name}', value={self.value!r}, type='{self.schema.type_str}')"
