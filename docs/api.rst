###############
API Reference
###############

This page provides auto-generated documentation from the ConfigMaster source code docstrings.

Main Class
==========

.. autoclass:: configmaster.ConfigMaster
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__, __dict__

Schema & Setting Classes
========================

.. autoclass:: configmaster.SettingSchema
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: configmaster.ConfigSetting
   :members:
   :undoc-members:
   :show-inheritance:

Exceptions
==========

.. automodule:: configmaster.exceptions
   :members:
   :undoc-members:

Handlers (Base Class)
=====================

.. autoclass:: configmaster.handlers.StorageHandler
   :members: load, save, __init__
   :undoc-members:

.. note::
   Specific handler implementations (like ``JsonHandler``) are typically used internally via the ``get_handler`` factory and the ``ConfigMaster`` class based on file extensions. Their direct use is less common.

Utilities
=========

.. autofunction:: configmaster.generate_encryption_key

.. autofunction:: configmaster.set_log_level