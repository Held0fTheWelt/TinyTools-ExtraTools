"""Platform dispatch records for fy_platform.surfaces.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import read_text_safe, sha256_text, utc_now
from fy_platform.ir.catalog import IRCatalog
from fy_platform.ir.models import DecisionRecord, RepoAsset, RepositorySnapshot, ReviewTask, StructureFinding, SurfaceAlias


def fingerprint_repo(target: Path) -> str:
    """Fingerprint repo.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        target: Primary target used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    items: list[str] = []
    # Process path one item at a time so fingerprint_repo applies the same rule across
    # the full collection.
    for path in sorted(target.rglob('*')):
        # Branch on path.is_dir() so fingerprint_repo only continues along the matching
        # state path.
        if path.is_dir():
            continue
        # Protect the critical fingerprint_repo work so failures can be turned into a
        # controlled result or cleanup path.
        try:
            stat = path.stat()
        except OSError:
            continue
        items.append(f'{path.relative_to(target).as_posix()}:{stat.st_size}:{int(stat.st_mtime)}')
        # Branch on len(items) >= 500 so fingerprint_repo only continues along the
        # matching state path.
        if len(items) >= 500:
            break
    return sha256_text('\n'.join(items))

def record_snapshot(ir_catalog: IRCatalog, target_repo: Path | None) -> str | None:
    """Record snapshot.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        ir_catalog: Primary ir catalog used by this step.
        target_repo: Primary target repo used by this step.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    if target_repo is None:
        return None
    snapshot = RepositorySnapshot(
        snapshot_id=ir_catalog.new_id('snapshot'),
        repo_root=str(target_repo),
        fingerprint=fingerprint_repo(target_repo),
        created_at=utc_now(),
        scan_scope='full',
    )
    ir_catalog.write_snapshot(snapshot)
    return snapshot.snapshot_id


def record_bundle_assets(ir_catalog: IRCatalog, snapshot_id: str | None, payload: dict[str, Any], suite: str) -> list[str]:
    """Record bundle assets.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        ir_catalog: Primary ir catalog used by this step.
        snapshot_id: Identifier used to select an existing run or
            record.
        payload: Structured data carried through this workflow.
        suite: Primary suite used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[str] = []
    if not snapshot_id:
        return out
    for key, role in [('json_path', 'artifact_json'), ('md_path', 'artifact_md')]:
        path = payload.get(key)
        if not path:
            continue
        p = Path(path)
        if not p.is_file():
            continue
        asset = RepoAsset(
            asset_id=ir_catalog.new_id('asset'),
            snapshot_id=snapshot_id,
            path=str(p),
            kind='generated_artifact',
            language='markdown' if p.suffix == '.md' else 'json',
            role=role,
            ownership_zone='fy_workspace',
            content_hash=sha256_text(read_text_safe(p)),
            is_generated=True,
            suite_origin=suite,
            metadata={'path_key': key},
        )
        ir_catalog.write_repo_asset(asset)
        out.append(asset.asset_id)
    return out


def record_alias(ir_catalog: IRCatalog, suite: str, public_command: str, mode_name: str) -> str:
    """Record alias.

    Args:
        ir_catalog: Primary ir catalog used by this step.
        suite: Primary suite used by this step.
        public_command: Primary public command used by this step.
        mode_name: Primary mode name used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    alias = SurfaceAlias(
        alias_id=ir_catalog.new_id('alias'),
        legacy_surface=f'{suite}::{mode_name}',
        current_surface=f'fy::{public_command}::{mode_name}',
        status='compatibility-entry',
        sunset_phase='C2',
    )
    ir_catalog.write_surface_alias(alias)
    return alias.alias_id


def record_decision(ir_catalog: IRCatalog, *, reason: str, lane: str, recommended_action: str) -> str:
    """Record decision.

    Args:
        ir_catalog: Primary ir catalog used by this step.
        reason: Primary reason used by this step.
        lane: Primary lane used by this step.
        recommended_action: Primary recommended action used by this
            step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    decision = DecisionRecord(
        decision_id=ir_catalog.new_id('decision'),
        decision_kind='platform_route',
        lane=lane,
        reason=reason,
        confidence='high',
        recommended_action=recommended_action,
        created_at=utc_now(),
    )
    ir_catalog.write_decision(decision)
    return decision.decision_id


def record_review(ir_catalog: IRCatalog, mode_name: str, decision_id: str) -> str:
    """Record review.

    Args:
        ir_catalog: Primary ir catalog used by this step.
        mode_name: Primary mode name used by this step.
        decision_id: Identifier used to select an existing run or
            record.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    review = ReviewTask(
        review_task_id=ir_catalog.new_id('review'),
        subject_kind='decision',
        subject_id=decision_id,
        reason=f'{mode_name} mode requires review before outward action',
        priority='medium',
        requested_by_lane='govern',
        blocking=False,
    )
    ir_catalog.write_review_task(review)
    return review.review_task_id


def record_failure_finding(ir_catalog: IRCatalog, suite: str, mode_name: str, payload: dict[str, Any], asset_ids: list[str]) -> str:
    """Record failure finding.

    Args:
        ir_catalog: Primary ir catalog used by this step.
        suite: Primary suite used by this step.
        mode_name: Primary mode name used by this step.
        payload: Structured data carried through this workflow.
        asset_ids: Primary asset ids used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    finding = StructureFinding(
        finding_id=ir_catalog.new_id('finding'),
        finding_kind='platform_dispatch_failure',
        severity='high',
        confidence='high',
        summary=f'{suite}::{mode_name} failed during platform dispatch: {payload.get("reason") or payload.get("error") or "unknown"}',
        asset_ids=asset_ids,
        recommended_action='Re-audit the touched compatibility surface and rerun the selected implementation pass.',
    )
    ir_catalog.write_structure_finding(finding)
    return finding.finding_id
