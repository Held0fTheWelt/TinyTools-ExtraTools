"""Run lifecycle for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.governance_checks import build_self_governance_status
from fy_platform.ai.strategy_profiles import strategy_runtime_metadata
from fy_platform.ai.workspace import internal_run_dir, target_repo_id, write_json


def start_run(*, root: Path, suite: str, mode: str, target_repo_root: Path, registry, journal) -> tuple[str, Path, str]:
    """Start run.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.
        mode: Named mode for this operation.
        target_repo_root: Root directory used to resolve
            repository-local paths.
        registry: Primary registry used by this step.
        journal: Primary journal used by this step.

    Returns:
        tuple[str, Path, str]:
            Filesystem path produced or resolved by this
            callable.
    """
    governance = build_self_governance_status(root, suite)
    # Branch on not governance['ok'] so start_run only continues along the matching
    # state path.
    if not governance['ok']:
        raise RuntimeError(f"governance_gate_failed:{';'.join(governance['failures'])}")
    # Build filesystem locations and shared state that the rest of start_run reuses.
    tgt_id = target_repo_id(target_repo_root)
    strategy = strategy_runtime_metadata(root)
    run = registry.start_run(suite=suite, mode=mode, target_repo_root=str(target_repo_root), target_repo_id=tgt_id, strategy_profile=strategy['active_profile'], run_metadata={'active_strategy_profile': strategy})
    run_dir = internal_run_dir(root, suite, run.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    journal.append(suite, run.run_id, 'run_started', {'mode': mode, 'target_repo_root': str(target_repo_root), 'target_repo_id': tgt_id, 'active_strategy_profile': strategy})
    journal.append(suite, run.run_id, 'self_governance_checked', governance)
    return run.run_id, run_dir, tgt_id


def finish_run(suite: str, run_id: str, status: str, summary: dict[str, Any], *, registry, journal) -> None:
    """Finish run.

    Args:
        suite: Primary suite used by this step.
        run_id: Identifier used to select an existing run or record.
        status: Named status for this operation.
        summary: Structured data carried through this workflow.
        registry: Primary registry used by this step.
        journal: Primary journal used by this step.
    """
    journal.append(suite, run_id, 'run_finished', {'status': status, 'summary': summary})
    registry.finish_run(run_id, status=status)


def write_payload_bundle(*, root: Path, suite: str, run_id: str, run_dir: Path, payload: dict[str, Any], summary_md: str, role_prefix: str, registry) -> dict[str, str]:
    """Write payload bundle.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.
        suite: Primary suite used by this step.
        run_id: Identifier used to select an existing run or record.
        run_dir: Root directory used to resolve repository-local paths.
        payload: Structured data carried through this workflow.
        summary_md: Primary summary md used by this step.
        role_prefix: Primary role prefix used by this step.
        registry: Primary registry used by this step.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    json_path = run_dir / f'{role_prefix}.json'
    md_path = run_dir / f'{role_prefix}.md'
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(json_path, payload)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    md_path.write_text(summary_md, encoding='utf-8')
    # Register the written artifact in the evidence registry so later status and compare
    # flows can discover it.
    registry.record_artifact(suite=suite, run_id=run_id, format='json', role=f'{role_prefix}_json', path=str(json_path.relative_to(root)), payload=payload)
    # Register the written artifact in the evidence registry so later status and compare
    # flows can discover it.
    registry.record_artifact(suite=suite, run_id=run_id, format='md', role=f'{role_prefix}_md', path=str(md_path.relative_to(root)), payload={'markdown_preview': summary_md[:500]})
    return {'json_path': str(json_path), 'md_path': str(md_path)}
