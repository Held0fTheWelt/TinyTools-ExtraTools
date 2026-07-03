# Unreal Project Design Assistant

UPDA is a local browser for Blueprint Journals and the projects that result
from them. It is not a Tiny Tool Development repository browser; its default
index is intentionally limited to BPJ journal material.

The first version is split into four surfaces:

- **Overview** shows Blueprint Journal sources, derived project cases, source
  health, and record counts.
- **Review** searches project journals, BPJ knowledge journals, construction
  instructions, project evidence notes, and reusable BPJ source journals.
- **Planning** groups selected records into local work packages with priority,
  status, and notes.
- **Deploy** turns a package into a local Markdown deploy plan under
  `Saved/UPDA/deploy/`.

UPDA is read-only against indexed project sources. Planning and deploy state is
stored under `Saved/UPDA/` outside this tool folder.

## Start

From the TinyToolDevelopment root:

```powershell
python Tools\UPDA\upda.py
```

Open `http://127.0.0.1:8776`.

Or use the helper:

```powershell
.\Tools\UPDA\run_upda.ps1
```

Use another port when needed:

```powershell
.\Tools\UPDA\run_upda.ps1 -Port 8888
```

## Indexed Defaults

UPDA indexes these BPJ sources when present:

- `Git/docs/BPJ/project-journals`
  - `*/README.md` and `*/*-journal.md` are treated as project journals.
  - other `*/*.md` files are reviewable project journal sections.
- `Git/docs/BPJ/knowledge`
- `Git/docs/BPJ/Best_Practices_Journal_Specification.md`

Add an extra source root:

```powershell
python Tools\UPDA\upda.py --source-root D:\Some\BlueprintJournalExport
```

## Local State

| Path | Purpose |
| --- | --- |
| `Saved/UPDA/planning.json` | Planning packages created from selected review records. |
| `Saved/UPDA/deploy/*.md` | Generated deploy-plan Markdown files. |

## Useful Commands

```powershell
python Tools\UPDA\upda.py --port 8776
python Tools\UPDA\upda.py --state-root Saved\UPDA
python Tools\UPDA\upda.py --source-root Git\docs\BPJ
```
