"""Service helpers for fy_platform.ai.context_packs.

"""
from __future__ import annotations

from pathlib import Path

from fy_platform.ai.cross_suite_intelligence import collect_cross_suite_signals
from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.workspace import write_json, write_text, workspace_root


class ContextPackService:
    """Service object for context pack operations.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize ContextPackService.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        self.index = SemanticIndex(self.root)

    def build_and_write(self, *, suite: str, query: str, suite_scope: list[str], audience: str, out_dir: Path) -> dict:
        """Build and write.

        This callable writes or records artifacts as part of its
        workflow. The implementation iterates over intermediate items
        before it returns.

        Args:
            suite: Primary suite used by this step.
            query: Free-text input that shapes this operation.
            suite_scope: Primary suite scope used by this step.
            audience: Free-text input that shapes this operation.
            out_dir: Root directory used to resolve repository-local
                paths.

        Returns:
            dict:
                Structured payload describing the
                outcome of the operation.
        """
        pack = self.index.build_context_pack(query, suite_scope=suite_scope, audience=audience)
        cross_suite = collect_cross_suite_signals(self.root, suite, query=query)
        json_path = out_dir / f'{suite}_context_pack.json'
        md_path = out_dir / f'{suite}_context_pack.md'
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(json_path, {
            'pack_id': pack.pack_id,
            'query': pack.query,
            'suite_scope': pack.suite_scope,
            'audience': pack.audience,
            'summary': pack.summary,
            'artifact_paths': pack.artifact_paths,
            'related_suites': pack.related_suites,
            'evidence_confidence': pack.evidence_confidence,
            'priorities': pack.priorities,
            'next_steps': pack.next_steps,
            'uncertainty': pack.uncertainty,
            'cross_suite': cross_suite,
            'hits': [h.__dict__ for h in pack.hits],
        })
        lines = [
            f'# Context Pack — {suite}',
            '',
            f'Query: `{pack.query}`',
            f'Audience: `{pack.audience}`',
            f'Evidence confidence: `{pack.evidence_confidence}`',
            '',
            pack.summary,
            '',
            '## Priorities',
            '',
        ]
        lines.extend(f'- {item}' for item in pack.priorities)
        lines.extend(['', '## Most-Recent-Next-Steps', ''])
        lines.extend(f'- {item}' for item in pack.next_steps)
        if pack.uncertainty:
            lines.extend(['', '## Uncertainty', ''])
            lines.extend(f'- {item}' for item in pack.uncertainty)
        lines.extend(['', '## Artifact paths', ''])
        lines.extend(f'- `{path}`' for path in pack.artifact_paths)
        if cross_suite.get('signals'):
            lines.extend(['', '## Cross-suite signals', ''])
            for signal in cross_suite['signals']:
                lines.append(f"- `{signal['suite']}`: {signal.get('status_summary') or 'No summary available.'}")
                for step in signal.get('next_steps', [])[:2]:
                    lines.append(f'  - next: {step}')
        lines.append('')
        for hit in pack.hits:
            lines.extend([
                f'## {hit.source_path}',
                '',
                f'- suite: {hit.suite}',
                f'- scope: {hit.scope}',
                f'- lexical: {hit.score_lexical}',
                f'- semantic: {hit.score_semantic}',
                f'- hybrid: {hit.score_hybrid}',
                f'- recency: {hit.score_recency}',
                f'- suite_affinity: {hit.score_suite_affinity}',
                f'- confidence: {hit.confidence}',
                f'- rationale: {hit.rationale}',
                '',
                hit.excerpt,
                '',
            ])
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        write_text(md_path, '\n'.join(lines).strip() + '\n')
        return {
            'json_path': str(json_path),
            'md_path': str(md_path),
            'hit_count': len(pack.hits),
            'summary': pack.summary,
            'artifact_paths': pack.artifact_paths,
            'evidence_confidence': pack.evidence_confidence,
            'priorities': pack.priorities,
            'next_steps': pack.next_steps,
            'uncertainty': pack.uncertainty,
            'cross_suite': cross_suite,
            'related_suites': pack.related_suites,
        }
