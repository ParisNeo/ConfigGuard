# -*- coding: utf-8 -*-
# Project: ConfigGuard
# File: examples/config_editor_app_qt5.py
# Author: ParisNeo with Gemini 2.5
# Date: 2025-05-01 (Added 'New Config', sample files support)
# Description: A basic MDI PyQt5 application to edit ConfigGuard configurations.
#              Includes sample schema and config files in the 'examples' directory.

import sys
import json
import typing
from pathlib import Path

# --- Setup ConfigGuard Import ---
try:
    import configguard
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import configguard

from configguard import (
    ConfigGuard, ConfigSection, ConfigSetting, SettingSchema,
    ValidationError, EncryptionError, HandlerError, SettingNotFoundError, SchemaError,
    generate_encryption_key, log, set_log_level
)
from packaging.version import parse as parse_version, InvalidVersion

# --- PyQt5 Imports ---
try:
    from PyQt5.QtWidgets import (
        QAction, QApplication, QMainWindow, QWidget, QVBoxLayout, QTreeWidget,
        QTreeWidgetItem, QStyledItemDelegate, QLineEdit, QComboBox,
        QFileDialog, QMessageBox, QMdiArea, QMdiSubWindow, QInputDialog,
        QPlainTextEdit, QDialog, QPushButton, QDialogButtonBox, QLabel,
        QSpinBox, QDoubleSpinBox, QHeaderView, QMenu
    )
    from PyQt5.QtGui import  QIcon, QColor, QBrush, QPalette, QFont
    from PyQt5.QtCore import Qt, pyqtSignal, QVariant, QModelIndex, QObject
except ImportError:
    print("PyQt5 is required for this example.")
    print("Please install it: pip install PyQt5")
    sys.exit(1)

# --- Logging Setup ---
set_log_level("INFO")

# --- Constants ---
COL_NAME = 0
COL_VALUE = 1
COL_TYPE = 2
COL_DEFAULT = 3
ITEM_ROLE = Qt.UserRole + 1

# --- Sample Files Location ---
EXAMPLES_DIR = Path(__file__).resolve().parent
SAMPLE_SCHEMA = EXAMPLES_DIR / "sample_schema.json"
SAMPLE_CONFIGS = [
    EXAMPLES_DIR / "sample_config_initial.json",
    EXAMPLES_DIR / "sample_config_modified.yaml",
    EXAMPLES_DIR / "sample_config_nested.toml",
    EXAMPLES_DIR / "sample_config_encrypted.db",
]
SAMPLE_KEY_FILE = EXAMPLES_DIR / "sample_config.secret"



# --- Custom Delegates for Editing ---
# (SettingDelegate class remains unchanged from previous version)
class SettingDelegate(QStyledItemDelegate):
    """ Custom delegate to provide appropriate editors for different setting types (PyQt5). """
    data_committed = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent: QWidget, option, index: QModelIndex) -> QWidget:
        if index.column() != COL_VALUE:
            return None # Only edit value column

        cg_item = index.data(ITEM_ROLE)
        if not cg_item or not isinstance(cg_item, ConfigSetting):
                 return None # Cannot edit sections or invalid data

        schema = cg_item.schema

        # Boolean editor
        if schema.type is bool:
            editor = QComboBox(parent)
            editor.addItems(["True", "False"])
            return editor

        # Options editor
        elif schema.options:
            editor = QComboBox(parent)
            str_options = [str(opt) if opt is not None else "" for opt in schema.options]
            editor.addItems(str_options)
            return editor

        # String, Int, Float, List editor (basic line edit for now)
        elif schema.type in (str, int, float, list):
            editor = QLineEdit(parent)
            # Provide placeholder text for lists
            if schema.type is list:
                editor.setPlaceholderText('Enter list as JSON array (e.g., ["a", 1]) or comma-separated')
            return editor

        return None

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        value = index.model().data(index, Qt.DisplayRole)
        if isinstance(editor, QComboBox):
            editor.setCurrentText(value)
        elif isinstance(editor, QLineEdit):
            editor.setText(value)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:
        cg_item = index.data(ITEM_ROLE)
        if not cg_item or not isinstance(cg_item, ConfigSetting):
            return

        schema = cg_item.schema
        original_value_str = index.model().data(index, Qt.DisplayRole)
        new_value_str = ""
        new_value: typing.Any = None

        # Get value from editor
        if isinstance(editor, QComboBox):
            new_value_str = editor.currentText()
        elif isinstance(editor, QLineEdit):
            new_value_str = editor.text()
        else:
            super().setModelData(editor, model, index)
            return

        # Attempt to coerce and validate
        try:
            if schema.type is bool:
                if new_value_str.lower() == "true": new_value = True
                elif new_value_str.lower() == "false": new_value = False
                else: raise ValueError("Invalid boolean string")
            elif schema.type is int: new_value = int(new_value_str)
            elif schema.type is float: new_value = float(new_value_str)
            elif schema.type is list:
                 # Try parsing as JSON first
                 try:
                     parsed_list = json.loads(new_value_str)
                     if isinstance(parsed_list, list):
                          new_value = parsed_list
                     else: # Valid JSON but not a list
                          raise ValueError("Input is valid JSON but not a list")
                 except json.JSONDecodeError:
                     # If not valid JSON, try comma-separated (basic split)
                     if new_value_str.strip():
                          new_value = [s.strip() for s in new_value_str.split(',')]
                     else: # Empty string becomes empty list
                          new_value = []
            else: # String or other types handled by ConfigSetting validation
                new_value = new_value_str

            cg_item.schema.validate(new_value)
            coerced_value = cg_item.schema._coerce_value(new_value)
            model.setData(index, str(coerced_value), Qt.DisplayRole) # Update display

            # Emit signal
            view = self.parent()
            if isinstance(view, QTreeWidget):
                item = view.itemFromIndex(index)
                if item:
                    self.data_committed.emit(item) # Emit the actual item

        except (ValidationError, ValueError, TypeError) as e:
            log.warning(f"Validation/Conversion Error: {e}")
            QMessageBox.warning(editor.parentWidget(), "Validation Error", f"Invalid value: {e}")
            # Do not update model data

    def updateEditorGeometry(self, editor: QWidget, option, index: QModelIndex) -> None:
        editor.setGeometry(option.rect)


# --- Configuration Editor Widget ---
class ConfigEditorWidget(QWidget):
    """ Widget holding the Tree view and managing a single ConfigGuard instance (PyQt5). """
    modification_changed = pyqtSignal(bool)

    def __init__(self, schema_path: Path, config_path: typing.Optional[Path] = None, encryption_key: typing.Optional[bytes] = None, instance_version: typing.Optional[str] = None, parent=None):
        super().__init__(parent)
        self.schema_path = schema_path
        self.config_path = config_path # Will be None for "New Config"
        self.encryption_key = encryption_key
        self.instance_version_override = instance_version
        self.config_guard: typing.Optional[ConfigGuard] = None
        self.is_modified = False # Start unmodified

        self.layout = QVBoxLayout(self)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(4)
        self.tree_widget.setHeaderLabels(["Name", "Value", "Type", "Default"])
        self.layout.addWidget(self.tree_widget)

        self.delegate = SettingDelegate(self.tree_widget)
        self.tree_widget.setItemDelegateForColumn(COL_VALUE, self.delegate)
        self.delegate.data_committed.connect(self.handle_data_committed)

        self.tree_widget.header().setStretchLastSection(False)
        self.tree_widget.header().setSectionResizeMode(COL_NAME, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(COL_VALUE, QHeaderView.Stretch)
        self.tree_widget.header().setSectionResizeMode(COL_TYPE, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(COL_DEFAULT, QHeaderView.ResizeToContents)
        self.tree_widget.header().resizeSection(COL_NAME, 200)
        self.tree_widget.header().resizeSection(COL_DEFAULT, 150)

        self.load_config()

    def load_config(self):
        """ Loads the schema and config file (if path provided) (PyQt5). """
        try:
            log.info(f"Editor loading schema from: {self.schema_path}")
            log.info(f"Editor using config path: {self.config_path}")
            log.info(f"Editor using instance version override: {self.instance_version_override}")
            log.info(f"Editor using encryption key: {'Yes' if self.encryption_key else 'No'}")

            # config_path=None will initialize with defaults based on schema
            self.config_guard = ConfigGuard(
                schema=self.schema_path,
                instance_version=self.instance_version_override,
                config_path=self.config_path, # Will be None for "New Config"
                encryption_key=self.encryption_key,
                autosave=False
            )
            log.info(f"Editor ConfigGuard instance created (Version: {self.config_guard.version}) for '{self.windowTitle()}'")
            self.populate_tree()
            # If config_path was None, this is a new config, mark as modified initially?
            # Let's consider it modified *only* when user changes something via delegate.
            # self.set_modified(self.config_path is None)
            self.set_modified(False)


        except FileNotFoundError as e:
             if self.config_path and self.config_path.exists():
                 # Config exists but schema might not - should be caught by main window
                 QMessageBox.critical(self, "Error", f"Schema file may be missing or inaccessible:\n{e}")
                 self.config_guard = None
             elif self.config_path:
                 # Config file specified but not found, proceed with defaults
                 log.warning(f"Config file '{self.config_path}' not found. Using defaults.")
                 # Need to re-init without config_path to get defaults
                 try:
                     self.config_guard = ConfigGuard(
                        schema=self.schema_path,
                        instance_version=self.instance_version_override,
                        config_path=None, # Initialize with defaults
                        encryption_key=self.encryption_key,
                        autosave=False
                     )
                     log.info(f"Re-initialized with defaults for {self.config_path}")
                     self.populate_tree()
                     self.set_modified(False) # Loaded defaults, not modified yet
                 except Exception as init_err:
                     QMessageBox.critical(self, "Error", f"Failed to initialize with defaults after file not found:\n{init_err}")
                     self.config_guard = None
             else:
                 # No config path provided, schema file not found (should be caught earlier)
                 QMessageBox.critical(self, "Error", f"Schema file not found:\n{e}")
                 self.config_guard = None

        except EncryptionError as e:
            log.error(f"Encryption error loading {self.config_path}: {e}")
            key_text, ok = QInputDialog.getText(self, "Encryption Key Needed",
                                                f"Enter encryption key (base64) for:\n{self.config_path}",
                                                QLineEdit.Password)
            if ok and key_text:
                try:
                    self.encryption_key = key_text.encode('utf-8')
                    self.config_guard = None # Reset
                    self.load_config() # Retry
                except Exception as key_err:
                     QMessageBox.critical(self, "Error", f"Invalid key or reload failed: {key_err}")
                     self.config_guard = None
            else:
                 QMessageBox.warning(self, "Load Cancelled", "Cannot load encrypted file.")
                 self.config_guard = None

        except (HandlerError, ValidationError, SchemaError, ImportError) as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load configuration:\n{e}")
            # If we failed loading the config file but schema was ok, show defaults
            if self.config_guard and self.config_path:
                 log.info("Falling back to default values due to load error.")
                 self.config_guard = None # Reset
                 try: # Re-init with defaults
                      self.config_guard = ConfigGuard(
                          schema=self.schema_path, instance_version=self.instance_version_override,
                          config_path=None, encryption_key=self.encryption_key, autosave=False
                      )
                      self.populate_tree()
                      self.set_modified(False)
                 except Exception as final_err:
                      QMessageBox.critical(self, "Fatal Error", f"Failed to initialize with defaults:\n{final_err}")
                      self.config_guard = None
            else: # Schema or other init error
                self.config_guard = None

        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred during load:\n{e}")
            log.exception("Unexpected error during load_config")
            self.config_guard = None

    def populate_tree(self):
        # (populate_tree logic remains unchanged)
        self.tree_widget.clear()
        if not self.config_guard:
            return

        def add_items(parent_item, config_node):
            if isinstance(config_node, ConfigGuard):
                container = config_node._settings
            elif isinstance(config_node, ConfigSection):
                container = config_node._settings
            else:
                return

            for name, item in container.items():
                if isinstance(item, ConfigSetting):
                    schema = item.schema
                    value_str = str(item.value) if item.value is not None else "None"
                    default_str = str(schema.default_value) if schema.default_value is not None else "None"
                    tree_item = QTreeWidgetItem(parent_item, [name, value_str, schema.type_str, default_str])
                    tree_item.setToolTip(COL_NAME, schema.help or "No help provided.")
                    tree_item.setToolTip(COL_VALUE, f"Current Value: {value_str}")
                    tree_item.setToolTip(COL_TYPE, f"Type: {schema.type_str}, Nullable: {schema.nullable}")
                    tree_item.setToolTip(COL_DEFAULT, f"Default: {default_str}")
                    tree_item.setData(COL_NAME, ITEM_ROLE, item)
                    tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

                elif isinstance(item, ConfigSection):
                    schema_dict = item.get_schema_dict()
                    help_text = schema_dict.get("help", "Section")
                    tree_item = QTreeWidgetItem(parent_item, [name, "", "section", ""])
                    tree_item.setToolTip(COL_NAME, help_text)
                    tree_item.setData(COL_NAME, ITEM_ROLE, item)
                    font = tree_item.font(COL_NAME)
                    font.setBold(True)
                    tree_item.setFont(COL_NAME, font)
                    tree_item.setForeground(COL_NAME, QBrush(QColor("navy")))
                    add_items(tree_item, item) # Recurse

        add_items(self.tree_widget, self.config_guard)
        self.tree_widget.expandAll()

    def handle_data_committed(self, item: QTreeWidgetItem):
        # (handle_data_committed logic remains unchanged)
        if not self.config_guard: return

        cg_item = item.data(COL_NAME, ITEM_ROLE)
        if isinstance(cg_item, ConfigSetting):
            new_value_str = item.text(COL_VALUE)
            schema = cg_item.schema
            try:
                parsed_value: typing.Any = None
                # Coercion logic (same as before)
                if schema.type is bool: parsed_value = new_value_str.lower() == "true"
                elif schema.type is int: parsed_value = int(new_value_str)
                elif schema.type is float: parsed_value = float(new_value_str)
                elif schema.type is list:
                    try:
                        parsed_value = json.loads(new_value_str)
                        if not isinstance(parsed_value, list): parsed_value = cg_item.value
                    except json.JSONDecodeError:
                         if new_value_str.strip(): parsed_value = [s.strip() for s in new_value_str.split(',')]
                         else: parsed_value = []
                else: parsed_value = new_value_str

                # Update ConfigGuard instance via parent
                parent_container = cg_item._parent
                if parent_container:
                    parent_container[cg_item.name] = parsed_value # Triggers validation
                    log.info(f"Updated ConfigGuard value for '{cg_item.name}' to {parsed_value!r}")
                    self.set_modified(True)
                else:
                    log.error(f"Cannot find parent container for setting '{cg_item.name}'.")

            except (ValidationError, ValueError, TypeError) as e:
                log.error(f"Error updating ConfigGuard instance for {cg_item.name}: {e}")
                item.setText(COL_VALUE, str(cg_item.value) if cg_item.value is not None else "None") # Revert display
            except Exception as e:
                 log.exception(f"Unexpected error updating ConfigGuard for {cg_item.name}")

    def save_config(self, save_path: typing.Optional[Path] = None) -> bool:
        # (save_config logic remains unchanged)
        if not self.config_guard:
            QMessageBox.warning(self, "Save Error", "No configuration loaded.")
            return False

        target_path = save_path or self.config_path
        if not target_path:
            log.error("Save failed: No target path specified.")
            QMessageBox.warning(self, "Save Error", "No file path specified. Use 'Save As'.")
            return False

        requires_encryption = target_path.suffix.lower() in ('.bin', '.enc')
        current_key = self.encryption_key

        if requires_encryption and not current_key:
             key_text, ok = QInputDialog.getText(self, "Encryption Key Needed",
                                                f"Saving to '{target_path.name}' requires encryption.\nEnter encryption key (base64):",
                                                QLineEdit.Password)
             if ok and key_text:
                 try:
                     current_key = key_text.encode('utf-8')
                     configguard.Fernet(current_key) # Test key validity
                     self.encryption_key = current_key
                 except Exception as key_err:
                      QMessageBox.critical(self, "Invalid Key", f"The provided key is invalid: {key_err}")
                      return False
             else:
                  QMessageBox.warning(self, "Save Cancelled", "Cannot save without encryption key.")
                  return False
        elif not requires_encryption and current_key:
             reply = QMessageBox.question(self, "Encryption Warning",
                                        f"The file '{target_path.name}' will be saved UNENCRYPTED.\nAn encryption key is currently loaded. Continue without encryption?",
                                        QMessageBox.Yes | QMessageBox.No)
             if reply == QMessageBox.No:
                 return False
             current_key = None

        try:
            handler = configguard.handlers.get_handler(target_path, fernet=current_key)
            log.info(f"Saving config to {target_path} using {type(handler).__name__} (mode=values)")

            payload = {
                "instance_version": self.config_guard.version,
                "schema_definition": self.config_guard.get_instance_schema_definition(),
                "config_values": self.config_guard.get_config_dict(),
            }
            handler.save(target_path, data=payload, mode="values")

            self.config_path = target_path # Update path after successful save
            self.set_modified(False)
            log.info(f"Configuration saved successfully to {target_path}")
            return True

        except (HandlerError, EncryptionError, ValidationError, SchemaError, ValueError, ImportError) as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")
            log.exception("Error during save_config")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Save Error", f"An unexpected error occurred:\n{e}")
            log.exception("Unexpected error during save_config")
            return False

    def set_modified(self, modified: bool):
        # (set_modified logic remains unchanged)
        if self.is_modified != modified:
            self.is_modified = modified
            self.modification_changed.emit(modified)

    def close_widget(self) -> bool:
        # (close_widget logic remains unchanged)
        if self.is_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "There are unsaved changes. Do you want to save before closing?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                parent = self.parent()
                while parent and not isinstance(parent, MainWindow):
                    parent = parent.parent()
                if isinstance(parent, MainWindow):
                    return parent.save_active_config()
                else:
                    log.error("Could not find MainWindow to trigger save from editor.")
                    return False
            elif reply == QMessageBox.Cancel:
                return False
        return True

# --- NEW: Schema Editor Widget ---
class SchemaEditorWidget(QWidget):
    """ Widget for creating and editing ConfigGuard Schema definitions (JSON structure). """
    modification_changed = pyqtSignal(bool)
    # Signal emitted when schema is saved, providing its path for potential use by value editors
    schema_saved = pyqtSignal(Path)

    # Define constants for schema tree columns
    SCH_COL_NAME = 0
    SCH_COL_PROP = 1
    SCH_COL_VALUE = 2

    def __init__(self, schema_path: typing.Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.schema_path = schema_path
        self.schema_data: typing.Dict[str, typing.Any] = {}
        self.is_modified = False

        self.layout = QVBoxLayout(self)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setHeaderLabels(["Name", "Property", "Value"])
        self.layout.addWidget(self.tree_widget)

        # Basic Delegate for Editing Property Values (simple strings for now)
        self.tree_widget.setItemDelegateForColumn(self.SCH_COL_VALUE, QStyledItemDelegate(self.tree_widget))
        self.tree_widget.itemChanged.connect(self.handle_item_changed) # Handle edits

        # Context Menu for Adding/Removing Items
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

        # Configure Tree View Appearance
        header = self.tree_widget.header()
        header.setSectionResizeMode(self.SCH_COL_NAME, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.SCH_COL_PROP, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.SCH_COL_VALUE, QHeaderView.Stretch)
        header.resizeSection(self.SCH_COL_NAME, 200)
        header.resizeSection(self.SCH_COL_PROP, 120)

        self.load_schema()

    def load_schema(self):
        """ Loads the schema definition from the path, or initializes an empty one. """
        self.tree_widget.clear()
        self.schema_data = {}
        try:
            if self.schema_path and self.schema_path.exists():
                log.info(f"SchemaEditor loading schema from: {self.schema_path}")
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    loaded_json = json.load(f)
                if not isinstance(loaded_json, dict):
                    raise TypeError("Schema file must contain a JSON object.")
                self.schema_data = loaded_json
                self.populate_tree()
                self.set_modified(False)
                self.schema_saved.emit(self.schema_path) # Emit signal on successful load
            else:
                log.info("SchemaEditor initialized with a new, empty schema.")
                # Initialize with mandatory version key
                self.schema_data = {"__version__": "1.0.0"}
                self.populate_tree()
                self.set_modified(True) # New schema starts modified
                # No path to emit yet

        except (json.JSONDecodeError, TypeError, OSError) as e:
            QMessageBox.critical(self, "Schema Load Error", f"Failed to load or parse schema file:\n{self.schema_path}\n\nError: {e}")
            self.schema_data = {"__version__": "1.0.0"} # Fallback to empty
            self.populate_tree()
            self.set_modified(True)
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Schema Load Error", f"An unexpected error occurred:\n{e}")
            log.exception("Unexpected error during schema load")
            self.schema_data = {"__version__": "1.0.0"}
            self.populate_tree()
            self.set_modified(True)

    def populate_tree(self):
        """ Populates the tree widget from the internal schema_data dictionary. """
        self.tree_widget.blockSignals(True) # Block itemChanged during population
        self.tree_widget.clear()

        def add_schema_node(parent_tree_item, name: str, definition: typing.Dict, schema_dict_ref: typing.Dict):
            """ Adds a setting or section node and its properties. """
            # Create main item for the setting/section name
            node_item = QTreeWidgetItem(parent_tree_item, [name, "", ""])
            node_item.setData(0, ITEM_ROLE, {"is_node": True, "name": name, "dict_ref": schema_dict_ref}) # Store ref to parent dict
            node_item.setFlags(node_item.flags() | Qt.ItemIsEditable) # Allow renaming

            font = node_item.font(self.SCH_COL_NAME)
            font.setBold(True)
            node_item.setFont(self.SCH_COL_NAME, font)

            # Add child items for each property (type, default, help, etc.)
            is_section = definition.get("type") == "section"
            if is_section:
                 node_item.setForeground(self.SCH_COL_NAME, QBrush(QColor("navy")))
            else:
                 node_item.setForeground(self.SCH_COL_NAME, QBrush(QColor("darkgreen")))


            for prop, value in definition.items():
                if prop == "schema" and is_section:
                    # Handle nested schema for sections
                    schema_prop_item = QTreeWidgetItem(node_item, ["", "schema", ""]) # Placeholder
                    schema_prop_item.setData(0, ITEM_ROLE, {"is_property": True, "node_name": name, "prop_name": prop, "dict_ref": definition})
                    schema_prop_item.setForeground(self.SCH_COL_PROP, QBrush(QColor("gray")))
                    # Recursively add items from the nested schema
                    if isinstance(value, dict):
                        for nested_name, nested_def in value.items():
                             if isinstance(nested_def, dict): # Check nested def is a dict
                                add_schema_node(schema_prop_item, nested_name, nested_def, value) # Pass nested schema dict as ref
                else:
                    # Simple property
                    value_str = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
                    prop_item = QTreeWidgetItem(node_item, ["", prop, value_str])
                    prop_item.setData(0, ITEM_ROLE, {"is_property": True, "node_name": name, "prop_name": prop, "dict_ref": definition}) # Store ref to definition dict
                    prop_item.setFlags(prop_item.flags() | Qt.ItemIsEditable) # Allow editing value
                    prop_item.setForeground(self.SCH_COL_PROP, QBrush(QColor("gray")))

        # Populate from root level of schema_data
        root_item = self.tree_widget.invisibleRootItem()
        for name, definition in self.schema_data.items():
             if isinstance(definition, dict): # Ensure definition is a dictionary
                 add_schema_node(root_item, name, definition, self.schema_data)
             elif name == "__version__": # Handle top-level version separately
                 version_item = QTreeWidgetItem(root_item, [name, "Property", str(definition)])
                 version_item.setData(0, ITEM_ROLE, {"is_property": True, "node_name": None, "prop_name": name, "dict_ref": self.schema_data})
                 version_item.setFlags(version_item.flags() | Qt.ItemIsEditable)
                 version_item.setForeground(self.SCH_COL_NAME, QBrush(QColor("purple")))


        self.tree_widget.expandAll()
        self.tree_widget.blockSignals(False)


    def handle_item_changed(self, item: QTreeWidgetItem, column: int):
        """ Update internal schema_data when tree item is edited. """
        item_data = item.data(0, ITEM_ROLE)
        if not item_data: return

        is_node = item_data.get("is_node", False)
        is_property = item_data.get("is_property", False)
        parent_dict_ref = item_data.get("dict_ref")

        if not parent_dict_ref:
            log.warning("Item data missing dictionary reference, cannot update schema.")
            return

        # --- Handle Renaming a Setting/Section Node ---
        if is_node and column == self.SCH_COL_NAME:
            old_name = item_data.get("name")
            new_name = item.text(self.SCH_COL_NAME)
            if old_name and new_name and old_name != new_name and old_name in parent_dict_ref:
                log.debug(f"Renaming node '{old_name}' to '{new_name}'")
                # Simple rename: Pop old key, insert with new key
                node_definition = parent_dict_ref.pop(old_name)
                parent_dict_ref[new_name] = node_definition
                # Update item data to reflect new name for future edits
                item_data["name"] = new_name
                item.setData(0, ITEM_ROLE, item_data)
                # Update child property references (important!)
                for i in range(item.childCount()):
                     child_item = item.child(i)
                     child_data = child_item.data(0, ITEM_ROLE)
                     if child_data and child_data.get("is_property"):
                          child_data["node_name"] = new_name
                          child_item.setData(0, ITEM_ROLE, child_data)
                     # Need recursive update if properties themselves have children (like 'schema')
                     if child_item.text(self.SCH_COL_PROP) == "schema":
                          for j in range(child_item.childCount()):
                              grandchild_item = child_item.child(j)
                              grandchild_data = grandchild_item.data(0, ITEM_ROLE)
                              if grandchild_data and grandchild_data.get("is_node"):
                                   # Update the 'dict_ref' of the nested node to point to the renamed parent's schema dict
                                   grandchild_data["dict_ref"] = node_definition.get("schema", {}) # Point to the actual schema dict


                self.set_modified(True)
            elif old_name != new_name: # Name change failed or key not found
                # Revert tree display if rename failed in data
                item.setText(self.SCH_COL_NAME, old_name)

        # --- Handle Editing a Property Value ---
        elif is_property and column == self.SCH_COL_VALUE:
            prop_name = item_data.get("prop_name")
            node_name = item_data.get("node_name") # Name of the parent setting/section
            new_value_str = item.text(self.SCH_COL_VALUE)

            if prop_name:
                log.debug(f"Updating property '{prop_name}' for node '{node_name or '__version__'}' to: {new_value_str}")
                try:
                    # Basic type guessing for common props (more robust parsing needed)
                    current_value = parent_dict_ref[prop_name]
                    new_value: typing.Any
                    if isinstance(current_value, bool) or prop_name == "nullable":
                        new_value = new_value_str.lower() == 'true'
                    elif isinstance(current_value, int) and prop_name not in ["type", "help", "default"]: # Avoid converting type/help/default strings to int
                        new_value = int(new_value_str)
                    elif isinstance(current_value, float) and prop_name not in ["type", "help", "default"]:
                        new_value = float(new_value_str)
                    elif isinstance(current_value, list) or prop_name == "options":
                        try: new_value = json.loads(new_value_str)
                        except json.JSONDecodeError: new_value = [s.strip() for s in new_value_str.split(',')] if new_value_str else []
                        if not isinstance(new_value, list): raise ValueError("Invalid list format")
                    else: # Default to string
                        new_value = new_value_str

                    # Update the dictionary reference
                    parent_dict_ref[prop_name] = new_value
                    self.set_modified(True)
                    # Re-set text in case JSON dump/str conversion differs slightly
                    value_disp_str = json.dumps(new_value) if isinstance(new_value, (list, dict)) else str(new_value)
                    item.setText(self.SCH_COL_VALUE, value_disp_str)

                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    log.warning(f"Failed to parse value for '{prop_name}': {e}. Reverting.")
                    # Revert tree display
                    old_value = parent_dict_ref.get(prop_name)
                    old_value_str = json.dumps(old_value) if isinstance(old_value, (list, dict)) else str(old_value)
                    item.setText(self.SCH_COL_VALUE, old_value_str)
                except Exception as e:
                     log.exception(f"Unexpected error updating property {prop_name}")


    def show_context_menu(self, position):
        """ Show context menu for adding/removing schema items. """
        menu = QMenu()
        selected_item = self.tree_widget.currentItem()

        target_item = selected_item or self.tree_widget.invisibleRootItem()
        item_data = selected_item.data(0, ITEM_ROLE) if selected_item else None

        # Determine where we can add items
        can_add_here = False
        target_dict_ref = None
        parent_node_item = None

        if not selected_item: # Right-click on empty space
            can_add_here = True
            target_dict_ref = self.schema_data # Add to root
            parent_node_item = self.tree_widget.invisibleRootItem()
        elif item_data:
            if item_data.get("is_node") and item_data.get("dict_ref").get(item_data.get("name"), {}).get("type") == "section":
                # Right-click on a section node - add inside its 'schema' dict
                section_name = item_data.get("name")
                parent_dict = item_data.get("dict_ref")
                if section_name and parent_dict and section_name in parent_dict:
                     section_def = parent_dict[section_name]
                     if "schema" not in section_def or not isinstance(section_def["schema"], dict):
                          section_def["schema"] = {} # Ensure schema dict exists
                     target_dict_ref = section_def["schema"]
                     can_add_here = True
                     parent_node_item = selected_item # Add visually under the section node
                     # Find the 'schema' property item to add children under visually
                     for i in range(selected_item.childCount()):
                         child = selected_item.child(i)
                         if child.text(self.SCH_COL_PROP) == "schema":
                             parent_node_item = child
                             break

            elif item_data.get("is_property") and item_data.get("prop_name") == "schema":
                 # Right-click on the 'schema' property of a section
                 section_def_ref = item_data.get("dict_ref")
                 if section_def_ref and isinstance(section_def_ref.get("schema"), dict):
                      target_dict_ref = section_def_ref["schema"]
                      can_add_here = True
                      parent_node_item = selected_item # Add visually under the schema property


        if can_add_here and target_dict_ref is not None:
            add_setting_action = menu.addAction("Add New Setting...")
            add_setting_action.triggered.connect(lambda: self.add_schema_item(target_dict_ref, parent_node_item, "setting"))
            add_section_action = menu.addAction("Add New Section...")
            add_section_action.triggered.connect(lambda: self.add_schema_item(target_dict_ref, parent_node_item, "section"))

        # Option to remove the selected item (if it's a setting/section node)
        if selected_item and item_data and item_data.get("is_node"):
             if item_data.get("name") != "__version__": # Cannot remove version
                menu.addSeparator()
                remove_action = menu.addAction(f"Remove '{item_data.get('name')}'")
                remove_action.triggered.connect(lambda: self.remove_schema_item(selected_item))

        menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    def add_schema_item(self, target_dict: dict, parent_tree_item: QTreeWidgetItem, item_type: str):
        """ Adds a new setting or section to the schema data and tree. """
        name, ok = QInputDialog.getText(self, f"Add New {item_type.capitalize()}", f"Enter name for the new {item_type}:")
        if ok and name and name not in target_dict and name != "__version__":
            if item_type == "setting":
                new_def = {
                    "type": "str",
                    "default": "",
                    "help": "New setting description.",
                    "nullable": False
                }
            elif item_type == "section":
                new_def = {
                    "type": "section",
                    "help": "New section description.",
                    "schema": {}
                }
            else: return

            log.info(f"Adding new {item_type} '{name}' to schema.")
            target_dict[name] = new_def
            # Manually add tree item instead of full refresh for better performance
            self.populate_tree() # Easier to just refresh for now
            self.set_modified(True)
        elif ok and not name:
            QMessageBox.warning(self, "Invalid Name", "Name cannot be empty.")
        elif ok and name in target_dict:
             QMessageBox.warning(self, "Name Exists", f"An item named '{name}' already exists here.")
        elif ok and name == "__version__":
             QMessageBox.warning(self, "Invalid Name", "Cannot use reserved name '__version__'.")


    def remove_schema_item(self, item: QTreeWidgetItem):
        """ Removes a setting or section from the schema data and tree. """
        item_data = item.data(0, ITEM_ROLE)
        if not item_data or not item_data.get("is_node"): return

        name = item_data.get("name")
        parent_dict_ref = item_data.get("dict_ref")

        if name and parent_dict_ref and name in parent_dict_ref:
             reply = QMessageBox.question(self, "Confirm Removal",
                                          f"Are you sure you want to remove '{name}' and all its properties/contents?",
                                          QMessageBox.Yes | QMessageBox.No)
             if reply == QMessageBox.Yes:
                 log.info(f"Removing schema item '{name}'.")
                 del parent_dict_ref[name]
                 # Remove from tree
                 (item.parent() or self.tree_widget.invisibleRootItem()).removeChild(item)
                 self.set_modified(True)


    def save_schema(self, save_path: typing.Optional[Path] = None) -> bool:
        """ Saves the current schema definition dictionary to a JSON file. """
        target_path = save_path or self.schema_path
        if not target_path:
            log.error("Schema save failed: No target path specified.")
            return False

        if target_path.suffix.lower() != ".json":
             QMessageBox.warning(self, "Invalid Format", "Schemas can only be saved as JSON files (.json).")
             # Optionally append .json? For now, just prevent saving.
             return False

        log.info(f"Saving schema definition to: {target_path}")
        try:
            # Ensure __version__ exists, default if somehow deleted
            if "__version__" not in self.schema_data:
                log.warning("Schema data missing '__version__', adding default '1.0.0'.")
                self.schema_data["__version__"] = "1.0.0"
                # Repopulate tree to show version? Optional.

            # Validate version format before saving
            try:
                parse_version(str(self.schema_data.get("__version__", "0.0.0")))
            except InvalidVersion as e:
                QMessageBox.critical(self, "Invalid Version", f"Schema contains an invalid __version__: {e}\nPlease correct it before saving.")
                return False

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(self.schema_data, f, indent=2, ensure_ascii=False)

            self.schema_path = target_path # Update path on successful save/save as
            self.set_modified(False)
            log.info(f"Schema definition saved successfully to {target_path}")
            self.schema_saved.emit(target_path) # Emit signal
            return True

        except (OSError, TypeError) as e:
            QMessageBox.critical(self, "Schema Save Error", f"Failed to save schema file:\n{target_path}\n\nError: {e}")
            log.exception("Error during save_schema")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Schema Save Error", f"An unexpected error occurred:\n{e}")
            log.exception("Unexpected error during save_schema")
            return False


    def set_modified(self, modified: bool):
        """ Sets the modification status and emits signal. """
        if self.is_modified != modified:
            self.is_modified = modified
            self.modification_changed.emit(modified)

    def close_widget(self) -> bool:
        """ Checks for modifications before closing. Returns True if safe to close. """
        if self.is_modified:
            reply = QMessageBox.question(self, "Unsaved Schema Changes",
                                         "The schema has unsaved changes. Do you want to save before closing?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                parent = self.parent()
                while parent and not isinstance(parent, MainWindow):
                    parent = parent.parent()
                if isinstance(parent, MainWindow):
                    # Need a way to trigger save specific to schema editor
                    return parent.save_active_schema() # Assume this method exists
                else:
                    log.error("Could not find MainWindow to trigger schema save.")
                    return False # Prevent close
            elif reply == QMessageBox.Cancel:
                return False
        return True


# --- Main Application Window ---
# (ConfigEditorWidget class remains as previously defined)
class ConfigEditorWidget(QWidget):
    """ Widget holding the Tree view and managing a single ConfigGuard instance (PyQt5). """
    modification_changed = pyqtSignal(bool)

    def __init__(self, schema_path: Path, config_path: typing.Optional[Path] = None, encryption_key: typing.Optional[bytes] = None, instance_version: typing.Optional[str] = None, parent=None):
        super().__init__(parent)
        self.schema_path = schema_path
        self.config_path = config_path # Will be None for "New Config"
        self.encryption_key = encryption_key
        self.instance_version_override = instance_version
        self.config_guard: typing.Optional[ConfigGuard] = None
        self.is_modified = False # Start unmodified

        self.layout = QVBoxLayout(self)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(4)
        self.tree_widget.setHeaderLabels(["Name", "Value", "Type", "Default"])
        self.layout.addWidget(self.tree_widget)

        self.delegate = SettingDelegate(self.tree_widget)
        self.tree_widget.setItemDelegateForColumn(COL_VALUE, self.delegate)
        self.delegate.data_committed.connect(self.handle_data_committed)

        self.tree_widget.header().setStretchLastSection(False)
        self.tree_widget.header().setSectionResizeMode(COL_NAME, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(COL_VALUE, QHeaderView.Stretch)
        self.tree_widget.header().setSectionResizeMode(COL_TYPE, QHeaderView.ResizeToContents)
        self.tree_widget.header().setSectionResizeMode(COL_DEFAULT, QHeaderView.ResizeToContents)
        self.tree_widget.header().resizeSection(COL_NAME, 200)
        self.tree_widget.header().resizeSection(COL_DEFAULT, 150)

        self.load_config()

    def load_config(self):
        """ Loads the schema and config file (if path provided) (PyQt5). """
        try:
            log.info(f"Editor loading schema from: {self.schema_path}")
            log.info(f"Editor using config path: {self.config_path}")
            log.info(f"Editor using instance version override: {self.instance_version_override}")
            log.info(f"Editor using encryption key: {'Yes' if self.encryption_key else 'No'}")

            # config_path=None will initialize with defaults based on schema
            self.config_guard = ConfigGuard(
                schema=self.schema_path,
                instance_version=self.instance_version_override,
                config_path=self.config_path, # Will be None for "New Config"
                encryption_key=self.encryption_key,
                autosave=False
            )
            log.info(f"Editor ConfigGuard instance created (Version: {self.config_guard.version}) for '{self.windowTitle()}'")
            self.populate_tree()
            self.set_modified(False)


        except FileNotFoundError as e:
             if self.config_path and self.config_path.exists():
                 QMessageBox.critical(self, "Error", f"Schema file may be missing or inaccessible:\n{e}")
                 self.config_guard = None
             elif self.config_path:
                 log.warning(f"Config file '{self.config_path}' not found. Using defaults.")
                 try:
                     self.config_guard = ConfigGuard(
                        schema=self.schema_path,
                        instance_version=self.instance_version_override,
                        config_path=None, # Initialize with defaults
                        encryption_key=self.encryption_key,
                        autosave=False
                     )
                     log.info(f"Re-initialized with defaults for {self.config_path}")
                     self.populate_tree()
                     self.set_modified(False) # Loaded defaults, not modified yet
                 except Exception as init_err:
                     QMessageBox.critical(self, "Error", f"Failed to initialize with defaults after file not found:\n{init_err}")
                     self.config_guard = None
             else:
                 QMessageBox.critical(self, "Error", f"Schema file not found:\n{e}")
                 self.config_guard = None

        except EncryptionError as e:
            log.error(f"Encryption error loading {self.config_path}: {e}")
            key_text, ok = QInputDialog.getText(self, "Encryption Key Needed",
                                                f"Enter encryption key (base64) for:\n{self.config_path}",
                                                QLineEdit.Password)
            if ok and key_text:
                try:
                    self.encryption_key = key_text.encode('utf-8')
                    self.config_guard = None # Reset
                    self.load_config() # Retry
                except Exception as key_err:
                     QMessageBox.critical(self, "Error", f"Invalid key or reload failed: {key_err}")
                     self.config_guard = None
            else:
                 QMessageBox.warning(self, "Load Cancelled", "Cannot load encrypted file.")
                 self.config_guard = None

        except (HandlerError, ValidationError, SchemaError, ImportError) as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load configuration:\n{e}")
            if self.config_guard and self.config_path:
                 log.info("Falling back to default values due to load error.")
                 self.config_guard = None # Reset
                 try: # Re-init with defaults
                      self.config_guard = ConfigGuard(
                          schema=self.schema_path, instance_version=self.instance_version_override,
                          config_path=None, encryption_key=self.encryption_key, autosave=False
                      )
                      self.populate_tree()
                      self.set_modified(False)
                 except Exception as final_err:
                      QMessageBox.critical(self, "Fatal Error", f"Failed to initialize with defaults:\n{final_err}")
                      self.config_guard = None
            else: # Schema or other init error
                self.config_guard = None

        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred during load:\n{e}")
            log.exception("Unexpected error during load_config")
            self.config_guard = None

    def populate_tree(self):
        # (populate_tree logic remains unchanged)
        self.tree_widget.clear()
        if not self.config_guard:
            return

        def add_items(parent_item, config_node):
            if isinstance(config_node, ConfigGuard):
                container = config_node._settings
            elif isinstance(config_node, ConfigSection):
                container = config_node._settings
            else:
                return

            for name, item in container.items():
                if isinstance(item, ConfigSetting):
                    schema = item.schema
                    value_str = str(item.value) if item.value is not None else "None"
                    default_str = str(schema.default_value) if schema.default_value is not None else "None"
                    tree_item = QTreeWidgetItem(parent_item, [name, value_str, schema.type_str, default_str])
                    tree_item.setToolTip(COL_NAME, schema.help or "No help provided.")
                    tree_item.setToolTip(COL_VALUE, f"Current Value: {value_str}")
                    tree_item.setToolTip(COL_TYPE, f"Type: {schema.type_str}, Nullable: {schema.nullable}")
                    tree_item.setToolTip(COL_DEFAULT, f"Default: {default_str}")
                    tree_item.setData(COL_NAME, ITEM_ROLE, item)
                    tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

                elif isinstance(item, ConfigSection):
                    schema_dict = item.get_schema_dict()
                    help_text = schema_dict.get("help", "Section")
                    tree_item = QTreeWidgetItem(parent_item, [name, "", "section", ""])
                    tree_item.setToolTip(COL_NAME, help_text)
                    tree_item.setData(COL_NAME, ITEM_ROLE, item)
                    font = tree_item.font(COL_NAME)
                    font.setBold(True)
                    tree_item.setFont(COL_NAME, font)
                    tree_item.setForeground(COL_NAME, QBrush(QColor("navy")))
                    add_items(tree_item, item) # Recurse

        add_items(self.tree_widget, self.config_guard)
        self.tree_widget.expandAll()

    def handle_data_committed(self, item: QTreeWidgetItem):
        # (handle_data_committed logic remains unchanged)
        if not self.config_guard: return

        cg_item = item.data(COL_NAME, ITEM_ROLE)
        if isinstance(cg_item, ConfigSetting):
            new_value_str = item.text(COL_VALUE)
            schema = cg_item.schema
            try:
                parsed_value: typing.Any = None
                # Coercion logic
                if schema.type is bool: parsed_value = new_value_str.lower() == "true"
                elif schema.type is int: parsed_value = int(new_value_str)
                elif schema.type is float: parsed_value = float(new_value_str)
                elif schema.type is list:
                    try:
                        parsed_value = json.loads(new_value_str)
                        if not isinstance(parsed_value, list): parsed_value = cg_item.value
                    except json.JSONDecodeError:
                         if new_value_str.strip(): parsed_value = [s.strip() for s in new_value_str.split(',')]
                         else: parsed_value = []
                else: parsed_value = new_value_str

                # Update ConfigGuard instance
                parent_container = cg_item._parent
                if parent_container:
                    parent_container[cg_item.name] = parsed_value # Triggers validation
                    log.info(f"Updated ConfigGuard value for '{cg_item.name}' to {parsed_value!r}")
                    self.set_modified(True)
                else:
                    log.error(f"Cannot find parent container for setting '{cg_item.name}'.")

            except (ValidationError, ValueError, TypeError) as e:
                log.error(f"Error updating ConfigGuard instance for {cg_item.name}: {e}")
                item.setText(COL_VALUE, str(cg_item.value) if cg_item.value is not None else "None") # Revert display
            except Exception as e:
                 log.exception(f"Unexpected error updating ConfigGuard for {cg_item.name}")

    def save_config(self, save_path: typing.Optional[Path] = None) -> bool:
        # (save_config logic remains unchanged)
        if not self.config_guard:
            QMessageBox.warning(self, "Save Error", "No configuration loaded.")
            return False

        target_path = save_path or self.config_path
        if not target_path:
            log.error("Save failed: No target path specified.")
            QMessageBox.warning(self, "Save Error", "No file path specified. Use 'Save As'.")
            return False

        requires_encryption = target_path.suffix.lower() in ('.bin', '.enc')
        current_key = self.encryption_key

        if requires_encryption and not current_key:
             key_text, ok = QInputDialog.getText(self, "Encryption Key Needed",
                                                f"Saving to '{target_path.name}' requires encryption.\nEnter encryption key (base64):",
                                                QLineEdit.Password)
             if ok and key_text:
                 try:
                     current_key = key_text.encode('utf-8')
                     configguard.Fernet(current_key) # Test key validity
                     self.encryption_key = current_key
                 except Exception as key_err:
                      QMessageBox.critical(self, "Invalid Key", f"The provided key is invalid: {key_err}")
                      return False
             else:
                  QMessageBox.warning(self, "Save Cancelled", "Cannot save without encryption key.")
                  return False
        elif not requires_encryption and current_key:
             reply = QMessageBox.question(self, "Encryption Warning",
                                        f"The file '{target_path.name}' will be saved UNENCRYPTED.\nAn encryption key is currently loaded. Continue without encryption?",
                                        QMessageBox.Yes | QMessageBox.No)
             if reply == QMessageBox.No:
                 return False
             current_key = None

        try:
            handler = configguard.handlers.get_handler(target_path, fernet=current_key)
            log.info(f"Saving config to {target_path} using {type(handler).__name__} (mode=values)")

            payload = {
                "instance_version": self.config_guard.version,
                "schema_definition": self.config_guard.get_instance_schema_definition(),
                "config_values": self.config_guard.get_config_dict(),
            }
            handler.save(target_path, data=payload, mode="values")

            self.config_path = target_path # Update path
            self.set_modified(False)
            log.info(f"Configuration saved successfully to {target_path}")
            return True

        except (HandlerError, EncryptionError, ValidationError, SchemaError, ValueError, ImportError) as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")
            log.exception("Error during save_config")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Save Error", f"An unexpected error occurred:\n{e}")
            log.exception("Unexpected error during save_config")
            return False

    def set_modified(self, modified: bool):
        # (set_modified logic remains unchanged)
        if self.is_modified != modified:
            self.is_modified = modified
            self.modification_changed.emit(modified)

    def close_widget(self) -> bool:
        # (close_widget logic remains unchanged)
        if self.is_modified:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "There are unsaved changes. Do you want to save before closing?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                parent = self.parent()
                while parent and not isinstance(parent, MainWindow):
                    parent = parent.parent()
                if isinstance(parent, MainWindow):
                    return parent.save_active_config() # Use existing save config method
                else:
                    log.error("Could not find MainWindow to trigger save from editor.")
                    return False
            elif reply == QMessageBox.Cancel:
                return False
        return True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ConfigGuard Editor")
        self.setGeometry(100, 100, 1000, 700)

        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)
        self.mdi_area.subWindowActivated.connect(self.update_window_title_and_actions)

        # Remove global schema context - each editor now manages its own
        # self.current_schema_path: typing.Optional[Path] = None
        # self.current_instance_version: typing.Optional[str] = None

        self.check_sample_files()
        self._create_actions()
        self._create_menus()
        self.update_window_title_and_actions() # Set initial state

    def check_sample_files(self):
        # (check_sample_files logic remains unchanged)
        if not SAMPLE_SCHEMA.exists():
             QMessageBox.warning(self, "Sample Files Missing",
                                 f"Sample schema file not found at:\n{SAMPLE_SCHEMA}\n\n"
                                 "Some examples might not load correctly.")

    def _create_actions(self):
        # --- Schema Actions ---
        self.new_schema_action = QAction("New &Schema", self)
        self.new_schema_action.setStatusTip("Create a new schema definition.")
        self.new_schema_action.triggered.connect(self.new_schema)

        self.open_schema_action = QAction("&Open Schema...", self)
        self.open_schema_action.setStatusTip("Open a schema definition file for viewing/editing.")
        self.open_schema_action.triggered.connect(self.open_schema)

        self.save_schema_action = QAction("Save S&chema", self)
        self.save_schema_action.setStatusTip("Save the active schema definition.")
        self.save_schema_action.setShortcut("Ctrl+Shift+S")
        self.save_schema_action.triggered.connect(self.save_active_schema)
        self.save_schema_action.setEnabled(False)

        self.save_schema_as_action = QAction("Save Schema &As...", self)
        self.save_schema_as_action.setStatusTip("Save the active schema definition to a new file.")
        self.save_schema_as_action.triggered.connect(self.save_active_schema_as)
        self.save_schema_as_action.setEnabled(False)

        # --- Config Value Actions ---
        self.new_config_action = QAction("&New Config...", self) # Renamed
        self.new_config_action.setStatusTip("Create a new configuration based on a schema file.")
        self.new_config_action.triggered.connect(self.new_config)
        # self.new_config_action.setEnabled(False) # No longer depends on global state

        self.load_values_action = QAction("&Load Config Values...", self) # Renamed
        self.load_values_action.setStatusTip("Load configuration values using a specified schema file.")
        self.load_values_action.triggered.connect(self.load_config_values) # Connect to new method
        # self.load_values_action.setEnabled(False) # No longer depends on global state

        self.save_config_action = QAction("&Save Config", self) # Renamed for clarity
        self.save_config_action.setStatusTip("Save the active configuration values.")
        self.save_config_action.setShortcut("Ctrl+S")
        self.save_config_action.triggered.connect(self.save_active_config)
        self.save_config_action.setEnabled(False)

        self.save_config_as_action = QAction("Save Config &As...", self) # Renamed
        self.save_config_as_action.setStatusTip("Save the active configuration values to a new file.")
        self.save_config_as_action.triggered.connect(self.save_active_config_as)
        self.save_config_as_action.setEnabled(False)

        # --- Common Actions ---
        self.close_action = QAction("&Close", self)
        self.close_action.setStatusTip("Close the active window (Schema or Config).")
        self.close_action.setShortcut("Ctrl+W")
        self.close_action.triggered.connect(self.close_active_subwindow)
        self.close_action.setEnabled(False)

        self.exit_action = QAction("E&xit", self)
        self.exit_action.setStatusTip("Exit the application.")
        self.exit_action.triggered.connect(self.close)

    def _create_menus(self):
        self.statusBar()

        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.new_schema_action)
        file_menu.addAction(self.open_schema_action)
        file_menu.addAction(self.save_schema_action)
        file_menu.addAction(self.save_schema_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.new_config_action)
        file_menu.addAction(self.load_values_action)
        file_menu.addAction(self.save_config_action)
        file_menu.addAction(self.save_config_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.close_action)
        file_menu.addAction(self.exit_action)

        self.window_menu = self.menuBar().addMenu("&Window")
        self.window_menu.aboutToShow.connect(self.update_window_menu)

    def update_window_menu(self):
        # (update_window_menu logic remains unchanged)
        self.window_menu.clear()
        tile_action = self.window_menu.addAction("Tile")
        tile_action.triggered.connect(self.mdi_area.tileSubWindows)
        cascade_action = self.window_menu.addAction("Cascade")
        cascade_action.triggered.connect(self.mdi_area.cascadeSubWindows)
        self.window_menu.addSeparator()

        windows = self.mdi_area.subWindowList()
        active_subwindow = self.mdi_area.activeSubWindow()

        for i, window in enumerate(windows):
            title = window.windowTitle()
            action = self.window_menu.addAction(title)
            action.setCheckable(True)
            action.setChecked(window is active_subwindow)
            action.triggered.connect(lambda checked=False, w=window: self.mdi_area.setActiveSubWindow(w))

    def get_active_editor_widget(self) -> typing.Optional[QWidget]:
        """ Gets the active editor widget (either SchemaEditorWidget or ConfigEditorWidget). """
        active_sub = self.mdi_area.activeSubWindow()
        if active_sub:
            return active_sub.widget()
        return None

    def update_window_title_and_actions(self, sub_window: typing.Optional[QMdiSubWindow] = None):
        """ Updates main window title and enables/disables actions based on active window type. """
        if sub_window is None:
            sub_window = self.mdi_area.activeSubWindow()

        active_widget = self.get_active_editor_widget()
        is_schema_editor = isinstance(active_widget, SchemaEditorWidget)
        is_config_editor = isinstance(active_widget, ConfigEditorWidget)
        is_modified = False
        has_widget = active_widget is not None
        window_title_base = "ConfigGuard Editor"

        if active_widget:
            is_modified = active_widget.is_modified
            # Use sub-window title which is already formatted
            window_title_base = f"{sub_window.windowTitle()}{'[*] ' if is_modified else ' '}- ConfigGuard Editor"

        # Enable/disable actions based on active editor type
        self.save_schema_action.setEnabled(is_schema_editor and is_modified)
        self.save_schema_as_action.setEnabled(is_schema_editor)

        self.save_config_action.setEnabled(is_config_editor and is_modified)
        self.save_config_as_action.setEnabled(is_config_editor)

        self.close_action.setEnabled(has_widget)

        # New Config/Load Values are always enabled (they prompt for schema)
        self.new_config_action.setEnabled(True)
        self.load_values_action.setEnabled(True)

        # Update main window title and status bar
        self.setWindowTitle(window_title_base)
        status = "No file open."
        if is_schema_editor:
            status = f"Editing Schema: {active_widget.schema_path.name if active_widget.schema_path else 'New Schema'}"
        elif is_config_editor:
            schema_name = active_widget.schema_path.name if active_widget.schema_path else 'Unknown Schema'
            config_name = active_widget.config_path.name if active_widget.config_path else 'New Config'
            version = f" (v{active_widget.config_guard.version})" if active_widget.config_guard else ""
            status = f"Editing Config: {config_name} | Schema: {schema_name}{version}"
        self.statusBar().showMessage(status)


    def new_schema(self):
        """ Creates a new, empty Schema Editor window. """
        log.info("Creating new schema editor.")
        self.create_schema_editor_subwindow(schema_path=None)

    def open_schema(self):
        """ Opens a schema JSON file in a Schema Editor window. """
        filepath_str, _ = QFileDialog.getOpenFileName(
            self, "Open Schema Definition File", str(EXAMPLES_DIR), "JSON Files (*.json);;All Files (*)"
        )
        if filepath_str:
            schema_path = Path(filepath_str)
            self.create_schema_editor_subwindow(schema_path=schema_path)

    def save_active_schema(self) -> bool:
        """ Saves the content of the active Schema Editor window. """
        active_widget = self.get_active_editor_widget()
        if isinstance(active_widget, SchemaEditorWidget):
            if active_widget.schema_path:
                return active_widget.save_schema()
            else:
                return self.save_active_schema_as() # Force Save As if no path
        return False

    def save_active_schema_as(self) -> bool:
        """ Saves the content of the active Schema Editor window to a new file. """
        active_widget = self.get_active_editor_widget()
        if isinstance(active_widget, SchemaEditorWidget):
            default_name = "new_schema.json"
            if active_widget.schema_path: default_name = active_widget.schema_path.name

            filepath_str, _ = QFileDialog.getSaveFileName(
                self, "Save Schema Definition As",
                str(EXAMPLES_DIR / default_name),
                "JSON Files (*.json);;All Files (*)"
            )
            if filepath_str:
                save_path = Path(filepath_str)
                if active_widget.save_schema(save_path):
                    # Update title after successful save
                    active_sub = self.mdi_area.activeSubWindow()
                    if active_sub: self.update_window_title_and_actions(active_sub)
                    return True
        return False

    # --- Config Value Methods ---
    def new_config(self):
        """ Prompts for a schema, then creates a new Config Editor window. """
        schema_path, instance_version = self._prompt_for_schema_and_version()
        if schema_path:
            log.info(f"Creating new config based on schema: {schema_path} (Version override: {instance_version})")
            self.create_config_editor_subwindow(
                schema_path=schema_path,
                config_path=None, # New config
                instance_version=instance_version
            )

    def load_config_values(self):
        """ Prompts for schema, then value file, then opens Config Editor. """
        schema_path, instance_version = self._prompt_for_schema_and_version()
        if not schema_path:
            return # User cancelled schema selection

        filepath_str, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration Values File", str(EXAMPLES_DIR),
            "Config Files (*.json *.yaml *.yml *.toml *.db *.sqlite *.sqlite3 *.bin *.enc);;All Files (*)"
        )
        if filepath_str:
            config_path = Path(filepath_str)
            encryption_key: typing.Optional[bytes] = None
            # Check for sample key
            if config_path == EXAMPLES_DIR / "sample_config_encrypted.db" and SAMPLE_KEY_FILE.exists():
                reply = QMessageBox.question(self, "Load Sample Key?",
                                             f"Load the corresponding sample encryption key from:\n{SAMPLE_KEY_FILE.name}?",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    try:
                        encryption_key = SAMPLE_KEY_FILE.read_bytes()
                        configguard.Fernet(encryption_key)
                        log.info("Loaded sample encryption key.")
                    except Exception as e:
                        QMessageBox.warning(self, "Key Error", f"Failed to load or validate sample key: {e}")
                        encryption_key = None

            self.create_config_editor_subwindow(
                schema_path=schema_path,
                config_path=config_path,
                instance_version=instance_version,
                encryption_key=encryption_key
            )

    def _prompt_for_schema_and_version(self) -> typing.Tuple[typing.Optional[Path], typing.Optional[str]]:
        """ Helper to prompt user for schema file and optional version override. """
        schema_path_str, _ = QFileDialog.getOpenFileName(
            self, "Select Schema File", str(EXAMPLES_DIR), "JSON Files (*.json);;All Files (*)"
        )
        if not schema_path_str:
            return None, None

        schema_path = Path(schema_path_str)
        schema_version: typing.Optional[str] = None
        explicit_instance_version: typing.Optional[str] = None

        try:
            # Pre-load schema to check for version
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            if not isinstance(schema_data, dict):
                raise ValueError("Schema file must contain a JSON object.")

            schema_version_raw = schema_data.get("__version__")
            if schema_version_raw:
                 schema_version = str(schema_version_raw)
                 parse_version(schema_version) # Validate format

            prompt_text = f"Schema '{schema_path.name}'"
            if schema_version: prompt_text += f" (v{schema_version}).\n"
            else: prompt_text += f" has no version.\n"
            prompt_text += "Enter instance version override (optional):"

            version_text, ok = QInputDialog.getText(self, "Set Instance Version", prompt_text)

            if ok and version_text.strip():
                try:
                    parse_version(version_text)
                    explicit_instance_version = version_text
                except InvalidVersion:
                     QMessageBox.warning(self, "Invalid Version", f"Entered version '{version_text}' is invalid. No override set.")

            return schema_path, explicit_instance_version

        except InvalidVersion as e:
            QMessageBox.critical(self, "Schema Error", f"Schema contains an invalid version format:\n{e}")
            return None, None
        except Exception as e:
            QMessageBox.critical(self, "Schema Error", f"Failed to load or parse schema file:\n{e}")
            return None, None

    def save_active_config(self) -> bool:
        """ Saves the content of the active Config Editor window. """
        active_widget = self.get_active_editor_widget()
        if isinstance(active_widget, ConfigEditorWidget):
            if active_widget.config_path:
                return active_widget.save_config()
            else:
                return self.save_active_config_as() # Force Save As for new configs
        return False

    def save_active_config_as(self) -> bool:
        """ Saves the content of the active Config Editor window to a new file. """
        active_widget = self.get_active_editor_widget()
        if isinstance(active_widget, ConfigEditorWidget):
            default_filename = "new_config.json"
            if active_widget.config_path: default_filename = active_widget.config_path.name
            elif active_widget.schema_path: default_filename = active_widget.schema_path.with_suffix('.json').name

            filepath_str, selected_filter = QFileDialog.getSaveFileName(
                self, "Save Configuration Values As",
                str(EXAMPLES_DIR / default_filename),
                "JSON (*.json);;YAML (*.yaml *.yml);;TOML (*.toml);;SQLite DB (*.db *.sqlite *.sqlite3);;Encrypted Binary (*.bin *.enc);;All Files (*)"
            )
            if filepath_str:
                save_path = Path(filepath_str)
                if active_widget.save_config(save_path):
                    active_sub = self.mdi_area.activeSubWindow()
                    if active_sub: self.update_window_title_and_actions(active_sub)
                    return True
        return False

    # --- Window Creation Methods ---
    def create_schema_editor_subwindow(self, schema_path: typing.Optional[Path]):
        """ Creates and adds a SchemaEditorWidget sub-window. """
        try:
            editor_widget = SchemaEditorWidget(schema_path=schema_path, parent=self)
            # No need to check config_guard here

            sub_window = QMdiSubWindow()
            sub_window.setWidget(editor_widget)
            sub_window.setAttribute(Qt.WA_DeleteOnClose)
            self.mdi_area.addSubWindow(sub_window)

            # Connect modification signal
            editor_widget.modification_changed.connect(
                lambda modified, w=sub_window: self.handle_modification(modified, w)
            )
            # Connect schema saved signal to potentially update other windows? (Advanced use)
            # editor_widget.schema_saved.connect(self.handle_schema_saved)

            sub_window.show()
            sub_window.resize(600, 600) # Schema editor size
            # Set initial title
            title = "New Schema"
            if editor_widget.schema_path: title = editor_widget.schema_path.name
            sub_window.setWindowTitle(title)
            self.update_window_title_and_actions(sub_window) # Update main window state

        except Exception as e:
            QMessageBox.critical(self, "Error Creating Schema Editor", f"Failed to create schema editor window:\n{e}")
            log.exception("Error in create_schema_editor_subwindow")

    def create_config_editor_subwindow(self, schema_path: Path, config_path: typing.Optional[Path] = None, encryption_key: typing.Optional[bytes] = None, instance_version: typing.Optional[str] = None):
        """ Creates and adds a ConfigEditorWidget sub-window. """
        try:
            editor_widget = ConfigEditorWidget(
                schema_path=schema_path,
                config_path=config_path,
                encryption_key=encryption_key,
                instance_version=instance_version,
                parent=self
            )

            if editor_widget.config_guard is None:
                 log.error("Config editor widget failed ConfigGuard init. Subwindow aborted.")
                 return

            sub_window = QMdiSubWindow()
            sub_window.setWidget(editor_widget)
            sub_window.setAttribute(Qt.WA_DeleteOnClose)
            self.mdi_area.addSubWindow(sub_window)

            editor_widget.modification_changed.connect(
                lambda modified, w=sub_window: self.handle_modification(modified, w)
            )

            sub_window.show()
            sub_window.resize(700, 500)
            # Title is set dynamically based on loaded data/state in update_window_title_and_actions
            self.update_window_title_and_actions(sub_window)

        except Exception as e:
            QMessageBox.critical(self, "Error Creating Config Editor", f"Failed to create config editor window:\n{e}")
            log.exception("Error in create_config_editor_subwindow")

    # --- Common Methods ---
    def handle_modification(self, modified: bool, window: QMdiSubWindow):
        # (handle_modification logic remains unchanged)
        window.setWindowModified(modified)
        if self.mdi_area.activeSubWindow() == window:
            self.update_window_title_and_actions(window)

    def close_active_subwindow(self):
        # (close_active_subwindow logic remains unchanged)
        active_sub = self.mdi_area.activeSubWindow()
        if active_sub:
            # close() triggers the sub-window's close event, which calls widget's close_widget
            if not active_sub.close():
                 log.debug("Subwindow close cancelled.")

    def closeEvent(self, event):
        # (closeEvent logic remains unchanged)
        self.mdi_area.closeAllSubWindows()
        if self.mdi_area.subWindowList():
            event.ignore()
        else:
            event.accept()


# --- Run Application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())