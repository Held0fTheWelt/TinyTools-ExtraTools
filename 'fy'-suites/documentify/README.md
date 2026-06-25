# Documentify

Documentify generates **working documentation drafts** from the current repository surface.

Inputs:

- current code layout
- current documentation trees
- current technical / operations / testing documents

Outputs:

- `generated/simple/` — easy-entry explanations in a readable **What / Why / How** style
- `generated/technical/` — technical reference views
- `generated/roles/` — role-bound documentation by subfolder

Documentify is additive: it drafts a maintained documentation layer without pretending to replace the repository's normative contracts.

## Output style goals

The easy documentation output should be:

- easy to read for humans
- structured around **What**, **Why**, and **How**
- willing to use **Mermaid** when a small visual helps orientation
- still grounded in the real repository surface

## CLI

```bash
documentify generate --out-dir "'fy'-suites/documentify/generated"
documentify audit
```
