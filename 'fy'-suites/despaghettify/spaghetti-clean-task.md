# Spaghetti clean task (workstream artefact wipe + ephemeral cleanup)

**Purpose:** Remove **all** session pre/post files under [`state/artifacts/workstreams/`](state/artifacts/workstreams/) (every governed workstream slug), then recreate **empty** `pre/` and `post/` directories so the tree stays usable for the next wave. **Also** clears **machine session** paths under [`state/artifacts/autonomous_loop/`](state/artifacts/autonomous_loop/) (see **Step 1b**) and an optional **last-check** JSON at `state/artifacts/spaghetti_check_last.json` if present. Optionally continues with the same **ephemeral** repo cleanup as [`spaghetti-reset-task.md`](spaghetti-reset-task.md) (caches, `var/` scratch, hub `*.tmp`).

**Language:** [Repository language](../docs/dev/contributing.md#repository-language).

**Binding index:** Workstream slugs and paths — [`state/WORKSTREAM_INDEX.md`](state/WORKSTREAM_INDEX.md).

---

## Danger / irreversibility

- This task **deletes governance evidence** (all files under `artifacts/workstreams/<slug>/pre/` and `…/post/` for every slug). **Do not** run on a machine that is the **only** copy of required closure proof; prefer machines with Git history / PRs / CI logs as backup.
- **Step 1b** removes **`autonomous_state.json`** and any other files under **`artifacts/autonomous_loop/`** (autonomous macro-loop session; see [`spaghetti-autonomous-agent-task.md`](spaghetti-autonomous-agent-task.md)). After a clean, start a new session with `python -m despaghettify.tools autonomous-init` if needed.
- This task **does not** delete `despaghettify/state/WORKSTREAM_*.md` or other state **documents** — only the **artefact file trees** under `artifacts/workstreams/` plus the paths named in **Step 1b**.
- **`artifacts/repo_governance_rollout/`** is **not** removed here (different scope); delete only if team policy says so, outside this task.

---

## Step 1 — Wipe and recreate `artifacts/workstreams/`

**Effect:** Delete the entire directory `despaghettify/state/artifacts/workstreams/` (all children), then recreate it with one folder per workstream from the index, each containing empty **`pre/`** and **`post/`**.

Canonical slugs (must match [WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)):

| Slug |
|------|
| `backend_runtime_services` |
| `ai_stack` |
| `administration_tool` |
| `documentation` |
| `world_engine` |

**PowerShell (repo root):**

```powershell
$root = 'despaghettify/state/artifacts/workstreams'
if (Test-Path $root) { Remove-Item -Recurse -Force $root }
$slugs = @(
  'backend_runtime_services',
  'ai_stack',
  'administration_tool',
  'documentation',
  'world_engine'
)
foreach ($s in $slugs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $root "$s/pre") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $root "$s/post") | Out-Null
}
```

**Bash (repo root):**

```bash
rm -rf despaghettify/state/artifacts/workstreams
for s in backend_runtime_services ai_stack administration_tool documentation world_engine; do
  mkdir -p "despaghettify/state/artifacts/workstreams/$s/pre"
  mkdir -p "despaghettify/state/artifacts/workstreams/$s/post"
done
```

---

## Step 1b — `artifacts/autonomous_loop/` and optional check echo JSON

**Effect:** Delete the directory `despaghettify/state/artifacts/autonomous_loop/` entirely (including `autonomous_state.json`), then recreate it as an **empty** folder so future `autonomous-init` runs have a stable parent. Remove **`despaghettify/state/artifacts/spaghetti_check_last.json`** if it exists (local echo of a prior `check` run — not governance evidence).

**PowerShell (repo root):**

```powershell
$al = 'despaghettify/state/artifacts/autonomous_loop'
if (Test-Path $al) { Remove-Item -Recurse -Force $al }
New-Item -ItemType Directory -Force -Path $al | Out-Null
$last = 'despaghettify/state/artifacts/spaghetti_check_last.json'
if (Test-Path $last) { Remove-Item -Force $last }
```

**Bash (repo root):**

```bash
rm -rf despaghettify/state/artifacts/autonomous_loop
mkdir -p despaghettify/state/artifacts/autonomous_loop
rm -f despaghettify/state/artifacts/spaghetti_check_last.json
```

**Do not** delete `artifacts/repo_governance_rollout/` or other ad-hoc trees under `artifacts/` except the two paths above and the workstream tree handled in **Step 1**.

---

## Step 2 — Ephemeral repo + hub scratch (same scope as reset task 1a–1c)

Reuse **Step 1** (sections 1a–1c) from [`spaghetti-reset-task.md`](spaghetti-reset-task.md): repo caches, wave-adjacent `var/` trees, loose scratch under `despaghettify/` excluding `state/` and `templates/`.

**Order:** Run **Step 1 (workstreams)** and **Step 1b (autonomous loop + optional check JSON)** of **this** document **before** the reset task’s copy of EMPTY → live input, so no stale session files remain beside a fresh input list.

---

## Relationship to other tasks

| Task | Role |
|------|------|
| **This file (`spaghetti-clean-task`)** | Wipe **all** workstream pre/post trees, **`artifacts/autonomous_loop/`**, optional **`spaghetti_check_last.json`**, + optional ephemeral cleanup. |
| [`spaghetti-reset-task.md`](spaghetti-reset-task.md) | **Requires** running this clean (workstream wipe) **first**, then reset input from template + one check pass. |
| [`spaghetti-check-task.md`](spaghetti-check-task.md) | Read-side metrics; **does not** delete artefacts. |

---

## Completion checklist

- [ ] `despaghettify/state/artifacts/workstreams/` was removed and recreated with **five** slugs, each with **empty** `pre/` and `post/`.
- [ ] **Step 1b:** `despaghettify/state/artifacts/autonomous_loop/` is empty (no `autonomous_state.json`); `despaghettify/state/artifacts/spaghetti_check_last.json` removed if it existed.
- [ ] (If combined with reset) Ephemeral dirs from reset task 1a–1b and hub file sweep 1c completed.
- [ ] Team understands prior session files under workstreams and autonomous-loop state are **gone** from the working tree.
