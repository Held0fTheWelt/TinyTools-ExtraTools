"""Context pack graph for fy_platform.ai.graph_recipes.

"""
from __future__ import annotations

from fy_platform.ai.graph_recipes.recipe_base import RecipeResult, RecipeStep


def run_context_pack_recipe(adapter, query: str, audience: str = 'developer') -> RecipeResult:
    """Run context pack recipe.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.
        audience: Free-text input that shapes this operation.

    Returns:
        RecipeResult:
            Value produced by this callable as
            ``RecipeResult``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # run_context_pack_recipe.
    steps = [RecipeStep('refresh_index'), RecipeStep('build_context_pack', {'query': query, 'audience': audience})]
    payload = adapter.prepare_context_pack(query, audience)
    steps.append(RecipeStep('persist_context_pack', {'hit_count': payload.get('hit_count', 0)}))
    return RecipeResult(recipe='context-pack', ok=True, steps=steps, output=payload)
