# examples/create_encrypted_db.py
import sys
from pathlib import Path
# Add parent dir to path if running from examples folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from configguard import ConfigGuard, generate_encryption_key

# Define paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "sample_schema.json"
DB_PATH = SCRIPT_DIR / "sample_config_encrypted.db"
KEY_PATH = SCRIPT_DIR / "sample_config.secret" # Store the key

# Ensure schema exists
if not SCHEMA_PATH.exists():
    print(f"Error: Schema file not found at {SCHEMA_PATH}")
    sys.exit(1)

# Generate and save key (or load if exists)
if KEY_PATH.exists():
    enc_key = KEY_PATH.read_bytes()
    print(f"Using existing encryption key from {KEY_PATH}")
else:
    enc_key = generate_encryption_key()
    KEY_PATH.write_bytes(enc_key)
    print(f"Generated and saved new encryption key to {KEY_PATH}")

# Data to save
config_data = {
    "general": {
        "app_name": "SecureApp",
        "debug_mode": False,
        "max_retries": 1
    },
    "ui_settings": {
        "theme": "light",
        "font_size": 9,
        "recent_files": ["/secure/path/file.enc"],
        "window_positions": {
            "secure_window": {"x": 0, "y": 0}
        }
    },
    "api_key": "a_very_secret_key_in_db_123!@#"
}

try:
    # Initialize ConfigGuard in memory first
    config = ConfigGuard(
        schema=SCHEMA_PATH,
        encryption_key=enc_key
        # No config_path initially
    )

    # Import the data
    config.import_config(config_data)

    # Save to the DB file path
    print(f"Saving encrypted data to {DB_PATH}...")
    config.save(filepath=DB_PATH, mode='values') # Save only values

    print(f"Successfully created encrypted database: {DB_PATH}")
    print(f"Use the key from {KEY_PATH} to load it in the GUI.")

except ImportError as e:
    print(f"Error: Missing dependency required for DB handler: {e}")
except Exception as e:
    print(f"An error occurred: {e}")