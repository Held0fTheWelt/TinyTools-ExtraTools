"""Catalog for fy_platform.ir.

"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import workspace_root
from fy_platform.ir.ids import new_ir_id


class IRCatalog:
    """Coordinate ircatalog behavior.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize IRCatalog.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        self.ir_root = self.root / '.fydata' / 'ir'
        self.ir_root.mkdir(parents=True, exist_ok=True)

    def new_id(self, namespace: str) -> str:
        """New id.

        Args:
            namespace: Primary namespace used by this step.

        Returns:
            str:
                Rendered text produced for downstream
                callers or writers.
        """
        return new_ir_id(namespace)

    def _normalize(self, payload: Any) -> dict[str, Any]:
        """Normalize the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            payload: Structured data carried through this workflow.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        if is_dataclass(payload):
            return asdict(payload)
        return dict(payload)

    def _write_json(self, rel: str, payload: dict[str, Any]) -> None:
        """Write json.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            rel: Primary rel used by this step.
            payload: Structured data carried through this workflow.
        """
        path = self.ir_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def _read_json(self, rel: str) -> dict[str, Any]:
        """Read json.

        Args:
            rel: Primary rel used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        path = self.ir_root / rel
        return json.loads(path.read_text(encoding='utf-8'))

    def _write_named(self, bucket: str, item_id: str, payload: Any) -> None:
        """Write named.

        Args:
            bucket: Primary bucket used by this step.
            item_id: Identifier used to select an existing run or
                record.
            payload: Structured data carried through this workflow.
        """
        self._write_json(f'{bucket}/{item_id}.json', self._normalize(payload))

    def write_snapshot(self, snapshot) -> None:
        """Write snapshot.

        Args:
            snapshot: Primary snapshot used by this step.
        """
        self._write_named('snapshots', snapshot.snapshot_id, snapshot)

    def write_repo_asset(self, asset) -> None:
        """Write repo asset.

        Args:
            asset: Primary asset used by this step.
        """
        self._write_named('repo_assets', asset.asset_id, asset)

    def write_structure_finding(self, finding) -> None:
        """Write structure finding.

        Args:
            finding: Structured data carried through this workflow.
        """
        self._write_named('structure_findings', finding.finding_id, finding)

    def write_decision(self, decision) -> None:
        """Write decision.

        Args:
            decision: Primary decision used by this step.
        """
        self._write_named('decisions', decision.decision_id, decision)

    def write_review_task(self, review_task) -> None:
        """Write review task.

        Args:
            review_task: Primary review task used by this step.
        """
        self._write_named('review_tasks', review_task.review_task_id, review_task)

    def write_lane_execution(self, record) -> None:
        """Write lane execution.

        Args:
            record: Structured data carried through this workflow.
        """
        self._write_named('lane_executions', record.lane_execution_id, record)

    def update_lane_execution(self, lane_execution_id: str, **patch: Any) -> None:
        """Update lane execution.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            lane_execution_id: Identifier used to select an existing run
                or record.
            **patch: Primary patch used by this step.
        """
        rel = f'lane_executions/{lane_execution_id}.json'
        payload = self._read_json(rel)
        detail_append = patch.pop('detail_append', None)
        if detail_append:
            payload.setdefault('detail', {}).update(detail_append)
        payload.update(patch)
        self._write_json(rel, payload)

    def write_provider_call(self, provider_call) -> None:
        """Write provider call.

        Args:
            provider_call: Primary provider call used by this step.
        """
        self._write_named('provider_calls', provider_call.provider_call_id, provider_call)

    def write_surface_alias(self, alias) -> None:
        """Write surface alias.

        Args:
            alias: Primary alias used by this step.
        """
        self._write_named('surface_aliases', alias.alias_id, alias)
