# configmaster/log.py
import ascii_colors as logging
import os
import logging as std_logging # Import standard logging for level parsing

# Basic configuration, can be overridden by the application using ConfigMaster
# Let's apply the initial level setting more carefully.
# Avoid calling basicConfig here, let the application potentially call it,
# or rely on the default ascii_colors setup.
# We will just set the level on the root logger.
initial_log_level_name = os.environ.get("CONFIGMASTER_LOG_LEVEL", "INFO").upper()
initial_numeric_level = std_logging.getLevelName(initial_log_level_name)
if not isinstance(initial_numeric_level, int):
    initial_numeric_level = std_logging.INFO # Default to INFO if env var is invalid
    print(f"[ConfigMaster Init Warning] Invalid CONFIGMASTER_LOG_LEVEL '{initial_log_level_name}'. Defaulting to INFO.", file=sys.stderr)


# Get the logger instance for the library AFTER setting the initial level
log = logging.getLogger("ConfigMaster")
# Set the initial level on the root logger ascii_colors uses
logging.getLogger().setLevel(initial_numeric_level)
# Configure a basic handler if none exist, using ascii_colors defaults
if not logging.getLogger().hasHandlers():
     # Let ascii_colors handle its default setup if needed, or add a simple handler.
     # This ensures logs are visible even if the user doesn't configure logging.
     logging.basicConfig(level=initial_numeric_level, format='%(asctime)s %(levelname)s %(name)s: %(message)s')


def set_log_level(level: str):
    """Sets the logging level for the ConfigMaster library root logger."""
    level_upper = level.upper()
    numeric_level = std_logging.getLevelName(level_upper) # Get numeric level (e.g., 10 for DEBUG)

    if not isinstance(numeric_level, int):
        log.error(f"Invalid log level specified: {level}")
        return # Don't proceed if level name is invalid

    try:
        # Set level on the root logger managed by ascii_colors
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Log the change *after* the level might have been lowered
        current_level_name = std_logging.getLevelName(root_logger.getEffectiveLevel())
        log.info(f"ConfigMaster log level set attempt: {level_upper}. Effective root logger level: {current_level_name}")

    except Exception as e: # Catch broader exceptions during level setting
        log.error(f"Error setting log level to {level_upper}: {e}")