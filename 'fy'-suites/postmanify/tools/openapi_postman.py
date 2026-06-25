"""
Build Postman Collection v2.1 JSON from an OpenAPI 3 document (paths +
tags).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})


@dataclass(frozen=True)
class OperationRef:
    """Reference to operation.
    """
    path: str
    method: str
    operation: Mapping[str, Any]


def load_openapi_dict(path: Path) -> dict[str, Any]:
    """Read Openapi Dict from configuration, disk, or remote sources.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Read and normalize the input data before load_openapi_dict branches on or
    # transforms it further.
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    # Branch on not isinstance(data, dict) so load_openapi_dict only continues along the
    # matching state path.
    if not isinstance(data, dict):
        msg = f"OpenAPI root must be a mapping: {path}"
        raise ValueError(msg)
    return data


def iter_operations(spec: Mapping[str, Any]) -> list[OperationRef]:
    """Implement ``iter_operations`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        spec: Primary spec used by this step.

    Returns:
        list[OperationRef]:
            Collection produced from the parsed or
            accumulated input data.
    """
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []
    out: list[OperationRef] = []
    for pth, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            m = method.lower()
            if m not in HTTP_METHODS or not isinstance(op, dict):
                continue
            out.append(OperationRef(path=pth, method=m.upper(), operation=op))
    return out


def _primary_tag(operation: Mapping[str, Any]) -> str:
    """Primary tag.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        operation: Primary operation used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    tags = operation.get("tags")
    if isinstance(tags, list) and tags:
        first = tags[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return "Untagged"


def backend_postman_url_raw(openapi_path: str, *, backend_api_prefix: str) -> str:
    """Map ``/api/v1/...`` OpenAPI paths to Postman raw URL using
    collection variables.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        openapi_path: Filesystem path to the file or directory being
            processed.
        backend_api_prefix: Primary backend api prefix used by this
            step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    prefix = backend_api_prefix.rstrip("/")
    if openapi_path.startswith(prefix + "/"):
        tail = openapi_path[len(prefix) + 1 :]
    elif openapi_path in (prefix, prefix + "/"):
        tail = ""
    else:
        return "{{backendBaseUrl}}" + (openapi_path if openapi_path.startswith("/") else "/" + openapi_path)
    return "{{backendBaseUrl}}{{backendApiPrefix}}/" + tail if tail else "{{backendBaseUrl}}{{backendApiPrefix}}"


def _request_item(name: str, method: str, url_raw: str, description: str) -> dict[str, Any]:
    """Request item.

    Args:
        name: Primary name used by this step.
        method: Primary method used by this step.
        url_raw: Primary url raw used by this step.
        description: Primary description used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {
        "name": name,
        "request": {
            "method": method,
            "header": [],
            "url": url_raw,
            "description": description,
        },
        "response": [],
    }


def group_operations_by_tag(ops: list[OperationRef]) -> dict[str, list[OperationRef]]:
    """Implement ``group_operations_by_tag`` for the surrounding module
    workflow.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        ops: Primary ops used by this step.

    Returns:
        dict[str, list[OperationRef]]:
            Structured payload describing the outcome of the
            operation.
    """
    buckets: dict[str, list[OperationRef]] = defaultdict(list)
    for op in ops:
        buckets[_primary_tag(op.operation)].append(op)
    return dict(sorted(buckets.items(), key=lambda kv: kv[0].lower()))


def _slug_tag(tag: str) -> str:
    """Slug tag.

    Args:
        tag: Primary tag used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", tag.strip()).strip("_")
    return s or "untagged"


def build_collections(
    spec: Mapping[str, Any],
    *,
    backend_api_prefix: str = "/api/v1",
    master_name: str = "World of Shadows — OpenAPI (generated)",
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Return (master_collection, tag_slug -> sub_collection).

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        spec: Primary spec used by this step.
        backend_api_prefix: Primary backend api prefix used by this
            step.
        master_name: Primary master name used by this step.

    Returns:
        tuple[dict[str, Any], dict[str, dict[str, Any]]]:
            Structured payload describing the outcome of the
            operation.
    """
    info = spec.get("info")
    title = master_name
    if isinstance(info, dict):
        t = info.get("title")
        if isinstance(t, str) and t.strip():
            title = f"{t.strip()} — generated from OpenAPI"

    ops = iter_operations(spec)
    grouped = group_operations_by_tag(ops)

    def folder_for_tag(tag: str, tag_ops: list[OperationRef]) -> dict[str, Any]:
        """Folder for tag.

        The implementation iterates over intermediate items before it
        returns. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            tag: Primary tag used by this step.
            tag_ops: Primary tag ops used by this step.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        items: list[dict[str, Any]] = []
        for op in sorted(tag_ops, key=lambda o: (o.path, o.method)):
            summary = op.operation.get("summary")
            if not isinstance(summary, str) or not summary.strip():
                summary = f"{op.method} {op.path}"
            desc = op.operation.get("description")
            desc_str = summary
            if isinstance(desc, str) and desc.strip():
                desc_str = f"{summary}\n\n{desc.strip()}"
            url_raw = backend_postman_url_raw(op.path, backend_api_prefix=backend_api_prefix)
            items.append(_request_item(summary.strip(), op.method, url_raw, desc_str))
        return {"name": tag, "description": f"Generated requests grouped by OpenAPI tag **{tag}**.", "item": items}

    master_items = [folder_for_tag(tag, tag_ops) for tag, tag_ops in grouped.items()]

    master: dict[str, Any] = {
        "info": {
            "name": title,
            "description": (
                "Machine-generated from repository OpenAPI. "
                "Use with `WorldOfShadows_Local` / `WorldOfShadows_Docker` environments. "
                "Hand-curated suites under `postman/WorldOfShadows_*.postman_collection.json` remain the "
                "reference for auth scripts, ordering, and assertions — merge or copy from there as needed."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": master_items,
    }

    subs: dict[str, dict[str, Any]] = {}
    for tag, tag_ops in grouped.items():
        slug = _slug_tag(tag)
        subs[slug] = {
            "info": {
                "name": f"World of Shadows — Suite · {tag}",
                "description": f"Sub-suite for OpenAPI tag **{tag}** (generated).",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [folder_for_tag(tag, tag_ops)],
        }

    return master, subs


def write_json(path: Path, data: Any) -> None:
    """Persist Json so it survives the current process.

    This callable writes or records artifacts as part of its workflow.

    Args:
        path: Filesystem path to the file or directory being processed.
        data: Primary data used by this step.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
