################
Installation
################

Install ConfigGuard using pip:

.. code-block:: bash

   pip install configguard

This installs the core library with JSON support.

Optional Features
=================

Encryption
----------
To use the configuration encryption features, you need the ``cryptography`` library. You can install it along with ConfigGuard using the ``[encryption]`` extra:

.. code-block:: bash

   pip install configguard[encryption]

Alternatively, install it separately:

.. code-block:: bash

   pip install cryptography

Other Backends (Future)
-----------------------
Support for other storage backends like YAML, TOML, and SQLite is planned. When available, they will likely be installable via extras:

.. code-block:: bash

   # Example (when implemented)
   pip install configguard[yaml]
   pip install configguard[toml]
   pip install configguard[sqlite]
   pip install configguard[all_handlers] # Install all available handlers

Development Installation
========================
If you want to contribute to ConfigGuard or install the latest development version:

1. Clone the repository:
   .. code-block:: bash

      git clone https://github.com/ParisNeo/ConfigGuard.git
      cd ConfigGuard

2. Install in editable mode with development dependencies:
   .. code-block:: bash

      pip install -e .[dev]

This will install the package such that changes in your local code are immediately reflected, along with tools needed for testing, linting, and building documentation (like `pytest`, `black`, `ruff`, `mypy`, `sphinx`).