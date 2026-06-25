# Delagecy

`delagecy` is the fy-suite for governed legacy removal.

It does **not** delete code. It gives the repo a repeatable path for:

- scanning for legacy surfaces in code, docs, tests, routes, and UI files;
- registering every newly found legacy item before removal work starts;
- recording the required discussion / approval state;
- separating true legacy residue from active canonical behavior with outdated names;
- verifying that removed items no longer remain in code or UI surfaces;
- exporting a human-readable tracker for reviews and ADR updates.

## Commands

```bash
PYTHONPATH="'fy'-suites" python -m delagecy.tools scan --out "'fy'-suites/delagecy/reports/latest_scan.json"
PYTHONPATH="'fy'-suites" python -m delagecy.tools new --scan-json "'fy'-suites/delagecy/reports/latest_scan.json"
PYTHONPATH="'fy'-suites" python -m delagecy.tools register --scan-json "'fy'-suites/delagecy/reports/latest_scan.json" --fingerprint <hash> --title "Short title"
PYTHONPATH="'fy'-suites" python -m delagecy.tools approve --id DLG-001 --approved-by "<name>" --note "Removal approved after review"
PYTHONPATH="'fy'-suites" python -m delagecy.tools mark-removed --id DLG-001 --verification "tests + scan clean"
PYTHONPATH="'fy'-suites" python -m delagecy.tools mark-canonicalized --id DLG-001 --compatibility-scope alternative_use --reason "Active provider variant" --evidence "ADR/reference link"
PYTHONPATH="'fy'-suites" python -m delagecy.tools check --scan-json "'fy'-suites/delagecy/reports/latest_scan.json"
PYTHONPATH="'fy'-suites" python -m delagecy.tools report --scan-json "'fy'-suites/delagecy/reports/latest_scan.json" --out "'fy'-suites/delagecy/reports/latest_report.md"
PYTHONPATH="'fy'-suites" python -m delagecy.tools export-tracker
```

`scan` and `new` produce machine-readable JSON. `report` turns those artifacts
into the readable working document for review: summary, gate status, scope
warnings, top hit files, first unregistered findings, UI residue examples, and
the required removal rules.

The current execution plan lives at
`reports/legacy_removal_execution_plan.md`. It sequences removal into guarded
waves so legacy residue is removed completely without breaking active runtime,
UI, API, docs, or tests.

After editable install, use `delagecy ...`.

## Hard rules

1. New legacy findings must be registered and reported before any removal work.
2. Removal requires an explicit approval entry in the registry.
3. Problems, ambiguity, ownership conflicts, or integrity risk must be discussed with the user; the tool records blockers but does not auto-resolve them.
4. A removal is not done until code, docs, tests, routes, and UI surfaces are clean.
5. Legacy is not active compatibility. If a surface is still required by the current system, preserve the behavior and canonicalize the name/contract instead of deleting it.
6. Compatibility with earlier repo/product versions is not retained. Remove it together with code, tests, docs, UI, diagnostics, generated data, and routes.
7. Compatibility for active alternative usage, such as provider or adapter variation, may be retained only when the registry records evidence and the surface is canonicalized.
8. Redirects, compatibility aliases, hidden UI blocks, diagnostics fields, and tests count as residue unless they are reclassified as active canonical behavior with explicit evidence.

The active policy ADR is `docs/ADR/adr-0029-residue-removal-policy.md`; `delagecy` is the executable register and gate for that policy.

## Internal self-test area

`internal/` belongs to the suite itself. It may intentionally contain legacy
markers as scanner fixtures. Generated control-plane files
(`delagecy_registry.json`, `legacy_removal_tracker.md`) are skipped by default so
the suite does not register its own bookkeeping as product residue.
