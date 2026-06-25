# Testify

Testify governs the **test execution surface** of the repository.

It focuses on:

- the canonical multi-suite runner (`tests/run_tests.py`)
- GitHub Actions workflow coverage for core test lanes
- root `pyproject.toml` suite script registration
- component `pyproject.toml` / pytest configuration visibility

Testify does not replace the repository tests. It keeps the **test governance shell** current and visible.

## CLI

```bash
testify audit --out "'fy'-suites/testify/reports/testify_audit.json"
testify self-check
```
