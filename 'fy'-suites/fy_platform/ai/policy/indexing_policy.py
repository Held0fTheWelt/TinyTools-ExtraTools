"""Indexing policy for fy_platform.ai.policy.

"""
from __future__ import annotations

DEFAULT_EXCLUDED_DIRS = {
    '.git', '.hg', '.svn', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '.venv', 'venv', 'node_modules', '.fydata', 'dist', 'build', '.idea', '.vscode'
}
DEFAULT_EXCLUDED_FILES = {'.env', '.env.local', '.env.production', '.env.development'}
TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.rst', '.mmd', '.csv'
}
MAX_TEXT_BYTES = 1_000_000


def should_exclude_dir(name: str) -> bool:
    """Return whether exclude dir.

    Args:
        name: Primary name used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return name in DEFAULT_EXCLUDED_DIRS


def should_exclude_file(name: str) -> bool:
    """Return whether exclude file.

    Args:
        name: Primary name used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    return name in DEFAULT_EXCLUDED_FILES


def is_indexable_path(path) -> bool:
    """Return whether indexable path.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    suffix = getattr(path, 'suffix', '').lower()
    return suffix in TEXT_EXTENSIONS
