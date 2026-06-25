"""Inspect graph for fy_platform.ai.graph_recipes.

"""
from __future__ import annotations

from fy_platform.ai.graph_recipes.recipe_base import RecipeResult, RecipeStep


def run_inspect_recipe(adapter, query: str | None = None) -> RecipeResult:
    """Run inspect recipe.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.

    Returns:
        RecipeResult:
            Value produced by this callable as
            ``RecipeResult``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # run_inspect_recipe.
    steps = [RecipeStep('load_latest_run')]
    payload = adapter.inspect(query)
    # Branch on query so run_inspect_recipe only continues along the matching state
    # path.
    if query:
        steps.append(RecipeStep('query_index', {'query': query, 'hit_count': payload.get('hit_count', 0)}))
    return RecipeResult(recipe='inspect', ok=bool(payload.get('ok')), steps=steps, output=payload)
