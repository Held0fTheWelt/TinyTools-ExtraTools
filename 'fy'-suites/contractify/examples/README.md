# Contractify example machine outputs

These **committed** JSON files are **shape samples** for integrators and reviewers. They are smaller than a full monorepo audit.

- **`contract_discovery.sample.json`** — output shape of `python -m contractify.tools discover` (contracts, projections, relations).
- **`contract_audit.sample.json`** — output shape of `python -m contractify.tools audit` (adds drift, conflicts, `actionable_units`).

Regenerate from a real repo when the payload schema changes (keep samples small):

```bash
python -m contractify.tools discover --out "'fy'-suites/contractify/examples/_tmp_discovery.json" --quiet
python -m contractify.tools audit --out "'fy'-suites/contractify/examples/_tmp_audit.json" --quiet
```

Then trim large arrays and copy to `*.sample.json`. Ephemeral `_tmp_*.json` under `examples/` should be deleted and is gitignored if you add a local ignore pattern.

Live machine exports during day-to-day work belong under `reports/` (gitignored for `reports/*.json` at repo root — see [`../reports/README.md`](../reports/README.md)). **Full** frozen discover/audit JSON from the hermetic tree lives under [`../reports/committed/`](../reports/committed/). **`actionable_units`** entries may prefix conflicts as **`[conflict:<severity>|conflict|…]`** — see `contract_audit.sample.json`.

**Packaging hygiene:** do not ship `__pycache__` or `*.pyc` inside suite ZIPs.

- **Preferred:** `git archive` from the repo root so ignored paths (see root [`.gitignore`](../../.gitignore) and this suite’s [`.gitignore`](../.gitignore)) never enter the bundle.
- **Manual folder ZIP (PowerShell):** from the **repository root**, strip bytecode under the hub, then archive:

  ```powershell
  $suite = Join-Path $PWD "'fy'-suites" | Join-Path -ChildPath "contractify"
  Get-ChildItem -LiteralPath $suite -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
  ```

  Repeat after local `pytest` if you need a pristine tree before zipping.
