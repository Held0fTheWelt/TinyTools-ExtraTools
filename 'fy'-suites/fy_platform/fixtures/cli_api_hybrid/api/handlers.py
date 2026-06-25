"""API fixture handlers."""


def run_handler() -> dict[str, str]:
    """Return fixture response payload.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    return {"status": "accepted"}
