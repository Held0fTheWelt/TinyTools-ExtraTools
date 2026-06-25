"""Library fixture module."""


def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: Primary a used by this step.
        b: Primary b used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    return a + b
