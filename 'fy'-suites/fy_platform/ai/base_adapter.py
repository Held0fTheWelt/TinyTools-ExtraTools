"""Shared base adapter for all fy suite adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fy_platform.ai.adapter_commands import (
    attach_status_page,
    clean_suite,
    compare_runs,
    consolidate_unsupported,
    cross_suite,
    explain_suite,
    import_bundle_unsupported,
    init_suite,
    inspect_suite,
    prepare_context_pack,
    prepare_fix_suite,
    production_readiness_suite,
    release_readiness_suite,
    reset_suite,
    self_audit_suite,
    self_governance_status,
    triage_suite,
)
from fy_platform.ai.context_packs.service import ContextPackService
from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.model_router.router import ModelRouter
from fy_platform.ai.run_journal.journal import RunJournal
from fy_platform.ai.run_lifecycle import finish_run, start_run, write_payload_bundle
from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.workspace import ensure_workspace_layout, suite_hub_dir, workspace_root


class BaseSuiteAdapter(ABC):
    """Abstract base class for base suite adapter.
    """
    __test__ = False

    def __init__(self, suite: str, root: Path | None = None) -> None:
        """Initialize BaseSuiteAdapter.

        This callable writes or records artifacts as part of its
        workflow. The implementation iterates over intermediate items
        before it returns.

        Args:
            suite: Primary suite used by this step.
            root: Root directory used to resolve repository-local paths.
        """
        self.suite = suite
        self.root = workspace_root(root)
        ensure_workspace_layout(self.root)
        self.registry = EvidenceRegistry(self.root)
        self.journal = RunJournal(self.root)
        self.index = SemanticIndex(self.root)
        self.context_packs = ContextPackService(self.root)
        self.router = ModelRouter(self.root)
        self.hub_dir = suite_hub_dir(self.root, suite)
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        # Process name one item at a time so __init__ applies the same rule across the
        # full collection.
        for name in ('reports', 'state', 'generated'):
            (self.hub_dir / name).mkdir(parents=True, exist_ok=True)

    def _cross_suite(self, query: str | None = None) -> dict[str, Any]:
        """Cross suite.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return cross_suite(self, query)

    def _attach_status_page(self, command: str, payload: dict[str, Any], latest_run: dict[str, Any] | None = None, governance: dict[str, Any] | None = None) -> dict[str, Any]:
        """Attach status page.

        Args:
            command: Named command for this operation.
            payload: Structured data carried through this workflow.
            latest_run: Primary latest run used by this step.
            governance: Primary governance used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return attach_status_page(self, command, payload, latest_run=latest_run, governance=governance)

    def self_governance_status(self) -> dict[str, Any]:
        """Self governance status.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return self_governance_status(self)

    def init(self, target_repo_root: str | None = None) -> dict[str, Any]:
        """Init the requested operation.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return init_suite(self, target_repo_root)

    def inspect(self, query: str | None = None) -> dict[str, Any]:
        """Inspect the requested operation.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return inspect_suite(self, query)

    @abstractmethod
    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        raise NotImplementedError

    def explain(self, audience: str = 'developer') -> dict[str, Any]:
        """Explain the requested operation.

        Args:
            audience: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return explain_suite(self, audience)

    def prepare_context_pack(self, query: str, audience: str = 'developer') -> dict[str, Any]:
        """Prepare context pack.

        Args:
            query: Free-text input that shapes this operation.
            audience: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return prepare_context_pack(self, query, audience)

    def compare_runs(self, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        """Compare runs.

        Args:
            left_run_id: Identifier used to select an existing run or
                record.
            right_run_id: Identifier used to select an existing run or
                record.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return compare_runs(self, left_run_id, right_run_id)

    def clean(self, mode: str = 'standard') -> dict[str, Any]:
        """Clean the requested operation.

        Args:
            mode: Named mode for this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return clean_suite(self, mode)

    def reset(self, mode: str = 'soft') -> dict[str, Any]:
        """Reset the requested operation.

        Args:
            mode: Named mode for this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return reset_suite(self, mode)

    def triage(self, query: str | None = None) -> dict[str, Any]:
        """Triage the requested operation.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return triage_suite(self, query)

    def prepare_fix(self, finding_ids: list[str]) -> dict[str, Any]:
        """Prepare fix.

        Args:
            finding_ids: Primary finding ids used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return prepare_fix_suite(self, finding_ids)

    def self_audit(self) -> dict[str, Any]:
        """Self audit.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return self_audit_suite(self)

    def release_readiness(self) -> dict[str, Any]:
        """Release readiness.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return release_readiness_suite(self)

    def production_readiness(self) -> dict[str, Any]:
        """Production readiness.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return production_readiness_suite(self)

    def import_bundle(self, bundle_path: str, *, legacy: bool = False) -> dict[str, Any]:
        """Import bundle.

        Args:
            bundle_path: Filesystem path to the file or directory being
                processed.
            legacy: Whether to enable this optional behavior.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return import_bundle_unsupported(self, bundle_path, legacy=legacy)

    def consolidate(self, target_repo_root: str, *, apply_safe: bool = False, instruction: str | None = None) -> dict[str, Any]:
        """Consolidate the requested operation.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.
            apply_safe: Whether to enable this optional behavior.
            instruction: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return consolidate_unsupported(self, target_repo_root, apply_safe=apply_safe, instruction=instruction)

    def _start_run(self, mode: str, target_repo_root: Path) -> tuple[str, Path, str]:
        """Start run.

        Args:
            mode: Named mode for this operation.
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            tuple[str, Path, str]:
                Filesystem path produced or resolved by
                this callable.
        """
        return start_run(root=self.root, suite=self.suite, mode=mode, target_repo_root=target_repo_root, registry=self.registry, journal=self.journal)

    def _finish_run(self, run_id: str, status: str, summary: dict[str, Any]) -> None:
        """Finish run.

        Args:
            run_id: Identifier used to select an existing run or record.
            status: Named status for this operation.
            summary: Structured data carried through this workflow.
        """
        finish_run(self.suite, run_id, status, summary, registry=self.registry, journal=self.journal)

    def _write_payload_bundle(self, *, run_id: str, run_dir: Path, payload: dict[str, Any], summary_md: str, role_prefix: str) -> dict[str, str]:
        """Write payload bundle.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            run_id: Identifier used to select an existing run or record.
            run_dir: Root directory used to resolve repository-local
                paths.
            payload: Structured data carried through this workflow.
            summary_md: Primary summary md used by this step.
            role_prefix: Primary role prefix used by this step.

        Returns:
            dict[str, str]:
                Structured payload describing the
                outcome of the operation.
        """
        return write_payload_bundle(root=self.root, suite=self.suite, run_id=run_id, run_dir=run_dir, payload=payload, summary_md=summary_md, role_prefix=role_prefix, registry=self.registry)
