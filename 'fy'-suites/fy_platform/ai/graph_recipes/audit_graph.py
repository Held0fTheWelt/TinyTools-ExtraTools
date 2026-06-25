"""Audit graph for fy_platform.ai.graph_recipes.

"""
from __future__ import annotations

from fy_platform.ai.graph_recipes.recipe_base import RecipeResult, RecipeStep


def run_audit_recipe(adapter, target_repo_root: str) -> RecipeResult:
    """Run audit recipe.

    Args:
        adapter: Primary adapter used by this step.
        target_repo_root: Root directory used to resolve
            repository-local paths.

    Returns:
        RecipeResult:
            Value produced by this callable as
            ``RecipeResult``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # run_audit_recipe.
    steps = [RecipeStep('bind_target', {'target_repo_root': target_repo_root}), RecipeStep('execute_audit')]
    payload = adapter.audit(target_repo_root)
    steps.append(RecipeStep('collect_artifacts', {'ok': payload.get('ok', False)}))
    return RecipeResult(recipe='audit', ok=bool(payload.get('ok')), steps=steps, output=payload)
