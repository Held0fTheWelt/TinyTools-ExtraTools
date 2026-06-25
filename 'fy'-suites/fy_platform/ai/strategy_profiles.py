"""Markdown-backed strategy profile loading and persistence for fy_platform.ai."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.profile_behavior import behavior_for_profile
from fy_platform.ai.schemas.readiness_closure import ActiveStrategyProfile
from fy_platform.ai.workspace import workspace_root, write_text

SUPPORTED_STRATEGY_PROFILES = ('A', 'B', 'C', 'D', 'E')
DEFAULT_STRATEGY_PROFILE = 'D'
DEFAULT_PROGRESSION_ORDER = list(SUPPORTED_STRATEGY_PROFILES)
PROFILE_LABELS = {
    'A': 'artifact_first_precursor',
    'B': 'diagnosta_first',
    'C': 'coda_first',
    'D': 'balanced_dual_suite_target',
    'E': 'aggressive_expansion_target',
}
PROFILE_SUMMARIES = {
    'A': 'Artifact-first precursor. Best when the shared artifact foundation is still missing.',
    'B': 'Diagnosta-first. Best when readiness truth and blocker visibility are weak.',
    'C': 'Coda-first. Best only when closure-pack assembly is the dominant missing layer.',
    'D': 'Balanced dual-suite target. Recommended default for this MVP wave.',
    'E': 'Aggressive expansion target. Use only after D-level proof is materially present.',
}
STRATEGY_FILE_RELS = (
    Path('FY_STRATEGY_SETTINGS.md'),
    Path('fy_platform/state/strategy_profiles/FY_ACTIVE_STRATEGY.md'),
)


def validate_profile(profile: str) -> str:
    """Validate and normalize a strategy profile identifier."""
    normalized = str(profile).strip().upper()
    if normalized not in SUPPORTED_STRATEGY_PROFILES:
        raise ValueError(f'invalid strategy profile: {profile}')
    return normalized


def _canonical_strategy_text(values: dict[str, Any]) -> str:
    order = values.get('default_progression_order') or DEFAULT_PROGRESSION_ORDER
    if isinstance(order, str):
        order = [item.strip() for item in order.split(',') if item.strip()]
    lines = [
        '# FY Strategy Settings',
        '',
        'This file is the machine-parsable and developer-readable active strategy control surface for fy-suites.',
        '',
        '## Active strategy',
        '',
        f"- active_profile: {values['active_profile']}",
        f"- profile_label: {values['profile_label']}",
        f"- default_progression_order: {','.join(order)}",
        f"- progression_mode: {values['progression_mode']}",
        f"- allow_profile_switching: {_bool_text(values['allow_profile_switching'])}",
        '',
        '## Switching surfaces',
        '',
        f"- menu_enabled: {_bool_text(values['menu_enabled'])}",
        f"- trigger_enabled: {_bool_text(values['trigger_enabled'])}",
        f"- command_enabled: {_bool_text(values['command_enabled'])}",
        f"- markdown_override_allowed: {_bool_text(values['markdown_override_allowed'])}",
        '',
        '## Safety and review',
        '',
        f"- require_review_by_default: {_bool_text(values['require_review_by_default'])}",
        f"- auto_apply_level: {values['auto_apply_level']}",
        f"- abstain_when_evidence_is_weak: {_bool_text(values['abstain_when_evidence_is_weak'])}",
        f"- release_honesty_strict: {_bool_text(values['release_honesty_strict'])}",
        '',
        '## Diagnosta settings',
        '',
        f"- diagnosta_enabled: {_bool_text(values['diagnosta_enabled'])}",
        f"- diagnosta_scope: {values['diagnosta_scope']}",
        f"- diagnosta_emit_blocker_graph: {_bool_text(values['diagnosta_emit_blocker_graph'])}",
        f"- diagnosta_emit_cannot_honestly_claim: {_bool_text(values['diagnosta_emit_cannot_honestly_claim'])}",
        '',
        '## Coda settings',
        '',
        f"- coda_enabled: {_bool_text(values['coda_enabled'])}",
        f"- coda_scope: {values['coda_scope']}",
        f"- coda_review_packets_required: {_bool_text(values['coda_review_packets_required'])}",
        f"- coda_require_obligations: {_bool_text(values['coda_require_obligations'])}",
        f"- coda_require_residue_reporting: {_bool_text(values['coda_require_residue_reporting'])}",
        '',
        '## Observability and state',
        '',
        f"- emit_profile_to_run_journal: {_bool_text(values['emit_profile_to_run_journal'])}",
        f"- emit_profile_to_observifyfy: {_bool_text(values['emit_profile_to_observifyfy'])}",
        f"- emit_profile_to_compare_runs: {_bool_text(values['emit_profile_to_compare_runs'])}",
        f"- emit_profile_to_status_pages: {_bool_text(values['emit_profile_to_status_pages'])}",
        '',
        '## Optional advanced behavior',
        '',
        f"- compare_profile_effects: {values['compare_profile_effects']}",
        f"- allow_candidate_e_features: {_bool_text(values['allow_candidate_e_features'])}",
        f"- candidate_e_requires_explicit_opt_in: {_bool_text(values['candidate_e_requires_explicit_opt_in'])}",
        '',
        '## Candidate profile notes',
        '',
    ]
    for profile in SUPPORTED_STRATEGY_PROFILES:
        lines.extend([f'### {profile}', PROFILE_SUMMARIES[profile], ''])
    return '\n'.join(lines).rstrip() + '\n'

def _bool_text(value: Any) -> str:
    return 'true' if bool(value) else 'false'


def default_strategy_values() -> dict[str, Any]:
    active = DEFAULT_STRATEGY_PROFILE
    return {
        'active_profile': active,
        'profile_label': PROFILE_LABELS[active],
        'default_progression_order': list(DEFAULT_PROGRESSION_ORDER),
        'progression_mode': 'progressive',
        'allow_profile_switching': True,
        'menu_enabled': True,
        'trigger_enabled': True,
        'command_enabled': True,
        'markdown_override_allowed': True,
        'require_review_by_default': True,
        'auto_apply_level': 'none',
        'abstain_when_evidence_is_weak': True,
        'release_honesty_strict': True,
        'diagnosta_enabled': True,
        'diagnosta_scope': 'claim_and_mvp',
        'diagnosta_emit_blocker_graph': True,
        'diagnosta_emit_cannot_honestly_claim': True,
        'coda_enabled': True,
        'coda_scope': 'closure_pack_only',
        'coda_review_packets_required': True,
        'coda_require_obligations': True,
        'coda_require_residue_reporting': True,
        'emit_profile_to_run_journal': True,
        'emit_profile_to_observifyfy': True,
        'emit_profile_to_compare_runs': True,
        'emit_profile_to_status_pages': True,
        'compare_profile_effects': 'optional',
        'allow_candidate_e_features': False,
        'candidate_e_requires_explicit_opt_in': True,
    }


def strategy_file_path(root: Path | None = None) -> Path:
    """Return the canonical strategy settings file path, creating it if needed."""
    workspace = workspace_root(root)
    for rel in STRATEGY_FILE_RELS:
        candidate = workspace / rel
        if candidate.is_file():
            return candidate
    canonical = workspace / STRATEGY_FILE_RELS[0]
    canonical.parent.mkdir(parents=True, exist_ok=True)
    write_text(canonical, _canonical_strategy_text(default_strategy_values()))
    fallback = workspace / STRATEGY_FILE_RELS[1]
    fallback.parent.mkdir(parents=True, exist_ok=True)
    if not fallback.exists():
        write_text(fallback, _canonical_strategy_text(default_strategy_values()))
    return canonical


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    if ',' in value and not value.startswith('['):
        parts = [item.strip() for item in value.split(',') if item.strip()]
        if parts and all(item in SUPPORTED_STRATEGY_PROFILES for item in parts):
            return parts
    return value


def parse_strategy_markdown(text: str) -> dict[str, Any]:
    """Parse the stable Markdown bullet grammar used by strategy settings files."""
    values: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith('- ') or ':' not in stripped:
            continue
        key, raw = stripped[2:].split(':', 1)
        values[key.strip()] = _parse_scalar(raw)
    defaults = default_strategy_values()
    merged = {**defaults, **values}
    merged['active_profile'] = validate_profile(str(merged['active_profile']))
    merged['profile_label'] = PROFILE_LABELS[merged['active_profile']]
    order = merged.get('default_progression_order') or DEFAULT_PROGRESSION_ORDER
    if isinstance(order, str):
        order = [item.strip() for item in order.split(',') if item.strip()]
    merged['default_progression_order'] = [validate_profile(item) for item in order]
    return merged


def load_active_strategy_profile(root: Path | None = None) -> ActiveStrategyProfile:
    """Load the current active strategy profile from Markdown settings."""
    path = strategy_file_path(root)
    values = parse_strategy_markdown(path.read_text(encoding='utf-8'))
    return ActiveStrategyProfile(source_path=str(path.relative_to(workspace_root(root))), **values)


def strategy_runtime_metadata(root: Path | None = None) -> dict[str, Any]:
    """Return strategy metadata shaped for payloads, run records, and observability."""
    profile = load_active_strategy_profile(root)
    behavior = behavior_for_profile(
        profile.active_profile,
        allow_candidate_e_features=profile.allow_candidate_e_features,
        candidate_e_requires_explicit_opt_in=profile.candidate_e_requires_explicit_opt_in,
    )
    return {
        'schema_version': profile.schema_version,
        'active_profile': profile.active_profile,
        'profile_label': profile.profile_label,
        'default_profile': DEFAULT_STRATEGY_PROFILE,
        'supported_profiles': list(SUPPORTED_STRATEGY_PROFILES),
        'recommended_progression_order': list(profile.default_progression_order),
        'progression_graph': 'A->B->C->D->E',
        'progression_mode': profile.progression_mode,
        'allow_profile_switching': profile.allow_profile_switching,
        'require_review_by_default': profile.require_review_by_default,
        'emit_profile_to_run_journal': profile.emit_profile_to_run_journal,
        'emit_profile_to_compare_runs': profile.emit_profile_to_compare_runs,
        'emit_profile_to_observifyfy': profile.emit_profile_to_observifyfy,
        'emit_profile_to_status_pages': profile.emit_profile_to_status_pages,
        'allow_candidate_e_features': profile.allow_candidate_e_features,
        'source_path': profile.source_path,
        **behavior,
    }


def set_active_strategy_profile(root: Path | None, profile: str) -> ActiveStrategyProfile:
    """Persist a new active strategy profile to the canonical Markdown file."""
    workspace = workspace_root(root)
    normalized = validate_profile(profile)
    current = parse_strategy_markdown(strategy_file_path(workspace).read_text(encoding='utf-8'))
    current['active_profile'] = normalized
    current['profile_label'] = PROFILE_LABELS[normalized]
    current['allow_candidate_e_features'] = normalized == 'E'
    current['compare_profile_effects'] = 'required' if normalized == 'E' else 'optional'
    text = _canonical_strategy_text(current)
    primary = workspace / STRATEGY_FILE_RELS[0]
    primary.parent.mkdir(parents=True, exist_ok=True)
    write_text(primary, text)
    secondary = workspace / STRATEGY_FILE_RELS[1]
    secondary.parent.mkdir(parents=True, exist_ok=True)
    write_text(secondary, text)
    return load_active_strategy_profile(workspace)


__all__ = [
    'DEFAULT_PROGRESSION_ORDER',
    'DEFAULT_STRATEGY_PROFILE',
    'PROFILE_LABELS',
    'PROFILE_SUMMARIES',
    'STRATEGY_FILE_RELS',
    'SUPPORTED_STRATEGY_PROFILES',
    'load_active_strategy_profile',
    'parse_strategy_markdown',
    'set_active_strategy_profile',
    'strategy_file_path',
    'strategy_runtime_metadata',
    'validate_profile',
]
