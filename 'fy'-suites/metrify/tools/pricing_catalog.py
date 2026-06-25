"""Pricing catalog for metrify.tools.

"""
from __future__ import annotations

from typing import Any

DEFAULT_CATALOG: dict[str, dict[str, dict[str, float]]] = {
    'gpt-5.4': {
        'standard': {'input': 2.50, 'cached_input': 0.25, 'output': 15.00},
        'batch': {'input': 1.25, 'cached_input': 0.13, 'output': 7.50},
        'flex': {'input': 1.25, 'cached_input': 0.13, 'output': 7.50},
        'priority': {'input': 5.00, 'cached_input': 0.50, 'output': 30.00},
    },
    'gpt-5.4-mini': {
        'standard': {'input': 0.75, 'cached_input': 0.075, 'output': 4.50},
        'batch': {'input': 0.375, 'cached_input': 0.0375, 'output': 2.25},
        'flex': {'input': 0.375, 'cached_input': 0.0375, 'output': 2.25},
        'priority': {'input': 1.50, 'cached_input': 0.15, 'output': 9.00},
    },
    'gpt-5.4-nano': {
        'standard': {'input': 0.20, 'cached_input': 0.02, 'output': 1.25},
        'batch': {'input': 0.10, 'cached_input': 0.01, 'output': 0.625},
        'flex': {'input': 0.10, 'cached_input': 0.01, 'output': 0.625},
    },
    'gpt-5.4-pro': {
        'standard': {'input': 30.00, 'cached_input': 0.0, 'output': 180.00},
        'batch': {'input': 15.00, 'cached_input': 0.0, 'output': 90.00},
        'flex': {'input': 15.00, 'cached_input': 0.0, 'output': 90.00},
        'priority': {'input': 60.00, 'cached_input': 0.0, 'output': 270.00},
    },
}


def get_price(model: str, service_tier: str) -> dict[str, float]:
    """Get price.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        model: Primary model used by this step.
        service_tier: Primary service tier used by this step.

    Returns:
        dict[str, float]:
            Structured payload describing the outcome of the
            operation.
    """
    model_prices = DEFAULT_CATALOG.get(model)
    # Branch on not model_prices so get_price only continues along the matching state
    # path.
    if not model_prices:
        return {'input': 0.0, 'cached_input': 0.0, 'output': 0.0}
    return model_prices.get(service_tier, model_prices.get('standard', {'input': 0.0, 'cached_input': 0.0, 'output': 0.0}))


def catalog_payload() -> dict[str, Any]:
    """Catalog payload.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {'models': DEFAULT_CATALOG}
