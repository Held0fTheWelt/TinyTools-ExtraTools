"""Mode registry for fy_platform.runtime.

"""
from __future__ import annotations

from dataclasses import dataclass, field

from fy_platform.runtime.execution_plan import ExecutionPlan, LaneStep


@dataclass(frozen=True)
class ModeSpec:
    """Coordinate mode spec behavior.
    """
    public_command: str
    mode_name: str
    lens: str
    suite: str | None
    adapter_command: str | None
    default_lanes: list[str]
    provider_allowed: bool = False
    deterministic_first: bool = True
    review_required: bool = False
    notes: list[str] = field(default_factory=list)

    def to_execution_plan(self) -> ExecutionPlan:
        """To execution plan.

        Returns:
            ExecutionPlan:
                Value produced by this callable as
                ``ExecutionPlan``.
        """
        return ExecutionPlan(
            public_command=self.public_command,
            mode_name=self.mode_name,
            lens=self.lens,
            steps=[LaneStep(name) for name in self.default_lanes],
            provider_allowed=self.provider_allowed,
            deterministic_first=self.deterministic_first,
            review_required=self.review_required,
        )


MODE_SPECS: dict[str, ModeSpec] = {
    'analyze.contract': ModeSpec('analyze', 'contract', 'governance', 'contractify', 'audit', ['inspect', 'normalize', 'match', 'govern', 'generate'], review_required=True),
    'analyze.quality': ModeSpec('analyze', 'quality', 'quality', 'testify', 'audit', ['inspect', 'normalize', 'match', 'triage', 'generate']),
    'analyze.docs': ModeSpec('analyze', 'docs', 'knowledge', 'documentify', 'audit', ['inspect', 'normalize', 'match', 'generate']),
    'analyze.code_docs': ModeSpec('analyze', 'code_docs', 'knowledge', 'docify', 'audit', ['inspect', 'normalize', 'match', 'generate']),
    'analyze.security': ModeSpec('analyze', 'security', 'governance', 'securify', 'audit', ['inspect', 'normalize', 'match', 'govern', 'generate'], review_required=True),
    'analyze.docker': ModeSpec('analyze', 'docker', 'operations', 'dockerify', 'audit', ['inspect', 'normalize', 'match', 'govern', 'generate']),
    'analyze.observability': ModeSpec('analyze', 'observability', 'operations', 'observifyfy', 'audit', ['inspect', 'normalize', 'match', 'generate']),
    'analyze.templates': ModeSpec('analyze', 'templates', 'knowledge', 'templatify', 'audit', ['inspect', 'normalize', 'match', 'generate']),
    'analyze.usability': ModeSpec('analyze', 'usability', 'knowledge', 'usabilify', 'audit', ['inspect', 'normalize', 'match', 'generate']),
    'analyze.api': ModeSpec('analyze', 'api', 'knowledge', 'postmanify', 'audit', ['inspect', 'normalize', 'match', 'generate']),
    'analyze.structure': ModeSpec('analyze', 'structure', 'quality', 'despaghettify', 'audit', ['inspect', 'normalize', 'match', 'triage', 'generate']),
    'analyze.readiness': ModeSpec('analyze', 'readiness', 'governance', 'diagnosta', 'audit', ['inspect', 'normalize', 'match', 'triage', 'generate'], review_required=True),
    'analyze.closure': ModeSpec('analyze', 'closure', 'governance', 'coda', 'audit', ['inspect', 'normalize', 'match', 'triage', 'generate'], review_required=True),
    'inspect.contract': ModeSpec('inspect', 'contract', 'governance', 'contractify', 'inspect', ['inspect', 'index']),
    'inspect.quality': ModeSpec('inspect', 'quality', 'quality', 'testify', 'inspect', ['inspect', 'index']),
    'inspect.docs': ModeSpec('inspect', 'docs', 'knowledge', 'documentify', 'inspect', ['inspect', 'index']),
    'inspect.code_docs': ModeSpec('inspect', 'code_docs', 'knowledge', 'docify', 'inspect', ['inspect', 'index']),
    'inspect.security': ModeSpec('inspect', 'security', 'governance', 'securify', 'inspect', ['inspect', 'index']),
    'inspect.docker': ModeSpec('inspect', 'docker', 'operations', 'dockerify', 'inspect', ['inspect', 'index']),
    'inspect.observability': ModeSpec('inspect', 'observability', 'operations', 'observifyfy', 'inspect', ['inspect', 'index']),
    'inspect.templates': ModeSpec('inspect', 'templates', 'knowledge', 'templatify', 'inspect', ['inspect', 'index']),
    'inspect.usability': ModeSpec('inspect', 'usability', 'knowledge', 'usabilify', 'inspect', ['inspect', 'index']),
    'inspect.api': ModeSpec('inspect', 'api', 'knowledge', 'postmanify', 'inspect', ['inspect', 'index']),
    'inspect.structure': ModeSpec('inspect', 'structure', 'quality', 'despaghettify', 'inspect', ['inspect', 'index']),
    'inspect.readiness': ModeSpec('inspect', 'readiness', 'governance', 'diagnosta', 'inspect', ['inspect', 'index']),
    'inspect.closure': ModeSpec('inspect', 'closure', 'governance', 'coda', 'inspect', ['inspect', 'index']),
    'explain.contract': ModeSpec('explain', 'contract', 'governance', 'contractify', 'explain', ['inspect', 'match', 'explain'], provider_allowed=True),
    'explain.docs': ModeSpec('explain', 'docs', 'knowledge', 'documentify', 'explain', ['inspect', 'match', 'explain'], provider_allowed=True),
    'explain.code_docs': ModeSpec('explain', 'code_docs', 'knowledge', 'docify', 'explain', ['inspect', 'match', 'explain'], provider_allowed=True),
    'generate.context_pack': ModeSpec('generate', 'context_pack', 'platform', 'contractify', 'prepare-context-pack', ['inspect', 'index', 'match', 'generate']),
    'generate.docs': ModeSpec('generate', 'docs', 'knowledge', 'documentify', 'prepare-context-pack', ['inspect', 'index', 'match', 'generate']),
    'generate.surface_aliases': ModeSpec('generate', 'surface_aliases', 'platform', None, None, ['inspect', 'match', 'generate']),
    'generate.packaging_prep': ModeSpec('generate', 'packaging_prep', 'platform', None, None, ['inspect', 'govern', 'generate']),
    'generate.closure_pack': ModeSpec('generate', 'closure_pack', 'platform', 'coda', 'closure-pack', ['inspect', 'govern', 'generate'], review_required=True),
    'govern.release': ModeSpec('govern', 'release', 'platform', None, None, ['inspect', 'govern', 'verify', 'generate']),
    'govern.production': ModeSpec('govern', 'production', 'platform', None, None, ['inspect', 'govern', 'verify', 'generate']),
    'import.mvp': ModeSpec('import', 'mvp', 'platform', 'mvpify', 'import', ['inspect', 'normalize', 'generate']),
    'metrics.report': ModeSpec('metrics', 'report', 'platform', 'metrify', 'audit', ['inspect', 'govern', 'generate']),
    'metrics.governor_status': ModeSpec('metrics', 'governor_status', 'platform', None, None, ['inspect', 'govern', 'generate']),
}


def get_mode_spec(public_command: str, mode_name: str) -> ModeSpec:
    """Get mode spec.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        public_command: Primary public command used by this step.
        mode_name: Primary mode name used by this step.

    Returns:
        ModeSpec:
            Value produced by this callable as ``ModeSpec``.
    """
    key = f'{public_command}.{mode_name}'
    # Branch on key not in MODE_SPECS so get_mode_spec only continues along the matching
    # state path.
    if key not in MODE_SPECS:
        raise KeyError(f'unknown mode spec: {key}')
    return MODE_SPECS[key]
