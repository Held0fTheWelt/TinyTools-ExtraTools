# Fy Platform

Shared portability primitives for Fy suites.

## Scope (Wave 1)

- project root resolution without embedding suite-specific assumptions in shared core
- `fy-manifest.yaml` loading and suite-config lookup
- versioned shared artifact envelope for machine-readable outputs
- baseline compatibility matrix artifacts
- bootstrap utility for first-pass manifest generation

## CLI

```bash
python -m fy_platform.tools bootstrap
python -m fy_platform.tools validate-manifest
python -m fy_platform.tools bootstrap --project-root /path/to/project
```

After `pip install -e .` from repo root:

```bash
fy-platform bootstrap
fy-platform validate-manifest
```

Environment override for root resolution: `FY_PLATFORM_PROJECT_ROOT`.

## Core admission rule

Nothing moves into `fy_platform` solely due to duplication. Shared-core additions require demonstrated cross-suite utility and compatibility impact review.
