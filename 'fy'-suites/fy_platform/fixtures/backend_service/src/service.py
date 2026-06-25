"""Backend fixture service module."""


def health() -> str:
    """Return health marker.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return "ok"
