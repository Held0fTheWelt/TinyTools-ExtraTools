# observifyfy

`observifyfy` is the internal operations, memory, and AI-observability suite for the fy tool family.

It does **not** redefine repository truth. Instead it observes how fy suites work, what they changed, what state they left behind, what internal docs they manage, and what the best next steps are.

## Core responsibilities

- consolidate suite-level state without polluting project-facing repo truth
- expose internal fy-managed docs under `'fy'-suites/...`
- track internal ADR governance roots for Contractify under `docs/ADR`
- track internal documentation roots for Documentify under `docs`
- summarize journal, run, report, state, and readiness signals across suites
- generate AI-readable context packs and memory snapshots
- recommend the highest-value next steps

## CLI

```bash
observifyfy inspect --repo-root /path/to/workspace
observifyfy audit --repo-root /path/to/workspace
observifyfy ai-pack --repo-root /path/to/workspace
observifyfy full --repo-root /path/to/workspace
```
