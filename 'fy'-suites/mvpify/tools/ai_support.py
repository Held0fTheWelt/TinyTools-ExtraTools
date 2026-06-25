"""Ai support for mvpify.tools.

"""
from __future__ import annotations


def build_ai_context(imported: dict, plan: dict) -> dict:
    """Build ai context.

    Args:
        imported: Primary imported used by this step.
        plan: Primary plan used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    inventory = imported.get('inventory', imported)
    suites = [item['name'] for item in inventory.get('suite_signals', []) if item.get('present')]
    hv = plan.get('highest_value_next_step', {})
    return {
        'purpose': 'Help an agent import a prepared MVP into the live repository with honest orchestration across the fy suite family.',
        'import_source': imported.get('source'),
        'import_summary': {
            'artifact_count': imported.get('artifact_count', inventory.get('artifact_count', 0)),
            'docs_files': inventory.get('counters', {}).get('docs_files', 0),
            'test_files': inventory.get('counters', {}).get('test_files', 0),
            'detected_suites': suites,
            'mirrored_docs_root': imported.get('mirrored_docs_root', ''),
            'normalized_root': imported.get('normalized_root', ''),
        },
        'highest_value_next_step': hv,
        'search_hints': [
            'Find prepared MVP docs, contracts, tests, and implementation hints first.',
            'Prefer the smallest coherent insertion slice over broad speculative implementation.',
            'Use suite outputs as evidence, not as silent authority over project truth.',
            'After import, refresh tests, runtime validation, docs, and observability state.',
            'Mirror imported MVP docs so temporary implementation folders can later be removed.',
        ],
        'managed_internal_roots': {
            'mvpify_reports': 'mvpify/reports',
            'mvpify_state': 'mvpify/state',
            'mvpify_imports': 'mvpify/imports',
            'mvp_docs_imports': 'docs/MVPs/imports',
            'fy_internal_docs': 'docs',
            'fy_internal_adrs': 'docs/ADR',
        },
        'implemented_ai_mechanics': {
            'retrieval': ['semantic_index', 'context_packs', 'cross_suite_signals'],
            'decisioning': ['model_router', 'decision_policy'],
            'graph_support': ['generic inspect/audit/context/triage recipes via fy-suite'],
            'tracking': ['run_journal', 'observifyfy link if present'],
        },
    }


def build_llms_txt(ai_context: dict) -> str:
    """Build llms txt.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        ai_context: Primary ai context used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        '# MVPify AI context',
        '',
        ai_context['purpose'],
        '',
        '## Managed roots',
        '',
    ]
    for key, value in ai_context.get('managed_internal_roots', {}).items():
        lines.append(f'- {key}: {value}')
    lines.extend(['', '## Search hints', ''])
    lines.extend(f'- {item}' for item in ai_context.get('search_hints', []))
    lines.extend(['', '## Implemented AI mechanics', ''])
    for key, value in ai_context.get('implemented_ai_mechanics', {}).items():
        lines.append(f'- {key}: {", ".join(value)}')
    return "\n".join(lines) + "\n"
