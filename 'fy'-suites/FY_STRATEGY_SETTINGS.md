# FY Strategy Settings

This file is the machine-parsable and developer-readable active strategy control surface for fy-suites.

## Active strategy

- active_profile: D
- profile_label: balanced_dual_suite_target
- default_progression_order: A,B,C,D,E
- progression_mode: progressive
- allow_profile_switching: true

## Switching surfaces

- menu_enabled: true
- trigger_enabled: true
- command_enabled: true
- markdown_override_allowed: true

## Safety and review

- require_review_by_default: true
- auto_apply_level: none
- abstain_when_evidence_is_weak: true
- release_honesty_strict: true

## Diagnosta settings

- diagnosta_enabled: true
- diagnosta_scope: claim_and_mvp
- diagnosta_emit_blocker_graph: true
- diagnosta_emit_cannot_honestly_claim: true

## Coda settings

- coda_enabled: true
- coda_scope: closure_pack_only
- coda_review_packets_required: true
- coda_require_obligations: true
- coda_require_residue_reporting: true

## Observability and state

- emit_profile_to_run_journal: true
- emit_profile_to_observifyfy: true
- emit_profile_to_compare_runs: true
- emit_profile_to_status_pages: true

## Optional advanced behavior

- compare_profile_effects: optional
- allow_candidate_e_features: false
- candidate_e_requires_explicit_opt_in: true

## Candidate profile notes

### A
Artifact-first precursor. Best when the shared artifact foundation is still missing.

### B
Diagnosta-first. Best when readiness truth and blocker visibility are weak.

### C
Coda-first. Best only when closure-pack assembly is the dominant missing layer.

### D
Balanced dual-suite target. Recommended default for this MVP wave.

### E
Aggressive expansion target. Use only after D-level proof is materially present.
