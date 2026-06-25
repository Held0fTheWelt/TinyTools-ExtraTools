"""Recipe base for fy_platform.ai.graph_recipes.

"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecipeStep:
    """Coordinate recipe step behavior.
    """
    name: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecipeResult:
    """Structured data container for recipe result.
    """
    recipe: str
    ok: bool
    steps: list[RecipeStep]
    output: dict[str, Any]
