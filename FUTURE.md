# Future Plans & Considerations

This document outlines potential next steps and areas for improvement for the ConfigGuard library.

**High Priority:**

1.  **Comprehensive Unit Tests:** Add extensive unit tests using `pytest` in the `tests/` directory. Focus on:
    *   Schema validation (including edge cases, types, constraints).
    *   Nested section creation, access, and validation.
    *   Setting/getting values (attribute/item access, nested access).
    *   Loading/saving (`values`/`full` modes) with different handlers (start with JSON, add others as implemented).
    *   Encryption/decryption scenarios.
    *   Versioning and migration logic (including scenarios with added/removed/nested sections).
    *   `import_config` / `export_schema_with_values` functionality, especially with nesting.
    *   Error handling and exception raising.
2.  **Sphinx Documentation Content:**
    *   Run `sphinx-quickstart` in the `docs/` directory (if not already done).
    *   Configure `docs/conf.py`: Set theme (e.g., `sphinx_rtd_theme`), enable extensions (`autodoc`, `napoleon`, `viewcode`). Add `configguard` path to `sys.path`.
    *   Create `index.rst` with project overview, installation, quick start, and core concepts (toctree).
    *   Create `api.rst` using `automodule` directives to generate API documentation from docstrings.
    *   **Write/Update Docstrings:** Ensure all public classes, methods, and functions have clear, comprehensive docstrings (Google style preferred) explaining parameters, return values, exceptions, and usage, especially covering the new nested section features.
    *   Add usage examples and explanations for nested sections, versioning, encryption, etc.

**Medium Priority:**

3.  **Implement More Handlers:** Add support for other common configuration formats:
    *   `YamlHandler` (requires `pyyaml`).
    *   `TomlHandler` (requires `toml`).
    *   *(Consider)* `IniHandler` (requires careful thought on mapping INI structure to schema/nesting).
    *   *(Consider)* `SqliteHandler` (requires careful design for schema mapping, e.g., key-value table, potentially separate tables for sections?).
    *   Update `configguard/handlers/__init__.py` (`HANDLER_MAP`) and `pyproject.toml` (`optional-dependencies`) as handlers are added.
4.  **GitHub Actions (CI / Publish):**
    *   Create `.github/workflows/ci.yml`: Define jobs for linting (`black`, `ruff`), type checking (`mypy`), running tests (`pytest`), and building the package on pushes/PRs.
    *   Create `.github/workflows/publish.yml`: Define a job to build and publish the package to PyPI automatically when a new tag/release is created on GitHub.
5.  **Refine Type Hinting:** While type hints are used, perform a thorough review:
    *   Ensure maximum coverage for public and internal APIs.
    *   Consider enabling `mypy --strict` and addressing any resulting errors for improved type safety.
    *   Verify `py.typed` inclusion ensures proper downstream type checking.

**Lower Priority / Future Ideas:**

6.  **Refine Encryption Handling:** Evaluate if the current approach (handler encrypts/decrypts serialized bytes) is optimal for all handler types (e.g., databases). Consider alternative strategies if needed, although the current method works well for file-based formats.
7.  **Advanced Migration Strategies:** Allow users to provide custom migration functions for complex schema changes between versions (e.g., renaming keys, splitting sections).
8.  **Secret Vault Example:** Create a more complex example application (`examples/secret_vault.py`) demonstrating secure storage and retrieval of sensitive data using ConfigGuard's encryption and potentially nested sections.
9.  **List Element Validation:** Add optional schema support for validating the types of elements within a `list` setting (e.g., `"type": "list[int]"` or a separate `"element_type"` key).
