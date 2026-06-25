"""Strategy-profile commands for the public fy CLI."""
from __future__ import annotations

import argparse
import json

from fy_platform.ai.strategy_profiles import load_active_strategy_profile, set_active_strategy_profile, strategy_runtime_metadata
from fy_platform.tools.cli_workspace_commands import resolve_repo


def cmd_strategy_show(args: argparse.Namespace) -> int:
    """Print the active strategy profile payload."""
    repo = resolve_repo(args.project_root)
    profile = load_active_strategy_profile(repo)
    payload = {
        'ok': True,
        'schema_version': profile.schema_version,
        'active_profile': profile.active_profile,
        'profile_label': profile.profile_label,
        'default_progression_order': profile.default_progression_order,
        'progression_mode': profile.progression_mode,
        'source_path': profile.source_path,
        'runtime_metadata': strategy_runtime_metadata(repo),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_strategy_set(args: argparse.Namespace) -> int:
    """Persist a new active strategy profile."""
    repo = resolve_repo(args.project_root)
    profile = set_active_strategy_profile(repo, args.profile)
    payload = {
        'ok': True,
        'schema_version': profile.schema_version,
        'active_profile': profile.active_profile,
        'profile_label': profile.profile_label,
        'default_progression_order': profile.default_progression_order,
        'progression_mode': profile.progression_mode,
        'source_path': profile.source_path,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0
