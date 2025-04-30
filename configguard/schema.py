# configguard/schema.py
import typing

from .exceptions import SchemaError, ValidationError
from .log import log

SUPPORTED_TYPES = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    # Add more complex types later if needed, e.g., dict
}


class SettingSchema:
    """Represents the schema definition for a single configuration setting."""

    def __init__(self, name: str, definition: dict):
        """
        Initializes the SettingSchema.

        Args:
            name: The name of the setting.
            definition: A dictionary defining the schema for this setting.
                        Expected keys: 'type', 'help'.
                        Optional keys: 'default', 'nullable', 'min_val', 'max_val', 'options'.
        """
        self.name = name
        # Store the raw definition dictionary to check for explicit 'default' later
        self._raw_definition = definition
        log.debug(
            f"Initializing schema for setting '{name}' with definition: {definition}"
        )

        if not isinstance(definition, dict):
            raise SchemaError(f"Schema definition for '{name}' must be a dictionary.")

        # Type (Mandatory)
        type_str = definition.get("type")
        if not type_str or not isinstance(type_str, str):
            raise SchemaError(f"Schema for '{name}' must include a 'type' string.")
        if type_str not in SUPPORTED_TYPES:
            raise SchemaError(
                f"Unsupported type '{type_str}' for setting '{name}'. Supported types: {list(SUPPORTED_TYPES.keys())}"
            )
        self.type: typing.Type = SUPPORTED_TYPES[type_str]
        self.type_str: str = type_str

        # Nullable Flag (Optional)
        self.nullable: bool = definition.get("nullable", False)
        if not isinstance(self.nullable, bool):
            raise SchemaError(
                f"Schema 'nullable' flag for '{name}' must be a boolean (True or False)."
            )

        # Default Value (Conditionally Mandatory)
        if "default" in definition:
            self.default_value: typing.Any = definition["default"]
        elif self.nullable:
            # If nullable and no default specified, default is None
            self.default_value: typing.Any = None
            log.debug(
                f"Setting '{name}' is nullable and has no default specified. Defaulting to None."
            )
        else:
            # If not nullable and no default, raise error
            raise SchemaError(
                f"Schema for non-nullable setting '{name}' must include a 'default' value."
            )

        # Help Text (Mandatory)
        self.help: str = definition.get("help", "")
        if not self.help or not isinstance(self.help, str):
            log.warning(
                f"Schema for '{name}' should include a non-empty 'help' string for documentation."
            )
            self.help = "No help provided."  # Provide a default help string

        # Options (Optional, for specific types like str, int, float)
        self.options: typing.Optional[list] = definition.get("options")
        if self.options is not None:
            if not isinstance(self.options, list):
                raise SchemaError(f"Schema 'options' for '{name}' must be a list.")
            if not self.options:
                raise SchemaError(
                    f"Schema 'options' for '{name}' cannot be an empty list."
                )
            # Ensure options are valid for the type (check after default validation)
            # We'll validate options compatibility during default/value validation.

        # Min/Max Value (Optional, for numeric types int, float)
        self.min_val: typing.Optional[typing.Union[int, float]] = definition.get(
            "min_val"
        )
        self.max_val: typing.Optional[typing.Union[int, float]] = definition.get(
            "max_val"
        )

        if self.type not in [int, float]:
            if self.min_val is not None or self.max_val is not None:
                log.warning(
                    f"'min_val'/'max_val' are only applicable to int/float types. Ignored for '{name}' (type: {self.type_str})."
                )
                self.min_val = None
                self.max_val = None
        else:
            if self.min_val is not None and not isinstance(self.min_val, (int, float)):
                raise SchemaError(
                    f"'min_val' for numeric setting '{name}' must be a number (int or float)."
                )
            if self.max_val is not None and not isinstance(self.max_val, (int, float)):
                raise SchemaError(
                    f"'max_val' for numeric setting '{name}' must be a number (int or float)."
                )
            if (
                self.min_val is not None
                and self.max_val is not None
                and self.min_val > self.max_val
            ):
                raise SchemaError(
                    f"'min_val' ({self.min_val}) cannot be greater than 'max_val' ({self.max_val}) for setting '{name}'."
                )

        # Final validation of default value after setting constraints
        try:
            # Validate default *unless* it's None and nullable is True
            if not (self.nullable and self.default_value is None):
                self.validate(self.default_value)  # Validate first
                # Coerce default value if necessary *after* validation
                self.default_value = self._coerce_value(self.default_value)
            # else: Default is None and nullable is True, so it's valid and needs no coercion.

            # Now validate that options are compatible with the validated default
            if self.options is not None and self.default_value is not None:
                # Coerce options for comparison if needed (especially for bool)
                coerced_options = [self._coerce_value(opt) for opt in self.options]
                # Allow default None even if options are set, if nullable
                if not (self.nullable and self.default_value is None):
                    if self.default_value not in coerced_options:
                        raise SchemaError(
                            f"Default value '{self.default_value}' for setting '{name}' is not among the allowed options: {self.options}."
                        )

        except ValidationError as e:
            raise SchemaError(
                f"Default value '{self.default_value}' for setting '{name}' failed validation: {e}"
            )
        except SchemaError as e:  # Catch option validation error
            raise e

        log.debug(f"Schema initialized successfully for '{name}'.")

    def _coerce_value(self, value: typing.Any) -> typing.Any:
        """Attempts to coerce the value to the schema type, handling None if nullable."""
        if value is None:
            return None

        if self.type is bool:
            # Strict boolean coercion
            if isinstance(value, bool):
                return value  # Already a bool, no coercion needed
            if isinstance(value, str):
                val_lower = value.lower()
                if val_lower == "true":
                    return True
                if val_lower == "false":
                    return False
            # Allow 0/1 for bool type as well
            if isinstance(value, (int, float)):
                if value == 1:
                    return True
                if value == 0:
                    return False
            # If none of the above match, it's likely an invalid bool representation.
            # Let validation handle the type mismatch.
            # We return the original value here so validate can report the original type.
            log.debug(
                f"Could not strictly coerce '{value}' (type: {type(value).__name__}) to bool. Passing original value to validation."
            )
            return value  # Pass original value to validation

        # --- Rest of the _coerce_value method remains the same ---
        if self.type is list and isinstance(value, str):
            pass

        try:
            # Standard type conversion for non-bool types if type doesn't match
            if not isinstance(value, self.type):
                # Avoid converting if it's already the correct type or if target is list/dict (handle those separately if needed)
                if self.type not in [list, dict]:
                    log.debug(
                        f"Attempting standard coercion for {value} to {self.type_str}"
                    )
                    return self.type(value)
            return value  # Return original if already correct type or complex type
        except (ValueError, TypeError) as e:
            log.warning(
                f"Standard coercion failed for '{value}' to type {self.type_str}: {e}. Passing original value to validation."
            )
            # Let validation handle the error if coercion fails
            return value

    def validate(self, value: typing.Any):
        """
        Validates a value against the schema definition.

        Args:
            value: The value to validate.

        Raises:
            ValidationError: If the value is invalid according to the schema.
        """
        # 1. Nullability Check --- NEW ---
        if value is None:
            if self.nullable:
                log.debug(f"Allowing None for nullable setting '{self.name}'.")
                return  # Valid: None is allowed
            else:
                # Raise error if None is provided but not allowed
                raise ValidationError(
                    f"Value for setting '{self.name}' cannot be None (nullable is False)."
                )

        coerced_value = self._coerce_value(value)

        # 1. Type Check
        if not isinstance(coerced_value, self.type):
            # Special check for bool allowing 0/1 if type is int/float for bool field
            if not (
                self.type is bool
                and isinstance(coerced_value, (int, float))
                and coerced_value in [0, 1]
            ):
                raise ValidationError(
                    f"Value '{value}' for setting '{self.name}' must be of type '{self.type_str}', but got '{type(value).__name__}'."
                )

        # 2. Options Check
        if self.options is not None:
            # Handle bool string options
            if self.type is bool and isinstance(coerced_value, bool):
                allowed_options = [self._coerce_value(opt) for opt in self.options]
                if coerced_value not in allowed_options:
                    raise ValidationError(
                        f"Value '{value}' for setting '{self.name}' is not one of the allowed options: {self.options}."
                    )
            elif coerced_value not in self.options:
                raise ValidationError(
                    f"Value '{value}' for setting '{self.name}' is not one of the allowed options: {self.options}."
                )

        # 3. Min/Max Check (for numeric types)
        if self.type in [int, float]:
            if self.min_val is not None and coerced_value < self.min_val:
                raise ValidationError(
                    f"Value '{value}' for setting '{self.name}' is below the minimum allowed value of {self.min_val}."
                )
            if self.max_val is not None and coerced_value > self.max_val:
                raise ValidationError(
                    f"Value '{value}' for setting '{self.name}' is above the maximum allowed value of {self.max_val}."
                )

        # 4. List element type check (basic)
        if self.type is list:
            # Currently, we don't enforce element types within lists in the schema definition itself.
            # This could be added with a syntax like "type": "list[str]" or "element_type": "str"
            # For now, we just check if it's a list.
            pass

        log.debug(
            f"Validation successful for setting '{self.name}' with value '{value}'."
        )

    def to_dict(self) -> dict:
        """Returns a dictionary representation of the schema, suitable for JSON serialization."""
        schema_dict = {
            "type": self.type_str,
            # Add help and nullable flags
            "help": self.help,
            "nullable": self.nullable,
        }

        # Include default value in the schema output
        # - Always include if it was explicitly defined in the raw input
        # - Include if it's not None (covers non-nullable defaults)
        # - Include if it's None AND nullable is True (covers explicit null default or implicit null for nullable)
        if (
            "default" in self._raw_definition
            or self.default_value is not None
            or (self.default_value is None and self.nullable)
        ):
            schema_dict["default"] = self.default_value

        # Add other optional fields if they exist on the instance
        if self.options is not None:
            schema_dict["options"] = self.options
        if self.min_val is not None:
            schema_dict["min_val"] = self.min_val
        if self.max_val is not None:
            schema_dict["max_val"] = self.max_val

        return schema_dict

    def __repr__(self) -> str:
        return f"SettingSchema(name='{self.name}', type='{self.type_str}', default={self.default_value})"
