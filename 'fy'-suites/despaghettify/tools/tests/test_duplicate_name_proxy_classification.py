"""Tests for DS-015 duplicate-name proxy classification."""

from __future__ import annotations

from pathlib import Path

from despaghettify.tools.duplicate_name_proxy_classification import (
    INTENTIONAL_PUBLIC_PROTOCOL,
    LOCAL_WRAPPER_CANDIDATE,
    PACKAGE_HELPER_CANDIDATE,
    REVIEW_REQUIRED,
    classify_duplicate_name,
    collect_duplicate_name_proxy_summary,
    helper_candidate_names,
    intentional_public_protocol_names,
)


def test_public_protocol_names_are_not_helper_candidates() -> None:
    """Public method/protocol names are intentional C6 proxy noise."""
    assert intentional_public_protocol_names() == {
        "to_dict",
        "to_runtime_dict",
        "generate",
    }
    assert intentional_public_protocol_names().isdisjoint(helper_candidate_names())

    for name in intentional_public_protocol_names():
        assert classify_duplicate_name(name).status == INTENTIONAL_PUBLIC_PROTOCOL


def test_known_helper_candidates_are_actionable_by_kind() -> None:
    """Repeated private helper names stay actionable after public names are excluded."""
    for name in {"_as_list", "_bounded_int", "_clean_str_list", "_text"}:
        assert classify_duplicate_name(name).status == PACKAGE_HELPER_CANDIDATE
    assert classify_duplicate_name("_do").status == LOCAL_WRAPPER_CANDIDATE
    assert classify_duplicate_name("_unknown_helper").status == REVIEW_REQUIRED


def test_duplicate_summary_groups_counts_by_classification(tmp_path: Path) -> None:
    """The scan guard buckets duplicate names before a human changes code."""
    first = tmp_path / "first.py"
    first.write_text(
        "def to_dict():\n    return {}\n"
        "def _text(value):\n    return str(value)\n"
        "def route():\n    def _do():\n        return 1\n    return _do()\n",
        encoding="utf-8",
    )
    second = tmp_path / "second.py"
    second.write_text(
        "def to_dict():\n    return {}\n"
        "def _text(value):\n    return str(value)\n"
        "def route():\n    def _do():\n        return 2\n    return _do()\n",
        encoding="utf-8",
    )

    summary = collect_duplicate_name_proxy_summary([first, second])
    by_status = summary["by_status"]

    assert by_status[INTENTIONAL_PUBLIC_PROTOCOL]["to_dict"]["count"] == 2
    assert by_status[PACKAGE_HELPER_CANDIDATE]["_text"]["count"] == 2
    assert by_status[LOCAL_WRAPPER_CANDIDATE]["_do"]["count"] == 2
