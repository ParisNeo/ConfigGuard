# Future Plans & Considerations

This document outlines potential next steps and areas for improvement for the ConfigGuard library.

**High Priority:**

1.  **Comprehensive Unit Tests:** Add extensive unit tests using `pytest` in the `tests/` directory. Focus on:
    *   Schema validation (including edge cases, types, constraints).
    *   Nested section creation, access, and validation.
    *   Setting/getting values (attribute/item access, nested access).
    *   Loading/saving (`values`/`full` modes) with **all implemented handlers (JSON, YAML, TOML, SQLite)**. Test handler-specific behaviors (e.g., SQLite flattening/unflattening).
    *   Encryption/decryption scenarios across different handlers.
    *   **Versioning and Migration:** Test version logic thoroughly, including scenarios with `instance_version` parameter overriding schema version, missing versions, loading older/newer files across different handlers, and migration with nested/dynamic sections.
    *   `import_config` / `export_schema_with_values` functionality, especially with nesting and dynamic sections.
    *   Error handling and exception raising (including `ImportError` for missing handler dependencies, `SchemaError` for invalid versions).
2.  **Sphinx Documentation Content:**
    *   Run `sphinx-quickstart` in the `docs/` directory (if not already done).
    *   Configure `docs/conf.py`: Set theme (e.g., `sphinx_rtd_theme`), enable extensions (`autodoc`, `napoleon`, `viewcode`). Add `configguard` path to `sys.path`.
    *   Create `index.rst` with project overview, installation (including extras for handlers), quick start, core concepts (toctree).
    *   Create `api.rst` using `automodule` directives to generate API documentation from docstrings.
    *   **Write/Update Docstrings:** Ensure all public classes, methods, and functions have clear, comprehensive docstrings (Google style preferred) explaining parameters (including `instance_version`), return values, exceptions, and usage, covering nested sections and different handlers.
    *   Add usage examples for each handler (JSON, YAML, TOML, SQLite), demonstrating nesting and encryption where applicable. Explain the SQLite handler's key-value/JSON storage mechanism.

**Medium Priority:**

3.  **Implement More Handlers (Optional):** Consider adding support for other formats if there is demand:
    *   *(Consider)* `IniHandler` (requires careful thought on mapping INI structure [sections, no deep nesting] to schema/nesting). How would `full` mode work?
    *   *(Consider)* Other formats (e.g., environment variables, cloud configuration services).
4.  **Refine SQLite Handler:**
    *   *(Consider)* Offer alternative storage strategies beyond flattened key-value (e.g., dedicated tables for sections), potentially configurable. This adds complexity but might be more efficient for very large/deeply nested configs queried frequently.
    *   *(Consider)* Add helper methods specific to database interactions if needed.
5.  **GitHub Actions (CI / Publish):**
    *   Create `.github/workflows/ci.yml`: Define jobs for linting (`black`, `ruff`), type checking (`mypy`), running tests (`pytest` - potentially matrix testing different Python versions and optional dependencies), and building the package on pushes/PRs.
    *   Create `.github/workflows/publish.yml`: Define a job to build and publish the package to PyPI automatically when a new tag/release is created on GitHub.
6.  **Refine Type Hinting:** While type hints are used, perform a thorough review:
    *   Ensure maximum coverage for public and internal APIs.
    *   Consider enabling `mypy --strict` and addressing any resulting errors for improved type safety.
    *   Verify `py.typed` inclusion ensures proper downstream type checking.

**Lower Priority / Future Ideas:**

7.  **Refine Encryption Handling:** Evaluate if the current approach (handler encrypts/decrypts serialized bytes) is optimal for all handler types. The current method works well for file-based and the current SQLite implementation.
8.  **Advanced Migration Strategies:** Allow users to provide custom migration functions for complex schema changes between versions (e.g., renaming keys, splitting sections, complex type changes).
9.  **Secret Vault Example:** Create a more complex example application (`examples/secret_vault.py`) demonstrating secure storage and retrieval of sensitive data using ConfigGuard's encryption and potentially nested sections with different backends.
10. **List Element Validation:** Add optional schema support for validating the types of elements within a `list` setting (e.g., `"type": "list[int]"` or a separate `"element_type"` key).

This list reflects the addition of the `instance_version` parameter and continues to prioritize testing and documentation as crucial next steps.
