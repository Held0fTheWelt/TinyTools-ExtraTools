"""
MVPify intake inspection and material preservation helpers.

This module is responsible for turning imported MVP/package bundles into
a restartable normalized handoff tree while preserving provenance and
enough structure for downstream graph-native consumption.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import sha256_text, slugify, utc_now, write_json, write_text
from .models import MVPArtifact, SuiteSignal
from .repo_paths import docs_imports_root, imports_root

KEY_FILES = {
    'README.md': 'project_readme',
    'docker-compose.yml': 'docker_stack',
    'docker-up.py': 'docker_entrypoint',
    'fy-manifest.yaml': 'fy_manifest',
    'tests/run_tests.py': 'test_runner',
    'pyproject.toml': 'python_project',
}

SUITE_NAMES = (
    'contractify', 'despaghettify', 'docify', 'documentify', 'dockerify',
    'testify', 'templatify', 'usabilify', 'securify', 'observifyfy', 'mvpify',
)

DOC_SUFFIXES = {'.md', '.txt', '.rst'}
JSONLIKE_SUFFIXES = {'.json', '.yaml', '.yml', '.toml'}
STARTER_HINTS = {'bootstrap', 'pilot', 'starter', 'runbook'}
TASK_HINTS = {'task', 'prompt', 'implementation', 'audit'}
AI_HINTS = {'ai', 'context', 'contexts', 'prompt', 'prompts', 'llms'}
IR_HINTS = {'ir'}


def _scan_root(root: Path) -> dict:
    """Scan root.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    artifacts: list[MVPArtifact] = []
    counters = Counter()
    doc_files: list[str] = []
    implementation_files: list[str] = []
    # Process path one item at a time so _scan_root applies the same rule across the
    # full collection.
    for path in root.rglob('*'):
        # Branch on path.is_dir() so _scan_root only continues along the matching state
        # path.
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        # Process (suffix, kind) one item at a time so _scan_root applies the same rule
        # across the full collection.
        for suffix, kind in KEY_FILES.items():
            # Branch on rel.endswith(suffix) so _scan_root only continues along the
            # matching state path.
            if rel.endswith(suffix):
                artifacts.append(MVPArtifact(rel, kind, 'key surface'))
                counters[kind] += 1
        # Branch on '/docs/' in f'/{rel}/' or rel.startswith('doc... so _scan_root only
        # continues along the matching state path.
        if '/docs/' in f'/{rel}/' or rel.startswith('docs/'):
            counters['docs_files'] += 1
            doc_files.append(rel)
        # Branch on 'MVP' in rel or 'implementation' in rel.lower() so _scan_root only
        # continues along the matching state path.
        if 'MVP' in rel or 'implementation' in rel.lower():
            implementation_files.append(rel)
        # Branch on '/tests/' in f'/{rel}/' or rel.startswith('te... so _scan_root only
        # continues along the matching state path.
        if '/tests/' in f'/{rel}/' or rel.startswith('tests/'):
            counters['test_files'] += 1
        # Branch on '/.github/workflows/' in f'/{rel}/' so _scan_root only continues
        # along the matching state path.
        if '/.github/workflows/' in f'/{rel}/':
            counters['workflow_files'] += 1
        # Branch on "'fy'-suites/" in rel or rel.startswith("'fy'... so _scan_root only
        # continues along the matching state path.
        if "'fy'-suites/" in rel or rel.startswith("'fy'-suites/"):
            counters['fy_suite_files'] += 1
        # Branch on rel.endswith('.md') so _scan_root only continues along the matching
        # state path.
        if rel.endswith('.md'):
            counters['markdown_files'] += 1
        # Branch on rel.endswith('.py') so _scan_root only continues along the matching
        # state path.
        if rel.endswith('.py'):
            counters['python_files'] += 1
        # Branch on rel.endswith('.json') so _scan_root only continues along the
        # matching state path.
        if rel.endswith('.json'):
            counters['json_files'] += 1
        # Branch on rel.endswith('.yml') or rel.endswith('.yaml') so _scan_root only
        # continues along the matching state path.
        if rel.endswith('.yml') or rel.endswith('.yaml'):
            counters['yaml_files'] += 1
    suite_signals = []
    # Process suite one item at a time so _scan_root applies the same rule across the
    # full collection.
    for suite in SUITE_NAMES:
        evidence = []
        # Process path one item at a time so _scan_root applies the same rule across the
        # full collection.
        for path in root.rglob('*'):
            rel = path.relative_to(root).as_posix()
            # Branch on suite in rel so _scan_root only continues along the matching
            # state path.
            if suite in rel:
                evidence.append(rel)
                # Branch on len(evidence) == 5 so _scan_root only continues along the
                # matching state path.
                if len(evidence) == 5:
                    break
        suite_signals.append(SuiteSignal(suite, bool(evidence), evidence, relevance='primary' if suite in {'contractify', 'despaghettify', 'mvpify'} else 'supporting'))
    return {
        'root': str(root),
        'artifact_count': sum(1 for _ in root.rglob('*') if _.is_file()),
        'artifacts': [a.to_dict() for a in artifacts],
        'counters': dict(counters),
        'suite_signals': [s.to_dict() for s in suite_signals],
        'mvp_candidate_roots': [p.relative_to(root).as_posix() for p in root.iterdir() if p.is_dir()][:20],
        'doc_files': sorted(doc_files)[:200],
        'implementation_files': sorted(implementation_files)[:200],
    }


def _detect_extracted_root(base: Path) -> Path:
    """Detect extracted root.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        base: Primary base used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    entries = [p for p in base.iterdir() if p.name != '__MACOSX']
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return base


def _prepare_source(*, source_root: str = '', mvp_zip: str = '') -> tuple[Path, tempfile.TemporaryDirectory[str] | None, str]:
    """Prepare source.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        source_root: Root directory used to resolve repository-local
            paths.
        mvp_zip: Primary mvp zip used by this step.

    Returns:
        tuple[Path, tempfile.TemporaryDirectory[str] | None, str]:
            Filesystem path produced or resolved by this
            callable.
    """
    if bool(source_root) == bool(mvp_zip):
        raise ValueError('Provide exactly one of source_root or mvp_zip')
    if source_root:
        return Path(source_root).resolve(), None, str(Path(source_root).resolve())
    zip_path = Path(mvp_zip).resolve()
    temp = tempfile.TemporaryDirectory(prefix='mvpify-import-')
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(temp.name)
    root = _detect_extracted_root(Path(temp.name))
    return root, temp, str(zip_path)


def inspect_source(*, source_root: str = '', mvp_zip: str = '') -> dict:
    """Inspect source.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        source_root: Root directory used to resolve repository-local
            paths.
        mvp_zip: Primary mvp zip used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    root, temp, source = _prepare_source(source_root=source_root, mvp_zip=mvp_zip)
    try:
        payload = _scan_root(root)
        payload['source_mode'] = 'directory' if source_root else 'zip'
        payload['source'] = source
        return payload
    finally:
        if temp is not None:
            temp.cleanup()


def _is_doc_like(rel: str, path: Path) -> bool:
    """Return whether doc like.

    Args:
        rel: Primary rel used by this step.
        path: Filesystem path to the file or directory being processed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return path.suffix.lower() in DOC_SUFFIXES or rel.startswith('docs/') or '/docs/' in f'/{rel}/'


def _classify_preserved_file(rel: str, path: Path) -> str | None:
    """Classify preserved file.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        rel: Primary rel used by this step.
        path: Filesystem path to the file or directory being processed.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    rel_path = Path(rel)
    parts = [part.lower() for part in rel_path.parts]
    name = rel_path.name.lower()
    suffix = rel_path.suffix.lower()

    if parts and parts[0] == 'docs':
        return 'docs'
    if 'reports' in parts:
        return 'reports'
    if (parts and parts[0] == 'schemas') or name.endswith('.schema.json'):
        return 'schemas'
    if parts and parts[0] == 'examples':
        return 'examples'
    if parts and (parts[0].endswith('_specs') or parts[0] == '09_tool_specs'):
        return 'tool_specs'
    if any(token in name for token in TASK_HINTS) and suffix in DOC_SUFFIXES | JSONLIKE_SUFFIXES:
        return 'tasks'
    if any(token in parts for token in AI_HINTS) or any(token in name for token in AI_HINTS):
        return 'ai_context'
    if any(token in parts for token in IR_HINTS):
        return 'ir'
    if any(token in parts for token in STARTER_HINTS) or any(token in name for token in STARTER_HINTS):
        return 'bootstrap'
    if len(rel_path.parts) == 1 and (suffix in DOC_SUFFIXES | JSONLIKE_SUFFIXES or name in {'manifest.txt', 'readme.md'}):
        return 'root_docs'
    if suffix in JSONLIKE_SUFFIXES and len(rel_path.parts) <= 2:
        return 'metadata'
    return None


def _copy_preserved_file(src: Path, dst: Path, refs: list[dict[str, Any]], *, kind: str, source_root: Path, normalized_root: Path) -> None:
    """Copy preserved file.

    This callable writes or records artifacts as part of its workflow.

    Args:
        src: Primary src used by this step.
        dst: Primary dst used by this step.
        refs: Primary refs used by this step.
        kind: Primary kind used by this step.
        source_root: Root directory used to resolve repository-local
            paths.
        normalized_root: Root directory used to resolve repository-local
            paths.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    refs.append({
        'source': src.relative_to(source_root).as_posix(),
        'destination': dst.relative_to(normalized_root).as_posix(),
        'kind': kind,
    })


def materialize_import(*, repo_root: Path, source_root: str = '', mvp_zip: str = '') -> dict[str, Any]:
    """Materialize import.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        source_root: Root directory used to resolve repository-local
            paths.
        mvp_zip: Primary mvp zip used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    root, temp, source = _prepare_source(source_root=source_root, mvp_zip=mvp_zip)
    try:
        inventory = _scan_root(root)
        import_id = f"{slugify(Path(source).stem)}-{sha256_text(source)[:8]}"
        normalized_root = imports_root(repo_root) / import_id / 'normalized'
        mirrored_docs_root = docs_imports_root(repo_root) / import_id
        normalized_root.mkdir(parents=True, exist_ok=True)
        mirrored_docs_root.mkdir(parents=True, exist_ok=True)

        refs: list[dict[str, Any]] = []
        preserved_counts: Counter[str] = Counter()
        preserved_examples: dict[str, list[str]] = defaultdict(list)
        mirrored_doc_count = 0
        doc_like_count = 0

        source_tree_root = normalized_root / 'source_tree'
        for path in sorted(root.rglob('*')):
            if path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            preserved_class = _classify_preserved_file(rel, path)
            if preserved_class is None:
                continue
            target = source_tree_root / rel
            _copy_preserved_file(path, target, refs, kind=preserved_class, source_root=root, normalized_root=normalized_root)
            preserved_counts[preserved_class] += 1
            if len(preserved_examples[preserved_class]) < 25:
                preserved_examples[preserved_class].append(rel)
            if _is_doc_like(rel, path):
                mirror_targets = []
                if rel.startswith('docs/'):
                    mirror_targets.append(mirrored_docs_root / rel[len('docs/'):])
                    mirror_targets.append(mirrored_docs_root / rel)
                else:
                    mirror_targets.append(mirrored_docs_root / rel)
                for mirror_target in mirror_targets:
                    mirror_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, mirror_target)
                mirrored_doc_count += len(mirror_targets)
                doc_like_count += 1

        reference_manifest = {
            'import_id': import_id,
            'source': source,
            'source_mode': 'directory' if source_root else 'zip',
            'mirrored_docs_root': str(mirrored_docs_root.relative_to(repo_root)),
            'normalized_root': str(normalized_root.relative_to(repo_root)),
            'normalized_source_tree': str(source_tree_root.relative_to(repo_root)),
            'mirrored_file_count': mirrored_doc_count,
            'copied_doc_like_count': doc_like_count,
            'preserved_file_count': sum(preserved_counts.values()),
            'preserved_class_counts': dict(sorted(preserved_counts.items())),
            'preserved_examples': {key: value for key, value in sorted(preserved_examples.items())},
            'references_recorded': len(refs),
            'created_at': utc_now(),
            'notes': [
                'Imported MVP material is normalized under mvpify/imports/<id>/normalized/source_tree with original relative paths preserved.',
                'Doc-like material is mirrored into docs/MVPs/imports/<id> for governed downstream reading and restartable handoff.',
                'Only materially relevant classes of content are preserved; arbitrary unrelated files are intentionally skipped.',
            ],
        }

        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(normalized_root / 'import_inventory.json', inventory)
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(normalized_root / 'reference_manifest.json', reference_manifest)
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(normalized_root / 'preservation_index.json', {'import_id': import_id, 'references': refs, 'preserved_class_counts': reference_manifest['preserved_class_counts']})
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(mirrored_docs_root / 'mvpify_reference_manifest.json', reference_manifest)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        write_text(
            mirrored_docs_root / 'README.md',
            '\n'.join([
                '# Imported MVP documentation',
                '',
                f"- import_id: `{import_id}`",
                f"- source: `{source}`",
                f"- normalized_root: `{reference_manifest['normalized_root']}`",
                f"- normalized_source_tree: `{reference_manifest['normalized_source_tree']}`",
                f"- preserved_file_count: `{reference_manifest['preserved_file_count']}`",
                f"- mirrored_file_count: `{reference_manifest['mirrored_file_count']}`",
                '',
                'This directory mirrors the doc-like material read from the imported bundle.',
                'The normalized source tree preserves original relative paths for graph-native downstream consumption.',
                '',
            ]),
        )
        return {
            'ok': True,
            'import_id': import_id,
            'source': source,
            'source_mode': 'directory' if source_root else 'zip',
            'artifact_count': inventory['artifact_count'],
            'inventory': inventory,
            'normalized_root': str(normalized_root.relative_to(repo_root)),
            'normalized_source_tree': str(source_tree_root.relative_to(repo_root)),
            'mirrored_docs_root': str(mirrored_docs_root.relative_to(repo_root)),
            'mirrored_file_count': mirrored_doc_count,
            'copied_doc_like_count': doc_like_count,
            'preserved_file_count': reference_manifest['preserved_file_count'],
            'preserved_class_counts': reference_manifest['preserved_class_counts'],
            'preserved_examples': reference_manifest['preserved_examples'],
            'references_recorded': len(refs),
        }
    finally:
        if temp is not None:
            temp.cleanup()
