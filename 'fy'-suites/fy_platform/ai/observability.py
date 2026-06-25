"""Observability for fy_platform.ai.

"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from fy_platform.ai.contracts import OBSERVABILITY_SCHEMA_VERSION
from fy_platform.ai.workspace import utc_now, workspace_root


class ObservabilityStore:
    """Coordinate observability store behavior.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize ObservabilityStore.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        self.metrics_dir = self.root / '.fydata' / 'metrics'
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.commands_path = self.metrics_dir / 'commands.jsonl'
        self.routes_path = self.metrics_dir / 'routes.jsonl'

    def _append(self, path: Path, payload: dict[str, Any]) -> None:
        """Append the requested operation.

        Args:
            path: Filesystem path to the file or directory being
                processed.
            payload: Structured data carried through this workflow.
        """
        with path.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + '\n')

    def record_command(self, *, suite: str, command: str, exit_code: int, duration_ms: int, ok: bool, warnings_count: int = 0, errors_count: int = 0, target_repo_id: str | None = None, active_profile: str = '') -> None:
        """Record command.

        Args:
            suite: Primary suite used by this step.
            command: Named command for this operation.
            exit_code: Primary exit code used by this step.
            duration_ms: Primary duration ms used by this step.
            ok: Whether to enable this optional behavior.
            warnings_count: Primary warnings count used by this step.
            errors_count: Primary errors count used by this step.
            target_repo_id: Identifier used to select an existing run or
                record.
        """
        self._append(self.commands_path, {
            'schema_version': OBSERVABILITY_SCHEMA_VERSION,
            'ts': utc_now(),
            'suite': suite,
            'command': command,
            'exit_code': exit_code,
            'ok': ok,
            'duration_ms': duration_ms,
            'warnings_count': warnings_count,
            'errors_count': errors_count,
            'target_repo_id': target_repo_id,
            'active_profile': active_profile,
        })

    def record_route(self, *, suite: str, command: str, route: dict[str, Any] | None) -> None:
        """Record route.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            suite: Primary suite used by this step.
            command: Named command for this operation.
            route: Primary route used by this step.
        """
        if not route:
            return
        self._append(self.routes_path, {
            'schema_version': OBSERVABILITY_SCHEMA_VERSION,
            'ts': utc_now(),
            'suite': suite,
            'command': command,
            'selected_tier': route.get('selected_tier'),
            'selected_model': route.get('selected_model'),
            'budget_class': route.get('budget_class'),
            'estimated_cost_class': route.get('estimated_cost_class'),
            'reproducibility_mode': route.get('reproducibility_mode'),
            'safety_mode': route.get('safety_mode'),
            'governor_allowed': route.get('governor_allowed'),
            'governor_reason': route.get('governor_reason'),
            'governor_policy_lane': route.get('governor_policy_lane'),
            'governor_cache_hit': route.get('governor_cache_hit'),
        })

    def _read_lines(self, path: Path) -> list[dict[str, Any]]:
        """Read lines.

        The implementation iterates over intermediate items before it
        returns. Exceptions are normalized inside the implementation
        before control returns to callers.

        Args:
            path: Filesystem path to the file or directory being
                processed.

        Returns:
            list[dict[str, Any]]:
                Structured payload describing the
                outcome of the operation.
        """
        if not path.is_file():
            return []
        out = []
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def summarize(self) -> dict[str, Any]:
        """Summarize the requested operation.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        commands = self._read_lines(self.commands_path)
        routes = self._read_lines(self.routes_path)
        by_suite = Counter(item['suite'] for item in commands)
        by_command = Counter(f"{item['suite']}::{item['command']}" for item in commands)
        by_exit = Counter(str(item['exit_code']) for item in commands)
        by_model = Counter(item['selected_model'] for item in routes if item.get('selected_model'))
        by_profile = Counter(item.get('active_profile', '') for item in commands if item.get('active_profile'))
        durations = [int(item.get('duration_ms', 0)) for item in commands]
        return {
            'schema_version': OBSERVABILITY_SCHEMA_VERSION,
            'command_event_count': len(commands),
            'route_event_count': len(routes),
            'suite_counts': dict(sorted(by_suite.items())),
            'command_counts': dict(sorted(by_command.items())),
            'exit_code_counts': dict(sorted(by_exit.items())),
            'model_counts': dict(sorted(by_model.items())),
            'active_profile_counts': dict(sorted(by_profile.items())),
            'avg_duration_ms': round(sum(durations) / len(durations), 2) if durations else 0.0,
            'max_duration_ms': max(durations) if durations else 0,
            'has_metrics': bool(commands or routes),
        }
