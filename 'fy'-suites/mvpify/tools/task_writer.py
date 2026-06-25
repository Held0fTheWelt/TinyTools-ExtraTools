"""Task writer for mvpify.tools.

"""
from __future__ import annotations


def build_audit_task(imported: dict, plan: dict) -> str:
    """Build audit task.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        imported: Primary imported used by this step.
        plan: Primary plan used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    inventory = imported.get('inventory', imported)
    source = imported.get('source')
    lines = [
        '# MVPify audit task',
        '',
        'You are auditing an imported prepared MVP bundle before implementation work proceeds.',
        '',
        f'- Imported source: `{source}`',
        f"- Artifact count: {imported.get('artifact_count', inventory.get('artifact_count', 0))}",
        f"- Mirrored docs root: `{imported.get('mirrored_docs_root', '')}`",
        f"- Suites detected in source: {', '.join(item['name'] for item in inventory.get('suite_signals', []) if item.get('present')) or 'none'}",
        '',
        '## Required audit questions',
        '',
        '- What is already explicit in the prepared MVP versus still implied?',
        '- Which repository surfaces are supposed to change?',
        '- Which contracts, tests, docs, runtime, template, usability, and security workstreams are directly implicated?',
        '- Which imported docs must remain referenced after temporary implementation folders disappear?',
        '- What is the smallest honest next implementation slice?',
        '',
        '## Planned phases',
        '',
    ]
    # Process step one item at a time so build_audit_task applies the same rule across
    # the full collection.
    for step in plan.get('steps', []):
        lines.append(f"- `{step['phase']}:{step['suite']}` — {step['objective']}")
    lines.append('')
    return "\n".join(lines) + "\n"


def build_implementation_task(imported: dict, plan: dict) -> str:
    """Build implementation task.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        imported: Primary imported used by this step.
        plan: Primary plan used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    source = imported.get('source')
    hv = plan.get('highest_value_next_step', {})
    lines = [
        '# MVPify implementation task',
        '',
        'You are implementing a prepared MVP import into the live repository.',
        '',
        f'- Imported source: `{source}`',
        f"- Current highest-value suite after import: `{hv.get('suite', 'mvpify')}`",
        f"- Mirrored docs root: `{imported.get('mirrored_docs_root', '')}`",
        '',
        '## Operating discipline',
        '',
        '- Import the prepared MVP content into the repository without losing the existing suite governance.',
        '- Mirror imported MVP docs into docs/MVPs/imports/<id> so they stay available after temporary implementation folders are removed.',
        '- Use contractify for contract/governance attachment when relevant.',
        '- Use despaghettify to pick the smallest coherent implementation insertion path.',
        '- Use testify and runtime-specialist suites before declaring the imported work operational.',
        '- Refresh documentation and internal suite tracking after implementation.',
        '',
        '## Ordered execution plan',
        '',
    ]
    for idx, step in enumerate(plan.get('steps', []), 1):
        lines.extend([
            f'### {idx}. {step["phase"]} / {step["suite"]}',
            '',
            step['objective'],
            '',
            f"Why now: {step['why_now']}",
            '',
        ])
        if step.get('inputs'):
            lines.append('Inputs:')
            lines.extend(f'- {item}' for item in step['inputs'])
            lines.append('')
        if step.get('outputs'):
            lines.append('Expected outputs:')
            lines.extend(f'- {item}' for item in step['outputs'])
            lines.append('')
    return "\n".join(lines) + "\n"
