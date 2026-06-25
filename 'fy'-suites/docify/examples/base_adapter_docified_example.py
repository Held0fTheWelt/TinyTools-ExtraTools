"""
Shared base adapter for all fy suite adapters.

This module defines :class:`BaseSuiteAdapter`, the common runtime
surface that all suite-specific adapters build on top of. The class
provides three major kinds of behavior:

1. **Workspace bootstrapping** It resolves the fy workspace root,
ensures the required internal directory layout exists, and wires
together the shared platform services (registry, journal, semantic
index, context packs, and model router).

2. **Common lifecycle commands** It implements the generic suite
lifecycle used throughout the fy platform, including ``init``,
``inspect``, ``explain``, ``prepare_context_pack``, ``compare_runs``,
``clean``, ``reset``, ``triage``, ``prepare_fix``, ``self_audit``,
``release_readiness``, ``production_readiness``, ``import_bundle``, and
``consolidate``.

3. **Run orchestration helpers** It provides internal helpers for
starting and finishing runs, writing artifact bundles, attaching suite
status pages, and enforcing governance gates before outward work begins.

The class is intentionally conservative:

- internal state always stays inside the fy workspace,
- outward work is explicit,
- risky automatic action is avoided,
- and every suite inherits the same operational baseline.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fy_platform.ai.context_packs.service import ContextPackService
from fy_platform.ai.cross_suite_intelligence import collect_cross_suite_signals
from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.model_router.router import ModelRouter
from fy_platform.ai.policy.suite_quality_policy import (
    evaluate_suite_quality,
    evaluate_workspace_quality,
)
from fy_platform.ai.production_readiness import workspace_production_readiness
from fy_platform.ai.release_readiness import suite_release_readiness
from fy_platform.ai.run_journal.journal import RunJournal
from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.status_page import build_status_payload, write_status_page
from fy_platform.ai.workspace import (
    binding_path,
    ensure_workspace_layout,
    internal_run_dir,
    suite_hub_dir,
    target_repo_id,
    utc_now,
    workspace_root,
    write_json,
)


class BaseSuiteAdapter(ABC):
    """Abstract base class for base suite adapter workflows.
    """

    def __init__(self, suite: str, root: Path | None = None) -> None:
        """Initialize the adapter and its shared platform services.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            suite: Primary suite used by this step.
            root: Root directory used to resolve repository-local paths.
        """
        self.suite = suite
        self.root = workspace_root(root)

        # Step 1: build the minimum fy workspace structure before any shared
        # service tries to touch local state, registry files, or generated
        # outputs. This prevents "works on my machine" style partial setups.
        ensure_workspace_layout(self.root)

        # Step 2: instantiate the shared platform services. These objects are
        # reused across all suite adapters so every suite sees the same
        # registry, run journal, semantic index, context-pack pipeline, and
        # model-routing logic.
        self.registry = EvidenceRegistry(self.root)
        self.journal = RunJournal(self.root)
        self.index = SemanticIndex(self.root)
        self.context_packs = ContextPackService(self.root)
        self.router = ModelRouter()

        # Step 3: create the suite-local hub. This is the suite-owned surface
        # inside the autark fy workspace. Reports, suite state, and generated
        # artifacts live here instead of polluting the outward target repo.
        self.hub_dir = suite_hub_dir(self.root, suite)
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "reports").mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "state").mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "generated").mkdir(parents=True, exist_ok=True)

    def _cross_suite(self, query: str | None = None) -> dict[str, Any]:
        """Collect cross-suite signals relevant to the current suite.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return collect_cross_suite_signals(self.root, self.suite, query=query)

    def _attach_status_page(
        self,
        command: str,
        payload: dict[str, Any],
        latest_run: dict[str, Any] | None = None,
        governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Attach a persisted status page to a command payload.

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
        latest = latest_run if latest_run is not None else self.registry.latest_run(self.suite)
        gov = governance if governance is not None else payload.get("governance")

        # The payload should never feel isolated from the rest of the fy
        # workspace. If the caller did not already attach cross-suite context,
        # add a lightweight signal bundle now so the status page has enough
        # neighboring evidence to be useful to a human reader.
        payload.setdefault(
            "cross_suite",
            self._cross_suite(payload.get("query") or payload.get("summary") or ""),
        )

        # Convert the raw command payload into the normalized status-page shape.
        # This gives us one consistent, human-readable surface per suite command.
        status = build_status_payload(
            suite=self.suite,
            command=command,
            payload=payload,
            latest_run=latest,
            governance=gov,
        )

        # Persist the status page and merge the resulting paths back into the
        # payload so CLI/report layers can point at the generated files directly.
        payload.update(write_status_page(self.root, self.suite, status))
        return payload

    def self_governance_status(self) -> dict[str, Any]:
        """Evaluate workspace-level and suite-level governance health.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        # The governance model has two layers:
        # 1. workspace-level expectations that every suite depends on
        # 2. suite-specific expectations for the selected suite itself
        workspace = evaluate_workspace_quality(self.root)
        suite = evaluate_suite_quality(self.root, self.suite)

        # Both must be healthy for the combined governance gate to be green.
        ok = bool(workspace["ok"] and suite["ok"])

        # Failures are namespaced so later readers can immediately see whether
        # they are blocked by a workspace issue or by a suite-local problem.
        failures = [f"workspace:{item}" for item in workspace["missing"]] + [
            f"suite:{item}" for item in suite["missing"]
        ]

        # Warnings are merged because the status page should show the reader all
        # relevant caution signals in one place, even when they are not hard
        # blockers.
        warnings = list(workspace["warnings"]) + list(suite["warnings"])

        return {
            "ok": ok,
            "suite": self.suite,
            "failures": failures,
            "warnings": warnings,
            "workspace": workspace,
            "suite_check": suite,
        }

    def init(self, target_repo_root: str | None = None) -> dict[str, Any]:
        """Initialize the suite and optionally bind it to a target
        repository.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        ensure_workspace_layout(self.root)
        target = Path(target_repo_root).resolve() if target_repo_root else None
        governance = self.self_governance_status()

        # The optional outward target must exist and be a directory before we
        # record a binding. A broken binding would poison later outward work.
        if target_repo_root and (not target or not target.exists() or not target.is_dir()):
            payload = {
                "ok": False,
                "suite": self.suite,
                "reason": "target_repo_not_found",
                "target_repo_root": target_repo_root,
                "governance": governance,
            }
            return self._attach_status_page("init", payload, governance=governance)

        # Initialization is intentionally blocked if the internal workspace is
        # not healthy enough. This prevents suites from binding outward work
        # while their own internal foundations are already broken.
        if not governance["ok"]:
            payload = {
                "ok": False,
                "suite": self.suite,
                "reason": "governance_gate_failed:init",
                "governance": governance,
            }
            return self._attach_status_page("init", payload, governance=governance)

        # The binding file is the stable contract that tells later commands
        # which outward repository this suite was initialized against.
        binding = {
            "suite": self.suite,
            "workspace_root": str(self.root),
            "target_repo_root": str(target) if target else None,
            "target_repo_id": target_repo_id(target) if target else None,
            "bound_at": utc_now(),
        }
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(binding_path(self.root, self.suite), binding)

        payload = {
            "ok": True,
            "suite": self.suite,
            "binding": binding,
            "governance": governance,
            "warnings": governance["warnings"],
            "summary": (
                f"{self.suite} is initialized and bound for outward work. "
                "Internal state stays in the fy workspace."
            ),
        }
        return self._attach_status_page("init", payload, governance=governance)

    def inspect(self, query: str | None = None) -> dict[str, Any]:
        """Inspect the latest suite state and optionally retrieve query
        context.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        latest = self.registry.latest_run(self.suite)
        governance = self.self_governance_status()

        # The route decision documents how the platform would like this
        # inspection to run: moderate evidence strength, developer audience,
        # and strict reproducibility for stable results.
        route = self.router.route(
            "summarize",
            evidence_strength="moderate",
            audience="developer",
            reproducibility="strict",
        )

        # Start with a minimal inspection payload that already makes sense even
        # if no query was provided. This gives a human reader a quick entry
        # point into the suite state.
        out = {
            "ok": True,
            "suite": self.suite,
            "latest_run": latest,
            "governance": governance,
            "warnings": governance["warnings"],
            "route": route.__dict__,
            "summary": (
                f"{self.suite} is ready for inspection. Read the latest summary "
                "first and then only open detailed artifacts where you still "
                "need proof."
            ),
            "uncertainty": [],
        }

        # If the caller supplied a query, enrich the inspection with a focused
        # context pack so the result becomes problem-oriented rather than only a
        # generic "latest status" view.
        if query:
            pack = self.index.build_context_pack(query, suite_scope=[self.suite], audience="developer")
            out.update(
                {
                    "query": query,
                    "hit_count": len(pack.hits),
                    "summary": pack.summary,
                    "artifact_paths": pack.artifact_paths,
                    "evidence_confidence": pack.evidence_confidence,
                    "priorities": pack.priorities,
                    "next_steps": pack.next_steps,
                    "uncertainty": pack.uncertainty,
                }
            )

        return self._attach_status_page("inspect", out, governance=governance)

    @abstractmethod
    def audit(self, target_repo_root: str) -> dict:
        """Run the suite-specific audit against a target repository.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        raise NotImplementedError

    def explain(self, audience: str = "developer") -> dict[str, Any]:
        """Explain the most recent run in audience-appropriate language.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            audience: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        latest = self.registry.latest_run(self.suite)
        governance = self.self_governance_status()

        # Explaining without any prior run would only fabricate confidence, so
        # the method stays explicit and returns a controlled negative result.
        if not latest:
            payload = {"ok": False, "reason": "no_runs", "suite": self.suite, "governance": governance}
            return self._attach_status_page("explain", payload, governance=governance)

        # Gather the factual building blocks that the explanation will stand on:
        # artifacts from the registry, a journal summary, and a route decision.
        artifacts = self.registry.artifacts_for_run(latest["run_id"])
        journal_summary = self.journal.summarize(self.suite, latest["run_id"])
        route = self.router.route("explain", audience=audience, evidence_strength="moderate")

        # Build a compact neutral base summary first. Audience-specific phrasing
        # is layered on top instead of duplicating the whole explanation logic.
        base = f"Suite {self.suite} last ran in mode {latest['mode']} with status {latest['status']}."
        if artifacts:
            base += f" Produced {len(artifacts)} artifacts."

        # The explanation is tuned for the audience rather than merely dumped.
        # This keeps manager/operator/developer outputs useful in their own way.
        if audience == "manager":
            summary = (
                f"{self.suite} has a fresh result. Start with the simple summary "
                "and only open deeper artifacts where the summary still feels incomplete."
            )
        elif audience == "operator":
            summary = base + " Review the journal and generated artifacts before outward application."
        else:
            summary = base + " Start with the top artifacts and validate the next action against the latest evidence."

        payload = {
            "ok": True,
            "suite": self.suite,
            "run_id": latest["run_id"],
            "summary": summary,
            "artifacts": artifacts,
            "journal_summary": journal_summary,
            "governance": governance,
            "warnings": governance["warnings"],
            "route": route.__dict__,
        }
        return self._attach_status_page("explain", payload, latest_run=latest, governance=governance)

    def prepare_context_pack(self, query: str, audience: str = "developer") -> dict[str, Any]:
        """Build a fresh context pack for the suite and the current query.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            query: Free-text input that shapes this operation.
            audience: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        latest = self.registry.latest_run(self.suite)

        # Step 1: if the latest run points at a bound target repository, refresh
        # the target scope so the context pack does not rely on stale indexed
        # evidence from a previous target snapshot.
        if latest and latest.get("target_repo_root"):
            target = Path(latest["target_repo_root"])
            if target.is_dir():
                # Clear the previous target-scope slice first. The re-indexed
                # directory should become the authoritative search surface for
                # this specific target repository.
                self.index.clear_scope(self.suite, "target", latest.get("target_repo_id"))
                self.index.index_directory(
                    suite=self.suite,
                    directory=target,
                    scope="target",
                    target_repo_id=latest.get("target_repo_id"),
                )

        # Step 2: re-index suite-owned artifacts as a separate scope. This makes
        # sure the pack can also see the newest reports, generated summaries,
        # context packs, and status surfaces produced inside the fy workspace.
        self.index.clear_scope(self.suite, "suite")
        self.index.index_directory(suite=self.suite, directory=self.hub_dir, scope="suite")

        # Step 3: prepare the output directory inside the suite-owned generated
        # area. Context packs remain internal first and only become outward
        # material if someone explicitly exports or applies them later.
        out_dir = self.hub_dir / "generated" / "context_packs"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: route the task through the model router so the pack is built
        # under a strict, reproducible profile rather than an ad-hoc mode.
        route = self.router.route(
            "prepare_context_pack",
            audience=audience,
            evidence_strength="moderate",
            reproducibility="strict",
        )

        # Step 5: build and persist the pack. The payload already contains the
        # retrieved evidence, summary, priorities, and next-step suggestions.
        payload = self.context_packs.build_and_write(
            suite=self.suite,
            query=query,
            suite_scope=[self.suite],
            audience=audience,
            out_dir=out_dir,
        )
        payload.update(
            {
                "ok": True,
                "suite": self.suite,
                "query": query,
                "audience": audience,
                "route": route.__dict__,
            }
        )

        # Step 6: attach a status page so the freshly built pack is reflected in
        # the suite's simple-language status surfaces as well.
        return self._attach_status_page("prepare-context-pack", payload, latest_run=latest)

    def compare_runs(self, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        """Compare two historical runs of the same suite.

        Control flow branches on the parsed state rather than relying on
        one linear path.

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
        delta = self.registry.compare_runs(left_run_id, right_run_id)
        if not delta:
            return self._attach_status_page(
                "compare-runs",
                {"ok": False, "reason": "run_not_found", "suite": self.suite},
            )

        # These warnings explain *why* the comparison might matter more than a
        # normal drift view. Target changes and mode changes are both strong
        # signals that the reader should inspect the delta more carefully.
        warnings: list[str] = []
        if delta.target_repo_changed or delta.target_repo_id_changed:
            warnings.append("target_repo_changed_between_runs")
        if delta.mode_changed:
            warnings.append("mode_changed_between_runs")

        route = self.router.route("compare", evidence_strength="moderate")
        payload = {
            "ok": True,
            "suite": self.suite,
            **delta.__dict__,
            "warnings": warnings,
            "route": route.__dict__,
            "summary": (
                f"Compared {left_run_id} with {right_run_id}. Focus first on "
                "changed artifacts, review-state changes, and any target or "
                "mode differences."
            ),
        }
        return self._attach_status_page("compare-runs", payload)

    def clean(self, mode: str = "standard") -> dict[str, Any]:
        """Remove transient suite data without destroying canonical
        workspace state.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            mode: Named mode for this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        removed = []

        # Cleaning always starts with cache because it is the lowest-risk
        # transient surface and the most common first step when a suite feels
        # stale or noisy.
        cache_dir = self.root / ".fydata" / "cache"
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            removed.append(str(cache_dir.relative_to(self.root)))

        # Generated outputs are removed only in stronger cleaning modes because
        # they are still useful evidence for many readers.
        if mode in {"aggressive", "generated"}:
            gen_dir = self.hub_dir / "generated"
            if gen_dir.is_dir():
                shutil.rmtree(gen_dir)
                gen_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(gen_dir.relative_to(self.root)))

        # The strongest cleaning mode also clears suite run directories, which is
        # more disruptive and therefore intentionally opt-in.
        if mode == "aggressive":
            run_dir = self.root / ".fydata" / "runs" / self.suite
            if run_dir.is_dir():
                shutil.rmtree(run_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(run_dir.relative_to(self.root)))

        payload = {"ok": True, "suite": self.suite, "mode": mode, "removed": removed}
        return self._attach_status_page("clean", payload)

    def reset(self, mode: str = "soft") -> dict[str, Any]:
        """Reset suite state to a cleaner baseline.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            mode: Named mode for this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        removed = []

        # A soft or hard reset clears suite-local state so the suite can rebuild
        # from a more trustworthy baseline.
        if mode in {"soft", "hard"}:
            state_dir = self.hub_dir / "state"
            if state_dir.is_dir():
                shutil.rmtree(state_dir)
                state_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(state_dir.relative_to(self.root)))

        # A hard or reindex reset also removes the semantic index database so the
        # search surface can be rebuilt from scratch.
        if mode in {"hard", "reindex-reset"}:
            index_db = self.root / ".fydata" / "index" / "semantic_index.db"
            if index_db.exists():
                index_db.unlink()
                removed.append(str(index_db.relative_to(self.root)))
                self.index = SemanticIndex(self.root)

        # A fully hard reset additionally drops the outward binding. This is the
        # cleanest reset, but also the one with the highest behavioral impact.
        if mode == "hard":
            bind = binding_path(self.root, self.suite)
            if bind.exists():
                bind.unlink()
                removed.append(str(bind.relative_to(self.root)))

        payload = {"ok": True, "suite": self.suite, "mode": mode, "removed": removed}
        return self._attach_status_page("reset", payload)

    def triage(self, query: str | None = None) -> dict[str, Any]:
        """Rank likely problem areas before a user takes action.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            query: Free-text input that shapes this operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        route = self.router.route(
            "triage",
            ambiguity="high" if query else "low",
            evidence_strength="weak" if not query else "moderate",
        )
        latest = self.registry.latest_run(self.suite)
        hints = []
        if latest:
            artifacts = self.registry.artifacts_for_run(latest["run_id"])
            hints = [item["path"] for item in artifacts[:5]]

        # Triage is intentionally advisory. It should point the reader toward the
        # most useful next evidence, not silently convert uncertainty into action.
        payload = {
            "ok": True,
            "suite": self.suite,
            "route": route.__dict__,
            "query": query or "",
            "latest_hints": hints,
            "summary": (
                "Triage is for ranking problems before action. It should help "
                "you decide what to inspect next, not silently fix risky issues."
            ),
            "decision": {
                "lane": "likely_but_review" if query else "abstain",
                "recommended_action": "Use triage to rank evidence first. Do not treat it as proof on its own.",
                "uncertainty_flags": ["query_missing"] if not query else [],
            },
            "uncertainty": ["query_missing"] if not query else [],
        }
        return self._attach_status_page("triage", payload)

    def prepare_fix(self, finding_ids: list[str]) -> dict[str, Any]:
        """Prepare an advisory-only fix plan for explicit findings.

        Args:
            finding_ids: Primary finding ids used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        route = self.router.route(
            "prepare_fix",
            ambiguity="high" if not finding_ids else "low",
            evidence_strength="weak" if not finding_ids else "moderate",
        )
        decision_lane = "abstain" if not finding_ids else "likely_but_review"

        # The fix-preparation layer never applies changes itself. Its job is to
        # convert explicit findings into a human-reviewable plan.
        payload = {
            "ok": True,
            "suite": self.suite,
            "route": route.__dict__,
            "finding_ids": finding_ids,
            "advisory_only": True,
            "decision": {
                "lane": decision_lane,
                "recommended_action": "Prepare the fix plan, then review it before any outward application.",
                "uncertainty_flags": ["no_finding_ids"] if not finding_ids else [],
            },
            "uncertainty": ["no_finding_ids"] if not finding_ids else [],
        }
        return self._attach_status_page("prepare-fix", payload)

    def self_audit(self) -> dict[str, Any]:
        """Audit whether the suite itself is internally healthy.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        governance = self.self_governance_status()
        latest = self.registry.latest_run(self.suite)
        latest_artifacts = self.registry.artifacts_for_run(latest["run_id"]) if latest else []

        # Self-audit is the suite’s own honesty layer. It summarizes whether the
        # suite is internally healthy before anyone trusts it for outward work.
        payload = {
            "ok": governance["ok"],
            "suite": self.suite,
            "summary": (
                "Self-audit checks whether this suite is internally well "
                "formed, documented, and ready for outward work."
            ),
            "governance": governance,
            "latest_run": latest,
            "latest_artifact_count": len(latest_artifacts),
            "warnings": governance["warnings"],
            "blocking_reasons": governance["failures"],
        }
        return self._attach_status_page("self-audit", payload, latest_run=latest, governance=governance)

    def release_readiness(self) -> dict[str, Any]:
        """Return MVP release readiness for the suite.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        payload = suite_release_readiness(self.root, self.suite)
        payload.update(
            {
                "ok": payload["ready"],
                "summary": (
                    "Release readiness tells you if this suite is ready to "
                    "participate in an MVP release from the current workspace state."
                ),
            }
        )
        return self._attach_status_page("release-readiness", payload, latest_run=payload.get("latest_run"))

    def production_readiness(self) -> dict[str, Any]:
        """Return stricter production-readiness information for the suite.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        workspace_payload = workspace_production_readiness(self.root)
        suite_payload = suite_release_readiness(self.root, self.suite)

        # This payload deliberately keeps MVP release readiness and stricter
        # production readiness separate so readers do not collapse them into one
        # blurry yes/no answer.
        payload = {
            "ok": bool(workspace_payload.get("ok") and suite_payload.get("ready")),
            "suite": self.suite,
            "summary": (
                "Production readiness is stricter than MVP release readiness. "
                "It checks persistence, compatibility, recovery, observability, "
                "security, and release-management evidence."
            ),
            "workspace_production": {
                "ok": workspace_payload.get("ok"),
                "workspace_production_md_path": workspace_payload.get("workspace_production_md_path"),
                "top_next_steps": workspace_payload.get("top_next_steps", []),
            },
            "suite_release": suite_payload,
            "warnings": list(suite_payload.get("warnings", [])),
        }
        return self._attach_status_page(
            "production-readiness",
            payload,
            latest_run=suite_payload.get("latest_run"),
        )

    def import_bundle(self, bundle_path: str, *, legacy: bool = False) -> dict[str, Any]:
        """Default import entry point for suites without bundle import
        support.

        Args:
            bundle_path: Filesystem path to the file or directory being
                processed.
            legacy: Whether to enable this optional behavior.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        payload = {
            "ok": False,
            "suite": self.suite,
            "reason": "import_not_supported",
            "bundle_path": bundle_path,
            "legacy": legacy,
        }
        return self._attach_status_page("legacy-import" if legacy else "import", payload)

    def consolidate(
        self,
        target_repo_root: str,
        *,
        apply_safe: bool = False,
        instruction: str | None = None,
    ) -> dict[str, Any]:
        """Default consolidation entry point for suites without support.

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
        payload = {
            "ok": False,
            "suite": self.suite,
            "reason": "consolidate_not_supported",
            "apply_safe": apply_safe,
            "instruction": instruction or "",
        }
        return self._attach_status_page("consolidate", payload)

    def _start_run(self, mode: str, target_repo_root: Path) -> tuple[str, Path, str]:
        """Create a new run, enforce governance, and write opening journal
        events.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            mode: Named mode for this operation.
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            tuple[str, Path, str]:
                Filesystem path produced or resolved by
                this callable.
        """
        governance = self.self_governance_status()
        if not governance["ok"]:
            raise RuntimeError(f"governance_gate_failed:{';'.join(governance['failures'])}")

        # The target repo id becomes the stable machine-readable link between
        # the run and the outward repository the run was about.
        tgt_id = target_repo_id(target_repo_root)

        # Start the registry run first so all later artifacts and journal events
        # can attach to a real run identifier.
        run = self.registry.start_run(
            suite=self.suite,
            mode=mode,
            target_repo_root=str(target_repo_root),
            target_repo_id=tgt_id,
        )

        # Every run gets its own internal output directory under .fydata/runs.
        run_dir = internal_run_dir(self.root, self.suite, run.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        # Record the run start in the journal so later explain/compare/status
        # surfaces can reconstruct what target and mode the run began with.
        self.journal.append(
            self.suite,
            run.run_id,
            "run_started",
            {
                "mode": mode,
                "target_repo_root": str(target_repo_root),
                "target_repo_id": tgt_id,
            },
        )

        # Also record the exact governance result that allowed the run to start.
        # This matters for audits and for debugging "why was this run allowed?"
        self.journal.append(self.suite, run.run_id, "self_governance_checked", governance)
        return run.run_id, run_dir, tgt_id

    def _finish_run(self, run_id: str, status: str, summary: dict[str, Any]) -> None:
        """Write closing run journal data and mark the run complete.

        Args:
            run_id: Identifier used to select an existing run or record.
            status: Named status for this operation.
            summary: Structured data carried through this workflow.
        """
        # The journal gets the closing summary first so the run history remains
        # readable even if someone later looks at the journal without reopening
        # every artifact file.
        self.journal.append(self.suite, run_id, "run_finished", {"status": status, "summary": summary})

        # The registry is the authoritative run-tracking surface, so it receives
        # the final status after the journal has been updated.
        self.registry.finish_run(run_id, status=status)

    def _write_payload_bundle(
        self,
        *,
        run_id: str,
        run_dir: Path,
        payload: dict[str, Any],
        summary_md: str,
        role_prefix: str,
    ) -> dict[str, str]:
        """Write a JSON/Markdown artifact pair for a run payload.

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
        # Step 1: build the concrete output paths for the machine-readable JSON
        # payload and the human-readable Markdown summary that describe the same
        # run from two different reading perspectives.
        json_path = run_dir / f"{role_prefix}.json"
        md_path = run_dir / f"{role_prefix}.md"

        # Step 2: persist the full structured payload first so automation,
        # compare-runs, and status/report surfaces can consume the raw result
        # without trying to parse meaning back out of Markdown.
        write_json(json_path, payload)

        # Step 3: persist the Markdown companion so a human reader gets a much
        # smaller and friendlier entry point into the run result.
        md_path.write_text(summary_md, encoding="utf-8")

        # Step 4: register the JSON artifact in the evidence registry so later
        # explain, search, compare, and context-pack flows can find it as an
        # official run output instead of treating it as an untracked file.
        self.registry.record_artifact(
            suite=self.suite,
            run_id=run_id,
            format="json",
            role=f"{role_prefix}_json",
            path=str(json_path.relative_to(self.root)),
            payload=payload,
        )

        # Step 5: register the Markdown artifact too. The registry payload keeps
        # only a short preview because the full Markdown already lives on disk
        # and the registry should stay light enough to query quickly.
        self.registry.record_artifact(
            suite=self.suite,
            run_id=run_id,
            format="md",
            role=f"{role_prefix}_md",
            path=str(md_path.relative_to(self.root)),
            payload={"markdown_preview": summary_md[:500]},
        )

        # Step 6: return the concrete paths because CLI/report layers often need
        # to print or forward them directly without rebuilding Path objects.
        return {"json_path": str(json_path), "md_path": str(md_path)}
