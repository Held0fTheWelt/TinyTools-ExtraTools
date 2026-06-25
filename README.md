# TinyTools Extra Tools

This repository contains local, Docker-friendly extra tools for Tiny Tool Development. The tools here support architecture work, AI-assisted modeling, repository inspection, knowledge capture, track-shape authoring, and local workflow evidence. They are companion tools, not Unreal Engine runtime plugins.

## Repository Contents

| Path | Purpose |
| --- | --- |
| `'fy'-suites/` | A collection of local automation suites and adapters for code, documentation, validation, packaging, observability, and related workflow tasks. |
| `AIaGMW/` | AI-assisted graphical modeling workspace with backend/frontend packages, sample workspaces, validation logic, and diagram/model editing workflows. |
| `ArchitecturalKnowledgeDB/` | Local architecture knowledge database service for ADR/spec/UML provenance, consistency checks, context packs, and project knowledge records. |
| `TrackShape/` | Embedded Git repository pointer for the TrackShape compiler/tracing toolchain. Its inner repository state is managed separately. |
| `TrackShapeEditor/` | Track shape editor and desktop/web UI for authoring, validating, compiling, and exporting track shape data. |
| `UmlBrowser/` | Local PlantUML and Mermaid browser with Docker and standalone Python startup options. |

Tiny Tool Observatory lives in the main Tiny Tool Development Git repository at `Git/Tools/TinyToolObservatory`, not in this extra-tools repository.

## Local-First Model

Most tools are intended to run locally through Python, Node, Docker Compose, or small startup wrappers such as `docker-up.py`. Generated outputs, runtime databases, logs, caches, local state, and dependency folders are intentionally ignored by Git.

The repository should contain source code, schemas, examples, documentation, and lightweight fixtures. It should not contain private credentials, local machine state, generated dependency trees, SQLite runtime databases, or temporary inspection output.

## Typical Workflows

- Start an individual tool from its own folder, usually through `python docker-up.py`, a local package script, or its documented command.
- Keep tool-specific runtime data in ignored `data/`, `logs/`, `exports/`, `state/`, or `workspace/` folders.
- Use Tiny Tool Observatory (`Git/Tools/TinyToolObservatory` in the main development repository) to inspect the broader Tiny Tool Development artifact landscape and create handoffs for follow-up workflows.
- Manage `TrackShape` changes inside its embedded repository unless it is intentionally converted into a normal folder in this repository.

## Repository Restart

This repository was restarted from fresh root commits after public leak remediation. Internal specs, platform strategy, agent skills, implementation plans, and maintainer runbooks were evacuated to the private Tiny Tool Development `Git` repository; each affected tool folder contains an `INTERNAL_*_RELOCATED.md` pointer.

Tiny Tool Observatory lives only in `Git/Tools/TinyToolObservatory`.
