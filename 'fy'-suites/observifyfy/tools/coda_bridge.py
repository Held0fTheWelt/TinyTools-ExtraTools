"""Read bounded Coda status for observifyfy."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.strategy_profiles import strategy_runtime_metadata


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_coda_signal(repo_root: Path) -> dict[str, Any]:
    """Load the latest Coda outputs that observifyfy can surface."""
    active_profile = strategy_runtime_metadata(repo_root)
    reports_root = repo_root / "coda" / "reports"
    closure_path = reports_root / "latest_closure_pack.json"
    warning_path = reports_root / "latest_warning_ledger.json"
    residue_path = reports_root / "latest_residue_ledger.json"
    review_path = reports_root / "latest_review_packet.json"
    if not closure_path.is_file():
        return {
            "present": False,
            "active_strategy_profile": active_profile,
            "closure_pack": None,
            "warning_ledger": None,
            "residue_ledger": None,
            "review_packet": None,
            "closure_movement": None,
        }
    closure_pack = _load_json(closure_path)
    warning_ledger = _load_json(warning_path) if warning_path.is_file() else None
    residue_ledger = _load_json(residue_path) if residue_path.is_file() else None
    review_packet = _load_json(review_path) if review_path.is_file() else None
    closure_movement = {
        "status": closure_pack.get("status", "unknown"),
        "obligation_count": len(closure_pack.get("obligations") or []),
        "required_test_count": len(closure_pack.get("required_tests") or []),
        "required_doc_count": len(closure_pack.get("required_docs") or []),
        "accepted_review_item_count": len(closure_pack.get("review_acceptances") or []),
        "affected_surface_count": len(closure_pack.get("affected_surfaces") or []),
        "grouped_obligation_count": len(closure_pack.get("grouped_obligations") or []),
        "wave_packet_count": len(closure_pack.get("wave_packets") or []),
        "auto_preparation_count": len(closure_pack.get("auto_preparation_packets") or []),
        "packet_depth": closure_pack.get("packet_depth", "standard"),
        "warning_count": len((warning_ledger or {}).get("items") or []),
        "residue_count": len((residue_ledger or {}).get("items") or []),
    }
    return {
        "present": True,
        "active_strategy_profile": active_profile,
        "closure_pack": closure_pack,
        "warning_ledger": warning_ledger,
        "residue_ledger": residue_ledger,
        "review_packet": review_packet,
        "closure_movement": closure_movement,
    }


__all__ = ["load_coda_signal"]
