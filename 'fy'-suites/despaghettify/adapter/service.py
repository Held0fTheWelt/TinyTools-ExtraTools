"""Service helpers for despaghettify.adapter.

"""
from __future__ import annotations

import ast
import statistics
from pathlib import Path
from typing import Any

from fy_platform.ai.base_adapter import BaseSuiteAdapter
from fy_platform.ai.workspace import write_json, write_text
from despaghettify.tools.canonical_graph import persist_despag_graph


class DespaghettifyAdapter(BaseSuiteAdapter):
    """Adapter implementation for despaghettify workflows.
    """
    __test__ = False
    FILE_SPIKE_LINES = 350
    FUNC_SPIKE_LINES = 80
    CORE_TRANSITION_PATH_PREFIXES = ('fy_platform/ai', 'fy_platform/runtime', 'fy_platform/ir', 'fy_platform/providers', 'fy_platform/surfaces')
    CORE_CONCERNS = {
        'lifecycle': ('run_', 'start_run', 'finish_run', 'clean', 'reset'),
        'routing': ('route', 'mode', 'dispatch', 'alias'),
        'provider_policy': ('provider', 'governor', 'budget', 'cache_hit'),
        'readiness_rendering': ('readiness', 'status_page', 'render_'),
        'packaging': ('package', 'bundle', 'layout'),
        'compatibility_aliasing': ('legacy', 'compatibility', 'alias'),
    }

    def __init__(self, root: Path | None = None) -> None:
        """Initialize DespaghettifyAdapter.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        super().__init__('despaghettify', root)

    def _severity(self, value: int, *, base: int) -> str:
        """Severity the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            value: Primary value used by this step.
            base: Primary base used by this step.

        Returns:
            str:
                Rendered text produced for downstream
                callers or writers.
        """
        # Branch on value >= base * 2 so _severity only continues along the matching
        # state path.
        if value >= base * 2:
            return 'high'
        # Branch on value >= int(base * 1.3) so _severity only continues along the
        # matching state path.
        if value >= int(base * 1.3):
            return 'medium'
        return 'low'

    def _scan(self, target: Path) -> dict[str, Any]:
        """Scan the requested operation.

        The implementation iterates over intermediate items before it
        returns. Exceptions are normalized inside the implementation
        before control returns to callers.

        Args:
            target: Primary target used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        file_spikes, function_spikes, line_counts = [], [], []
        total_files = 0
        for path in target.rglob('*.py'):
            rel = path.relative_to(target).as_posix()
            parts = set(path.parts)
            if 'tests' in parts or '__pycache__' in parts or '.venv' in parts or '.fydata' in parts or 'generated' in parts or 'examples' in parts:
                continue
            if rel.startswith('mvpify/imports/') or rel.startswith('docs/MVPs/imports/'):
                continue
            total_files += 1
            text = path.read_text(encoding='utf-8', errors='replace')
            lines = text.splitlines()
            line_counts.append(len(lines))
            if len(lines) >= self.FILE_SPIKE_LINES:
                file_spikes.append({'path': rel, 'line_count': len(lines), 'category': 'local_spike_file_length', 'severity': self._severity(len(lines), base=self.FILE_SPIKE_LINES)})
            try:
                module = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(module):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and hasattr(node, 'end_lineno'):
                    span = int(node.end_lineno or node.lineno) - int(node.lineno) + 1
                    if span >= self.FUNC_SPIKE_LINES:
                        function_spikes.append({'path': rel, 'name': node.name, 'line_span': span, 'category': 'local_spike_function_length', 'severity': self._severity(span, base=self.FUNC_SPIKE_LINES)})
        median_lines = int(statistics.median(line_counts)) if line_counts else 0
        avg_lines = round(sum(line_counts) / len(line_counts), 2) if line_counts else 0.0
        sorted_counts = sorted(line_counts)
        trim = max(1, int(len(sorted_counts) * 0.1)) if len(sorted_counts) >= 5 else 0
        trimmed = sorted_counts[:-trim] if trim else sorted_counts
        trimmed_average = round(sum(trimmed) / len(trimmed), 2) if trimmed else avg_lines
        robust_baseline = median_lines if (file_spikes or function_spikes) else int(trimmed_average)
        global_category = 'low' if robust_baseline <= 120 else 'medium' if robust_baseline <= 220 else 'high'
        return {'total_python_files': total_files, 'median_file_lines': median_lines, 'average_file_lines': avg_lines, 'trimmed_average_file_lines': trimmed_average, 'file_spikes': file_spikes, 'function_spikes': function_spikes, 'global_category': global_category, 'local_spike_count': len(file_spikes) + len(function_spikes)}

    def _concerns_for_file(self, rel: str, text: str) -> list[str]:
        """Concerns for file.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            rel: Primary rel used by this step.
            text: Text content to inspect or rewrite.

        Returns:
            list[str]:
                Collection produced from the parsed or
                accumulated input data.
        """
        concerns = []
        lowered = text.lower()
        for concern, needles in self.CORE_CONCERNS.items():
            if any(token.lower() in lowered or token in rel for token in needles):
                concerns.append(concern)
        return sorted(set(concerns))

    def _ownership_map(self, target: Path) -> dict[str, Any]:
        """Ownership map.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            target: Primary target used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        owners = []
        for prefix in self.CORE_TRANSITION_PATH_PREFIXES:
            base = target / prefix
            if not base.exists():
                continue
            for path in sorted(base.rglob('*.py')):
                rel = path.relative_to(target).as_posix()
                concerns = self._concerns_for_file(rel, path.read_text(encoding='utf-8', errors='replace'))
                owners.append({'path': rel, 'concern_count': len(concerns), 'concerns': concerns, 'mixed_responsibility': len(concerns) >= 3})
        return {'ownership_rows': owners, 'mixed_responsibility_count': sum(1 for row in owners if row['mixed_responsibility'])}

    def _scan_core_transition(self, target: Path, payload: dict[str, Any]) -> dict[str, Any]:
        """Scan core transition.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            target: Primary target used by this step.
            payload: Structured data carried through this workflow.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        ownership_map = self._ownership_map(target)
        ownership_hotspots = []
        for spike in payload['file_spikes']:
            if spike['path'].startswith(self.CORE_TRANSITION_PATH_PREFIXES):
                ownership_hotspots.append({'path': spike['path'], 'issue': 'core_transition_spike', 'recommended_wave': 'extract_service_or_facade', 'severity': spike['severity']})
        for row in ownership_map['ownership_rows']:
            if row['mixed_responsibility']:
                ownership_hotspots.append({'path': row['path'], 'issue': 'mixed_responsibility_module', 'recommended_wave': 'split_by_concern', 'severity': 'medium' if row['concern_count'] < 5 else 'high'})
        payload.update({'transition_profile': 'core_transition', 'ownership_map': ownership_map, 'ownership_hotspots': ownership_hotspots})
        return payload

    def _refattening_guard_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Refattening guard report.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            payload: Structured data carried through this workflow.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        violations = []
        for spike in payload.get('file_spikes', []):
            if spike['path'].startswith(self.CORE_TRANSITION_PATH_PREFIXES):
                violations.append({'path': spike['path'], 'kind': 'file_length', 'line_count': spike['line_count'], 'limit': self.FILE_SPIKE_LINES})
        for spike in payload.get('function_spikes', []):
            if spike['path'].startswith(self.CORE_TRANSITION_PATH_PREFIXES):
                violations.append({'path': spike['path'], 'kind': 'function_length', 'name': spike['name'], 'line_span': spike['line_span'], 'limit': self.FUNC_SPIKE_LINES})
        return {'ok': not violations, 'violation_count': len(violations), 'violations': violations}

    def _wave_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Wave plan.

        The implementation iterates over intermediate items before it
        returns.

        Args:
            payload: Structured data carried through this workflow.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        actions = []
        for spike in payload['file_spikes']:
            actions.append({'kind': 'split_file', 'path': spike['path'], 'severity': spike['severity']})
        for spike in payload['function_spikes']:
            actions.append({'kind': 'extract_function', 'path': spike['path'], 'name': spike['name'], 'severity': spike['severity']})
        for hotspot in payload.get('ownership_hotspots', []):
            actions.append({'kind': hotspot['recommended_wave'], 'path': hotspot['path'], 'severity': hotspot['severity']})
        actions.sort(key=lambda item: ({'high': 0, 'medium': 1, 'low': 2}[item['severity']], item['path']))
        return {'global_category': payload['global_category'], 'action_count': len(actions), 'actions': actions}

    def audit(self, target_repo_root: str) -> dict:
        """Audit the requested operation.

        Exceptions are normalized inside the implementation before
        control returns to callers. Control flow branches on the parsed
        state rather than relying on one linear path.

        Args:
            target_repo_root: Root directory used to resolve
                repository-local paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        target = Path(target_repo_root).resolve()
        run_id, run_dir, tgt_id = self._start_run('audit', target)
        try:
            payload = self._scan(target)
            if any((target / prefix).exists() for prefix in self.CORE_TRANSITION_PATH_PREFIXES):
                payload = self._scan_core_transition(target, payload)
                payload['refattening_guard_report'] = self._refattening_guard_report(payload)
            wave = self._wave_plan(payload)
            payload['wave_plan'] = wave
            payload['target_repo_id'] = tgt_id
            graph_bundle = persist_despag_graph(workspace=self.root, repo_root=target, run_id=run_id, payload=payload)
            payload['canonical_graph'] = {'unit_count': len(graph_bundle['unit_index']['units']), 'relation_count': len(graph_bundle['relation_graph']['relations']), 'artifact_count': graph_bundle['artifact_index']['artifact_count'], 'graph_dir': graph_bundle['graph_dir'], 'export_dir': graph_bundle['export_dir'], 'run_manifest_path': graph_bundle['written_paths']['run_manifest'][1]}
            md_lines = [
                '# Despaghettify Audit',
                '',
                f"- total_python_files: {payload['total_python_files']}",
                f"- file_spikes: {len(payload['file_spikes'])}",
                f"- function_spikes: {len(payload['function_spikes'])}",
                f"- global_category: `{payload['global_category']}`",
                f"- transition_profile: `{payload.get('transition_profile', 'standard')}`",
                '',
                '## Wave plan',
                '',
            ]
            md_lines.extend(f"- `{item['kind']}` → `{item['path']}` ({item['severity']})" for item in wave['actions'][:20])
            if payload.get('ownership_hotspots'):
                md_lines.extend(['', '## Ownership hotspots', ''])
                md_lines.extend(f"- `{item['path']}` → `{item['issue']}` ({item['severity']})" for item in payload['ownership_hotspots'][:20])
            if payload.get('refattening_guard_report'):
                md_lines.extend(['', '## Refattening guard', ''])
                md_lines.append(f"- ok: `{str(payload['refattening_guard_report']['ok']).lower()}`")
                md_lines.append(f"- violation_count: `{payload['refattening_guard_report']['violation_count']}`")
            summary_md = '\n'.join(md_lines) + '\n'
            reports_root = self.root / 'despaghettify' / 'reports'
            reports_root.mkdir(parents=True, exist_ok=True)
            write_json(reports_root / 'latest_check_with_metrics.json', payload)
            write_text(reports_root / 'latest_check_with_metrics.md', summary_md)
            paths = self._write_payload_bundle(run_id=run_id, run_dir=run_dir, payload=payload, summary_md=summary_md, role_prefix='despag_audit')
            self._finish_run(run_id, 'ok', {'local_spike_count': payload['local_spike_count'], 'transition_profile': payload.get('transition_profile', 'standard'), 'target_repo_id': tgt_id})
            return {'ok': True, 'suite': self.suite, 'run_id': run_id, 'target_repo_id': tgt_id, 'local_spike_count': payload['local_spike_count'], 'transition_profile': payload.get('transition_profile', 'standard'), 'canonical_graph': payload['canonical_graph'], **paths}
        except Exception as exc:
            self._finish_run(run_id, 'failed', {'error': str(exc)})
            return {'ok': False, 'suite': self.suite, 'run_id': run_id, 'error': str(exc)}
