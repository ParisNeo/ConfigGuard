###############
API Reference
###############

This page provides auto-generated documentation from the ConfigGuard source code docstrings.

Main Class
==========

.. autoclass:: configguard.ConfigGuard
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __weakref__, __dict__

Schema & Setting Classes
========================

.. autoclass:: configguard.SettingSchema
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: configguard.ConfigSetting
   :members:
   :undoc-members:
   :show-inheritance:

Exceptions
==========

.. automodule:: configguard.exceptions
   :members:
   :undoc-members:

Handlers (Base Class)
=====================

.. autoclass:: configguard.handlers.StorageHandler
   :members: load, save, __init__
   :undoc-members:

.. note::
   Specific handler implementations (like ``JsonHandler``) are typically used internally via the ``get_handler`` factory and the ``ConfigGuard`` class based on file extensions. Their direct use is less common.

Utilities
=========

.. autofunction:: configguard.generate_encryption_key

.. autofunction:: configguard.set_log_level