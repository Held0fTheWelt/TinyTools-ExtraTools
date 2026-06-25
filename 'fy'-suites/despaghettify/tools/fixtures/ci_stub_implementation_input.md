# CI stub — not the canonical input list

This file is **only** for `solve-preflight --override-input-list` when the real [despaghettification_implementation_input.md](../../despaghettification_implementation_input.md) has **no** open `DS-*` rows (CI must still exercise preflight). **Do not** merge this into the canonical list.

## Information input list

| ID | pattern | location (typical) | hint / measurement idea | direction (solution sketch) | collision hint |
|----|---------|--------------------|-------------------------|----------------------------|----------------|
| **DS-990** | **C3 ·** CI smoke stub | `backend/app/__init__.py` | AST | Stub only — validates tooling | CI only |

## Recommended implementation order

| Phase | note |
|-------|------|
| z | `pytest -q --co` (stub) |
