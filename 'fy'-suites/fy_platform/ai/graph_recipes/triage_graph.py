"""Triage graph for fy_platform.ai.graph_recipes.

"""
from __future__ import annotations

from fy_platform.ai.graph_recipes.recipe_base import RecipeResult, RecipeStep


def run_triage_recipe(adapter, query: str | None = None) -> RecipeResult:
    """Run triage recipe.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.

    Returns:
        RecipeResult:
            Value produced by this callable as
            ``RecipeResult``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # run_triage_recipe.
    steps = [RecipeStep('route_model'), RecipeStep('triage_query', {'query': query or ''})]
    payload = adapter.triage(query)
    return RecipeResult(recipe='triage', ok=bool(payload.get('ok')), steps=steps, output=payload)
