"""Classify duplicate-name proxy findings for despaghettify scans."""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INTENTIONAL_PUBLIC_PROTOCOL = "intentional_public_protocol"
PACKAGE_HELPER_CANDIDATE = "package_helper_candidate"
LOCAL_WRAPPER_CANDIDATE = "local_wrapper_candidate"
REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class DuplicateNameClassification:
    """Decision record for a duplicate function-name proxy finding."""

    name: str
    status: str
    reason: str


_INTENTIONAL_PUBLIC_PROTOCOLS: dict[str, str] = {
    "to_dict": "Public payload serialization method used across dataclasses and DTOs.",
    "to_runtime_dict": "Public runtime payload serialization method used across contracts.",
    "generate": "Adapter/protocol entrypoint used by test doubles and runtime adapters.",
}

_PACKAGE_HELPER_CANDIDATES: dict[str, str] = {
    "_as_list": "Repeated local collection coercion helper.",
    "_bounded_int": "Repeated bounded integer normalization helper.",
    "_clean_str_list": "Repeated string-list normalization helper.",
    "_text": "Repeated scalar-to-clean-text helper.",
}

_LOCAL_WRAPPER_CANDIDATES: dict[str, str] = {
    "_do": "Repeated local route wrapper; centralize only when closure behavior matches.",
}


def classify_duplicate_name(name: str) -> DuplicateNameClassification:
    """Return the duplicate-name proxy classification for ``name``."""
    if name in _INTENTIONAL_PUBLIC_PROTOCOLS:
        return DuplicateNameClassification(
            name=name,
            status=INTENTIONAL_PUBLIC_PROTOCOL,
            reason=_INTENTIONAL_PUBLIC_PROTOCOLS[name],
        )
    if name in _PACKAGE_HELPER_CANDIDATES:
        return DuplicateNameClassification(
            name=name,
            status=PACKAGE_HELPER_CANDIDATE,
            reason=_PACKAGE_HELPER_CANDIDATES[name],
        )
    if name in _LOCAL_WRAPPER_CANDIDATES:
        return DuplicateNameClassification(
            name=name,
            status=LOCAL_WRAPPER_CANDIDATE,
            reason=_LOCAL_WRAPPER_CANDIDATES[name],
        )
    return DuplicateNameClassification(
        name=name,
        status=REVIEW_REQUIRED,
        reason="No DS-015 classification exists; inspect before renaming.",
    )


def intentional_public_protocol_names() -> frozenset[str]:
    """Names that must not be renamed only to satisfy the C6 proxy."""
    return frozenset(_INTENTIONAL_PUBLIC_PROTOCOLS)


def helper_candidate_names() -> frozenset[str]:
    """Names that are eligible for package-local helper centralization."""
    return frozenset(_PACKAGE_HELPER_CANDIDATES) | frozenset(_LOCAL_WRAPPER_CANDIDATES)


def iter_function_names(path: Path) -> Iterable[str]:
    """Yield function names from a Python file, ignoring syntax failures."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return ()
    return (
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def collect_duplicate_name_proxy_summary(paths: Iterable[Path]) -> dict[str, object]:
    """Collect duplicate function-name counts grouped by DS-015 classification."""
    counts: Counter[str] = Counter()
    files_by_name: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        for name in iter_function_names(path):
            counts[name] += 1
            files_by_name[name].add(path.as_posix())

    duplicate_names = {name: count for name, count in counts.items() if count > 1}
    by_status: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for name, count in sorted(duplicate_names.items()):
        classification = classify_duplicate_name(name)
        by_status[classification.status][name] = {
            "count": count,
            "files": sorted(files_by_name[name]),
            "reason": classification.reason,
        }

    return {
        "duplicate_name_count": len(duplicate_names),
        "duplicate_function_instances": sum(duplicate_names.values()),
        "by_status": {status: dict(names) for status, names in sorted(by_status.items())},
    }


__all__ = [
    "INTENTIONAL_PUBLIC_PROTOCOL",
    "LOCAL_WRAPPER_CANDIDATE",
    "PACKAGE_HELPER_CANDIDATE",
    "REVIEW_REQUIRED",
    "DuplicateNameClassification",
    "classify_duplicate_name",
    "collect_duplicate_name_proxy_summary",
    "helper_candidate_names",
    "intentional_public_protocol_names",
    "iter_function_names",
]
