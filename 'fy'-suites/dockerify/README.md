# Dockerify

Dockerify governs the **repository Docker surface** for World of Shadows.

The suite focuses on the stable local stack path around:

- `docker-up.py`
- `docker-compose.yml`
- component Dockerfiles
- backend migration / database upgrade behavior
- startup smoke evidence and compose-facing health contracts

Dockerify is not a replacement for Docker Compose itself. It is the **governance and audit layer** that keeps the repository's Docker entry path honest, testable, and restartable.

## What Dockerify checks

- canonical compose services exist for the local stack
- `docker-up.py` still exposes the expected lifecycle commands
- compose health / dependency posture is still coherent
- database upgrade behavior remains visible and backed by migrations/tests
- smoke/startup evidence exists for the stack surface

## CLI

After `pip install -e .` from the repository root:

```bash
dockerify audit --out "'fy'-suites/dockerify/reports/dockerify_audit.json"
dockerify self-check
```

## Outputs

- `reports/dockerify_audit.json`
- `reports/dockerify_audit_report.md`
- `state/DOCKER_STACK_STATE.md`

## Current stance

Dockerify audits and documents the stack entry path. It does **not** auto-edit Compose or migrations on its own; unresolved issues are reported explicitly.
