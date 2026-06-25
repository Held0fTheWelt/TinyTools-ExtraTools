"""Final product capability for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import utc_now


def ai_capability_payload(root: Path | None = None) -> dict[str, Any]:
    """Ai capability payload.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {
        "schema_version": "fy.ai-capability.v1",
        "generated_at": utc_now(),
        "shared": {
            "langgraph_ready": ["inspect_graph", "audit_graph", "context_pack_graph", "triage_graph"],
            "langchain_ready": ["structured-output-compatible envelopes", "tool-like suite commands", "retrieval/context-pack surfaces"],
            "rag_ready": ["semantic_index", "context_packs", "cross_suite_intelligence"],
            "slm_llm_routing": ["model_router", "decision_policy"],
        },
        "per_suite": {
            "contractify": ["decision_policy", "import/legacy-import", "consolidate", "ADR reflection"],
            "testify": ["ADR reflection checks", "cross-suite status use"],
            "documentify": ["template-aware generation", "AI-readable tracks"],
            "docify": ["inline-explain guidance", "public API doc checks"],
            "despaghettify": ["local spike surfacing"],
            "templatify": ["template inventory/validation/drift"],
            "usabilify": ["human-readable next steps"],
            "securify": ["security lane + secret-risk review"],
            "observifyfy": ["internal suite-memory and non-contaminating tracking"],
            "mvpify": ["prepared MVP import", "doc mirroring", "cross-suite orchestration"],
            "metrify": ["usage ledger", "cost reporting", "observify bridge", "AI spend summaries"],
            "diagnosta": ["bounded readiness cases", "blocker graphs", "claim-honesty outputs", "strategy-profile-aware diagnosis"],
            "coda": ["bounded closure packs", "cross-suite obligations/tests/docs", "explicit residue ledgers", "review-first closure assembly"],
        },
        "aspirational": [
            "Swap graph recipe stubs for real LangGraph checkpointers and human-interrupt resume once external runtime dependencies are allowed.",
            "Bind model-router task classes to concrete LangChain model backends and provider-native structured output in production deployments.",
            "Promote semantic index scoring to stronger embedding/vector backends when cost/runtime policy permits.",
        ],
        "sources_of_truth": ["registry", "journal", "status pages", "suite reports", "docs/platform"],
    }


def render_ai_capability_markdown(payload: dict[str, Any]) -> str:
    """Render ai capability markdown.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        "# AI Capability Matrix",
        "",
        "This report shows which AI/graph/retrieval mechanisms are already wired into the current fy workspace and which ones are still aspirational.",
        "",
    ]
    lines.extend(["## Shared mechanisms", ""])
    # Process (key, value) one item at a time so render_ai_capability_markdown applies
    # the same rule across the full collection.
    for key, value in payload.get("shared", {}).items():
        lines.append(f"- {key}: {', '.join(value)}")
    lines.extend(["", "## Per-suite mechanisms", ""])
    # Process (suite, items) one item at a time so render_ai_capability_markdown applies
    # the same rule across the full collection.
    for suite, items in payload.get("per_suite", {}).items():
        lines.append(f"### {suite}")
        lines.append("")
        # Process item one item at a time so render_ai_capability_markdown applies the
        # same rule across the full collection.
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    lines.extend(["## Aspirational next upgrades", ""])
    # Process item one item at a time so render_ai_capability_markdown applies the same
    # rule across the full collection.
    for item in payload.get("aspirational", []):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"
