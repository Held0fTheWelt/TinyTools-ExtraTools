"""Graph store for fy_platform.evolution.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.evolution_contract_pack import canonical_schema_payloads, suite_names_for_ownership
from fy_platform.ai.workspace import target_repo_id, utc_now, workspace_root, write_json
from fy_platform.ai.workspace_hashing import sha256_text, slugify

ENTITY_TYPES = {
    'suite','package','module','class','function','cli-command','contract','claim','workflow','runtime-surface',
    'deployment-surface','test-surface','artifact-type','env-var','policy-rule','documentation-unit','import-package',
    'role-view','proof',
}
RELATION_TYPES = {
    'owns','emits','defines','imports','derives-from','depends-on','contains','calls','uses','extends','wraps',
    'documents','summarizes','projects','cross-links-to','stale-against','governs','proves','validates','tests',
    'constrains','violates','produces','consumes','persists','renders','publishes','matters-to-role',
    'owned-by-role','reviewed-by-role',
}
ARTIFACT_TYPES = {
    'unit-index','relation-graph','documentation-bundle','role-guide','ai-context-pack','contract-map','proof-report',
    'security-boundary-report','topology-map','cost-snapshot','drift-report','acceptance-report','run-manifest',
    'import-manifest','coverage-report','api-inventory','cli-inventory','example-index','code-doc-manifest',
    'normative-inventory','claim-proof-status',
}


def stable_unit_id(owner_suite: str, entity_type: str, normalized_name: str) -> str:
    """Stable unit id.

    Args:
        owner_suite: Primary owner suite used by this step.
        entity_type: Primary entity type used by this step.
        normalized_name: Primary normalized name used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return f"{owner_suite}:{entity_type}:{slugify(normalized_name).replace('-', '_')}"


def stable_relation_id(owner_suite: str, from_id: str, relation_type: str, to_id: str) -> str:
    """Stable relation id.

    Args:
        owner_suite: Primary owner suite used by this step.
        from_id: Identifier used to select an existing run or record.
        relation_type: Primary relation type used by this step.
        to_id: Identifier used to select an existing run or record.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    digest = sha256_text(f"{owner_suite}|{from_id}|{relation_type}|{to_id}")[:12]
    return f"{owner_suite}:relation:{relation_type}:{digest}"


def stable_artifact_id(producer_suite: str, artifact_type: str, path: str, run_id: str) -> str:
    """Stable artifact id.

    Args:
        producer_suite: Primary producer suite used by this step.
        artifact_type: Primary artifact type used by this step.
        path: Filesystem path to the file or directory being processed.
        run_id: Identifier used to select an existing run or record.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    digest = sha256_text(f"{producer_suite}|{artifact_type}|{path}|{run_id}")[:12]
    return f"{producer_suite}:artifact:{artifact_type}:{digest}"


def infer_owner_suite_for_path(path: Path, *, workspace: Path | None = None) -> str | None:
    """Infer owner suite for path.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        workspace: Primary workspace used by this step.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    root = workspace_root(workspace)
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    candidates = set(suite_names_for_ownership(root))
    return parts[0] if parts[0] in candidates else None


class CanonicalGraphStore:
    """Coordinate canonical graph store behavior.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize CanonicalGraphStore.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        self._schemas = canonical_schema_payloads(self.root)

    @property
    def schemas(self) -> dict[str, dict[str, Any]]:
        """Schemas the requested operation.

        Returns:
            dict[str, dict[str, Any]]:
                Structured payload describing the
                outcome of the operation.
        """
        return dict(self._schemas)

    def run_dir(self, run_id: str) -> Path:
        """Run dir.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            run_id: Identifier used to select an existing run or record.

        Returns:
            Path:
                Filesystem path produced or resolved by
                this callable.
        """
        path = self.root / '.fydata' / 'evolution_graph' / 'runs' / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def export_dir(self, suite: str, *, target_repo_root: Path, run_id: str) -> Path:
        """Export dir.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            suite: Primary suite used by this step.
            target_repo_root: Root directory used to resolve
                repository-local paths.
            run_id: Identifier used to select an existing run or record.

        Returns:
            Path:
                Filesystem path produced or resolved by
                this callable.
        """
        tgt_id = target_repo_id(target_repo_root)
        path = self.root / suite / 'generated' / tgt_id / run_id / 'evolution_graph'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_named(self, base: Path, name: str, payload: Any) -> Path:
        """Write named.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            base: Primary base used by this step.
            name: Primary name used by this step.
            payload: Structured data carried through this workflow.

        Returns:
            Path:
                Filesystem path produced or resolved by
                this callable.
        """
        path = base / name
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(path, payload)
        return path

    def persist_bundle(
        self, *, suite: str, run_id: str, command: str, mode: str, lane: str, target_repo_root: Path,
        units: list[dict[str, Any]], relations: list[dict[str, Any]], artifacts: list[dict[str, Any]],
        validation_summary: dict[str, Any], residual_notes: list[str] | None = None, tool_chain: list[str] | None = None,
        actor: str = 'fy_platform', status: str = 'complete', started_at: str | None = None, finished_at: str | None = None,
    ) -> dict[str, Any]:
        """Persist bundle.

        The implementation iterates over intermediate items before it
        returns.

        Args:
            suite: Primary suite used by this step.
            run_id: Identifier used to select an existing run or record.
            command: Named command for this operation.
            mode: Named mode for this operation.
            lane: Primary lane used by this step.
            target_repo_root: Root directory used to resolve
                repository-local paths.
            units: Primary units used by this step.
            relations: Primary relations used by this step.
            artifacts: Primary artifacts used by this step.
            validation_summary: Primary validation summary used by this
                step.
            residual_notes: Primary residual notes used by this step.
            tool_chain: Primary tool chain used by this step.
            actor: Primary actor used by this step.
            status: Named status for this operation.
            started_at: Primary started at used by this step.
            finished_at: Primary finished at used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        graph_dir = self.run_dir(run_id)
        export_dir = self.export_dir(suite, target_repo_root=target_repo_root, run_id=run_id)
        started = started_at or utc_now()
        finished = finished_at or utc_now()
        unit_index = {'schema_name': 'fy_unit.schema.json', 'schema_count': len(units), 'generated_at': finished, 'units': units}
        relation_graph = {'schema_name': 'relation.schema.json', 'relation_count': len(relations), 'generated_at': finished, 'relations': relations}
        artifact_index = {'schema_name': 'artifact.schema.json', 'artifact_count': len(artifacts), 'generated_at': finished, 'artifacts': artifacts}
        manifest = {
            'run_id': run_id, 'command': command, 'mode': mode, 'lane': lane, 'status': status, 'started_at': started,
            'finished_at': finished, 'actor': actor, 'policy_mode': 'deterministic-first', 'tool_chain': tool_chain or ['fy_platform', suite],
            'emitted_artifacts': [item['artifact_id'] for item in artifacts], 'validation_summary': validation_summary,
            'cost_summary': {}, 'residual_notes': residual_notes or [],
        }
        written = {}
        for base in (graph_dir, export_dir):
            written.setdefault('unit_index', []).append(str(self._write_named(base, 'unit_index.json', unit_index).relative_to(self.root)))
            written.setdefault('relation_graph', []).append(str(self._write_named(base, 'relation_graph.json', relation_graph).relative_to(self.root)))
            written.setdefault('artifact_index', []).append(str(self._write_named(base, 'artifact_index.json', artifact_index).relative_to(self.root)))
            written.setdefault('run_manifest', []).append(str(self._write_named(base, 'run_manifest.json', manifest).relative_to(self.root)))
        return {'unit_index': unit_index, 'relation_graph': relation_graph, 'artifact_index': artifact_index, 'run_manifest': manifest, 'written_paths': written, 'graph_dir': str(graph_dir.relative_to(self.root)), 'export_dir': str(export_dir.relative_to(self.root))}
