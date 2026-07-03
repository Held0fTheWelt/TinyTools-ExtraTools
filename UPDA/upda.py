#!/usr/bin/env python3
"""Unreal Project Design Assistant.

UPDA is a local-first browser for Blueprint Journals, Blueprint surface
evidence, planning bundles, and deploy-ready implementation plans.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import posixpath
import re
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


TOOL_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = TOOL_ROOT.parents[1]
STATIC_ROOT = TOOL_ROOT / "static"
DEFAULT_STATE_ROOT = WORKSPACE_ROOT / "Saved" / "UPDA"
MAX_BODY_SIZE = 2_000_000
MAX_INDEX_FILE_BYTES = 4_000_000

KIND_LABELS = {
    "project_journal": "Project Journal",
    "project_journal_section": "Project Journal Section",
    "knowledge_journal": "Knowledge Journal",
    "blueprint_surface": "Blueprint Surface",
    "blueprint_surface_index": "Blueprint Surface Index",
    "ubi_reference": "UBI Reference",
    "bpj_reference": "BPJ Reference",
    "planning_document": "Planning Document",
    "architecture_reference": "Architecture Reference",
    "uml_reference": "UML Reference",
    "journal_reference": "Journal Reference",
    "json_artifact": "JSON Artifact",
    "markdown_artifact": "Markdown Artifact",
}


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def write_json(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if length <= 0:
        raise ValueError("Request body is required.")
    if length > MAX_BODY_SIZE:
        raise ValueError("Request body is too large.")
    raw = handler.rfile.read(length)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON body: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object.")
    return payload


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def rel_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(WORKSPACE_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def stable_id(*parts: str) -> str:
    digest = hashlib.sha1("\0".join(parts).encode("utf-8", errors="replace")).hexdigest()
    return digest[:16]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "upda-plan"


def now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def normalize_path_fragment(value: str) -> str:
    value = unquote(value).replace("\\", "/").strip("/")
    normalized = posixpath.normpath(value)
    if normalized in ("", ".") or normalized.startswith("../") or normalized == "..":
        raise ValueError("Invalid path.")
    return normalized


def first_heading(source: str, fallback: str) -> str:
    for line in source.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return fallback


def parse_fields(source: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in source.splitlines()[:120]:
        match = re.match(r"^\s*[-*]\s+([^:]{2,80}):\s*(.*?)\s*$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        value = value.replace("`", "").strip()
        if key and value:
            fields[key] = value
    return fields


def parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace(";", ",")
    tags = []
    for part in normalized.split(","):
        tag = part.strip().strip("`").strip()
        if tag:
            tags.append(tag)
    return sorted(dict.fromkeys(tags), key=str.lower)


def extract_headings(source: str) -> list[str]:
    headings = []
    for line in source.splitlines():
        match = re.match(r"^\s{0,3}#{2,4}\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def extract_section(source: str, heading: str) -> str:
    target = heading.strip().lower()
    lines = source.splitlines()
    start = None
    level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^\s{0,3}(#{2,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        if match.group(2).strip().lower() == target:
            start = index + 1
            level = len(match.group(1))
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        match = re.match(r"^\s{0,3}(#{2,6})\s+", lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def build_excerpt(source: str, max_chars: int = 420) -> str:
    cleaned_lines = []
    in_code = False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if re.match(r"^[-*]\s+[^:]{2,80}:", stripped):
            continue
        if stripped.startswith("|"):
            continue
        cleaned_lines.append(stripped)
        if sum(len(item) for item in cleaned_lines) > max_chars:
            break
    excerpt = " ".join(cleaned_lines)
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "..."
    return excerpt


def count_markdown_table_rows(section: str) -> int:
    rows = [line for line in section.splitlines() if line.strip().startswith("|")]
    return max(0, len(rows) - 2) if len(rows) >= 2 else 0


def make_record(
    *,
    kind: str,
    title: str,
    path: Path,
    source_label: str,
    content: str,
    fields: dict[str, str] | None = None,
    tags: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    sections: dict[str, str] | None = None,
    sub_id: str = "",
) -> dict[str, Any]:
    fields = fields or {}
    sections = sections or {}
    headings = extract_headings(content)
    project = fields.get("Project") or fields.get("Source Project") or ""
    status = fields.get("Status") or fields.get("State") or ""
    focus = fields.get("Current Focus") or fields.get("Purpose") or ""
    record_tags = tags if tags is not None else parse_tags(fields.get("Tags"))
    search_parts = [
        title,
        kind,
        project,
        status,
        focus,
        " ".join(record_tags),
        " ".join(headings),
        content[:80_000],
    ]
    item_id = stable_id(kind, str(path.resolve()), sub_id)
    return {
        "id": item_id,
        "kind": kind,
        "kind_label": KIND_LABELS.get(kind, kind.replace("_", " ").title()),
        "title": title,
        "path": str(path),
        "rel_path": rel_label(path),
        "source_label": source_label,
        "project": project,
        "status": status,
        "focus": focus,
        "confidence": fields.get("Confidence", ""),
        "tags": record_tags,
        "fields": fields,
        "metrics": metrics or {},
        "headings": headings,
        "sections": sections,
        "excerpt": build_excerpt(content),
        "content": content,
        "search_blob": "\n".join(search_parts).lower(),
    }


def parse_markdown(path: Path, kind: str, source_label: str) -> dict[str, Any] | None:
    try:
        if path.stat().st_size > MAX_INDEX_FILE_BYTES:
            return None
    except OSError:
        return None
    content = read_text(path)
    fields = parse_fields(content)
    construction = extract_section(content, "Construction Instructions")
    backlog = extract_section(content, "Specification Backlog")
    evidence = extract_section(content, "Evidence Snapshot")
    open_requests = extract_section(content, "Open Evidence Requests")
    sections = {
        "construction_instructions": construction,
        "specification_backlog": backlog,
        "evidence_snapshot": evidence,
        "open_evidence_requests": open_requests,
    }
    metrics = {
        "headings": len(extract_headings(content)),
        "construction_lines": len([line for line in construction.splitlines() if line.strip()]),
        "backlog_items": count_markdown_table_rows(backlog),
        "bytes": path.stat().st_size,
    }
    return make_record(
        kind=kind,
        title=first_heading(content, path.stem.replace("-", " ").title()),
        path=path,
        source_label=source_label,
        content=content,
        fields=fields,
        metrics=metrics,
        sections=sections,
    )


def function_pin_count(function: dict[str, Any], field: str) -> int:
    value = function.get(field)
    return len(value) if isinstance(value, list) else 0


def summarize_blueprint_functions(functions: list[dict[str, Any]]) -> str:
    lines = []
    for function in functions[:80]:
        display = function.get("display_name") or function.get("function_name") or "Function"
        mutates = "mutates" if function.get("mutates") else "read"
        inputs = function_pin_count(function, "inputs")
        outputs = function_pin_count(function, "outputs")
        description = function.get("description") or ""
        lines.append(f"- {display} ({mutates}, inputs: {inputs}, outputs: {outputs})")
        if description:
            lines.append(f"  {description}")
    if len(functions) > 80:
        lines.append(f"- ... {len(functions) - 80} more functions")
    return "\n".join(lines)


def parse_blueprint_catalog(path: Path, source_label: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError):
        return []
    if data.get("schema_version") != "ttd.blueprint_surface_catalog.v2":
        return []
    records = []
    libraries = data.get("libraries") if isinstance(data.get("libraries"), list) else []
    for library in libraries:
        if not isinstance(library, dict):
            continue
        functions = [item for item in library.get("functions", []) if isinstance(item, dict)]
        plugin = library.get("plugin_name") or library.get("friendly_name") or "Blueprint Surface"
        friendly = library.get("friendly_name") or plugin
        title = f"{friendly} Blueprint Surface"
        mutable_count = sum(1 for item in functions if item.get("mutates"))
        editor_count = sum(1 for item in functions if item.get("call_in_editor"))
        tags = [
            str(value)
            for value in [
                library.get("plugin_name"),
                library.get("abbrev"),
                library.get("blueprint_type"),
                library.get("library_scope"),
                library.get("showcase_kind"),
                library.get("graph_strategy"),
                library.get("cpp_module"),
            ]
            if value
        ]
        tags.extend(sorted({str(item.get("surface_kind")) for item in functions if item.get("surface_kind")}))
        content = json.dumps(library, ensure_ascii=False, indent=2)
        fields = {
            "Plugin": str(plugin),
            "Unreal Asset": str(library.get("unreal_asset_path") or ""),
            "Blueprint Parent": str(library.get("blueprint_parent_class") or ""),
            "C++ Class": str(library.get("cpp_parent_class") or ""),
            "Module": str(library.get("cpp_module") or ""),
            "Graph Strategy": str(library.get("graph_strategy") or ""),
            "Showcase Kind": str(library.get("showcase_kind") or ""),
        }
        metrics = {
            "functions": len(functions),
            "mutable_functions": mutable_count,
            "editor_functions": editor_count,
            "input_pins": sum(function_pin_count(item, "inputs") for item in functions),
            "output_pins": sum(function_pin_count(item, "outputs") for item in functions),
        }
        sections = {
            "function_summary": summarize_blueprint_functions(functions),
            "construction_instructions": "",
            "specification_backlog": "",
            "evidence_snapshot": "",
            "open_evidence_requests": "",
        }
        records.append(
            make_record(
                kind="blueprint_surface",
                title=title,
                path=path,
                source_label=source_label,
                content=content,
                fields=fields,
                tags=tags,
                metrics=metrics,
                sections=sections,
                sub_id=str(plugin),
            )
        )
    return records


def parse_json_artifact(path: Path, kind: str, source_label: str) -> list[dict[str, Any]]:
    try:
        if path.stat().st_size > MAX_INDEX_FILE_BYTES:
            return []
        data = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError):
        return []
    catalog = parse_blueprint_catalog(path, source_label)
    if catalog:
        return catalog
    keys = list(data.keys()) if isinstance(data, dict) else []
    content = json.dumps(data, ensure_ascii=False, indent=2)
    fields = {
        "Schema": str(data.get("schema") or data.get("schema_version") or "") if isinstance(data, dict) else "",
        "Top-level keys": ", ".join(keys[:12]),
    }
    metrics = {
        "bytes": path.stat().st_size,
        "top_level_keys": len(keys),
    }
    title = path.stem.replace("_", " ").replace("-", " ").title()
    return [
        make_record(
            kind=kind,
            title=title,
            path=path,
            source_label=source_label,
            content=content,
            fields=fields,
            tags=[],
            metrics=metrics,
        )
    ]


def default_source_descriptors(workspace_root: Path) -> list[dict[str, Any]]:
    git = workspace_root / "Git"
    return [
        {
            "label": "BPJ Project Journal Index",
            "root": git / "docs" / "BPJ" / "project-journals" / "README.md",
            "kind": "journal_reference",
            "patterns": ["*.md"],
        },
        {
            "label": "BPJ Project Journals",
            "root": git / "docs" / "BPJ" / "project-journals",
            "kind": "project_journal",
            "patterns": ["*/*-journal.md", "*/README.md"],
        },
        {
            "label": "BPJ Project Journal Sections",
            "root": git / "docs" / "BPJ" / "project-journals",
            "kind": "project_journal_section",
            "patterns": ["*/*.md"],
        },
        {
            "label": "BPJ Knowledge Journals",
            "root": git / "docs" / "BPJ" / "knowledge",
            "kind": "knowledge_journal",
            "patterns": ["**/*.md"],
        },
        {
            "label": "BPJ Specification",
            "root": git / "docs" / "BPJ" / "Best_Practices_Journal_Specification.md",
            "kind": "journal_reference",
            "patterns": ["*.md"],
        },
    ]


class UPDAApplication:
    def __init__(self, source_roots: list[Path] | None = None, state_root: Path = DEFAULT_STATE_ROOT):
        self.state_root = state_root
        self.deploy_root = self.state_root / "deploy"
        self.records: list[dict[str, Any]] = []
        self.record_by_id: dict[str, dict[str, Any]] = {}
        self.source_descriptors = default_source_descriptors(WORKSPACE_ROOT)
        for root in source_roots or []:
            self.source_descriptors.append(
                {
                    "label": f"Custom Source: {root.name}",
                    "root": root,
                    "kind": "markdown_artifact",
                    "patterns": ["**/*.md", "**/*.json"],
                }
            )
        self.rebuild_index()

    @property
    def state_path(self) -> Path:
        return self.state_root / "planning.json"

    def rebuild_index(self) -> None:
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for descriptor in self.source_descriptors:
            root = Path(descriptor["root"])
            if not root.exists():
                continue
            label = str(descriptor["label"])
            kind = str(descriptor["kind"])
            patterns = descriptor.get("patterns") or ["*.md", "*.json"]
            paths: list[Path] = []
            if root.is_file():
                paths = [root]
            else:
                for pattern in patterns:
                    paths.extend(path for path in root.glob(pattern) if path.is_file())
            for path in sorted(dict.fromkeys(paths)):
                marker = str(path.resolve()).lower()
                if marker in seen:
                    continue
                seen.add(marker)
                suffix = path.suffix.lower()
                if suffix in {".md", ".markdown"}:
                    record = parse_markdown(path, kind, label)
                    if record:
                        records.append(record)
                elif suffix in {".json", ".yml", ".yaml"}:
                    if suffix == ".json":
                        records.extend(parse_json_artifact(path, "json_artifact" if kind == "markdown_artifact" else kind, label))
                    else:
                        record = parse_markdown(path, kind, label)
                        if record:
                            records.append(record)
        self.records = sorted(records, key=lambda item: (item["kind_label"].lower(), item["title"].lower(), item["rel_path"].lower()))
        self.record_by_id = {item["id"]: item for item in self.records}

    def public_item(self, record: dict[str, Any], include_detail: bool = False) -> dict[str, Any]:
        payload = {key: value for key, value in record.items() if key not in {"content", "search_blob"}}
        if not include_detail:
            payload.pop("sections", None)
            payload.pop("fields", None)
            payload["section_flags"] = {
                key: bool(value)
                for key, value in record.get("sections", {}).items()
                if key in {"construction_instructions", "specification_backlog", "evidence_snapshot", "open_evidence_requests", "function_summary"}
            }
        else:
            content = record.get("content", "")
            payload["content_preview"] = content[:40_000]
        return payload

    def filter_records(self, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        text = (query.get("q", [""])[0] or "").strip().lower()
        kind = query.get("kind", ["all"])[0] or "all"
        tag = query.get("tag", ["all"])[0] or "all"
        project = query.get("project", ["all"])[0] or "all"
        status = query.get("status", ["all"])[0] or "all"
        tokens = [token for token in re.split(r"\s+", text) if token]
        result = []
        for record in self.records:
            if kind != "all" and record["kind"] != kind:
                continue
            if tag != "all" and tag not in record.get("tags", []):
                continue
            if project != "all" and project != (record.get("project") or ""):
                continue
            if status != "all" and status != (record.get("status") or ""):
                continue
            if tokens and not all(token in record["search_blob"] for token in tokens):
                continue
            result.append(record)
        return result

    def filter_options(self) -> dict[str, Any]:
        kinds = sorted({record["kind"] for record in self.records})
        tags = sorted({tag for record in self.records for tag in record.get("tags", [])}, key=str.lower)
        projects = sorted({record.get("project") or "" for record in self.records if record.get("project")}, key=str.lower)
        statuses = sorted({record.get("status") or "" for record in self.records if record.get("status")}, key=str.lower)
        return {
            "kinds": [{"value": kind, "label": KIND_LABELS.get(kind, kind)} for kind in kinds],
            "tags": tags,
            "projects": projects,
            "statuses": statuses,
        }

    def overview(self) -> dict[str, Any]:
        by_kind: dict[str, int] = {}
        for record in self.records:
            by_kind[record["kind"]] = by_kind.get(record["kind"], 0) + 1
        blueprint_functions = sum(int(record.get("metrics", {}).get("functions") or 0) for record in self.records)
        projects = []
        seen_projects = set()
        for record in self.records:
            if record.get("kind") != "project_journal":
                continue
            project_name = record.get("fields", {}).get("Project") or record.get("title")
            marker = project_name.lower()
            if marker in seen_projects:
                continue
            seen_projects.add(marker)
            projects.append(
                {
                    "name": project_name,
                    "source_project": record.get("fields", {}).get("Source Project", ""),
                    "status": record.get("status", ""),
                    "focus": record.get("focus", ""),
                    "record_id": record.get("id", ""),
                    "title": record.get("title", ""),
                    "rel_path": record.get("rel_path", ""),
                }
            )
        state = self.read_state()
        deploys = self.list_deploys()
        sources = []
        for descriptor in self.source_descriptors:
            root = Path(descriptor["root"])
            sources.append(
                {
                    "label": descriptor["label"],
                    "path": str(root),
                    "rel_path": rel_label(root),
                    "exists": root.exists(),
                    "kind": descriptor["kind"],
                    "count": sum(1 for record in self.records if record.get("source_label") == descriptor["label"]),
                }
            )
        return {
            "name": "Unreal Project Design Assistant",
            "abbrev": "UPDA",
            "workspace_root": str(WORKSPACE_ROOT),
            "state_root": str(self.state_root),
            "total_items": len(self.records),
            "by_kind": by_kind,
            "blueprint_functions": blueprint_functions,
            "project_journals": by_kind.get("project_journal", 0),
            "knowledge_journals": by_kind.get("knowledge_journal", 0),
            "journal_projects": len(projects),
            "projects": projects,
            "planning_packages": len(state.get("packages", [])),
            "deploy_plans": len(deploys),
            "sources": sources,
            "workflow": [
                {
                    "name": "Overview",
                    "purpose": "Shows Blueprint Journal scope, indexed journal sources, and derived project cases.",
                },
                {
                    "name": "Review",
                    "purpose": "Searches project journals, reusable BPJ knowledge, construction instructions, and project evidence notes.",
                },
                {
                    "name": "Planning",
                    "purpose": "Collects journal records into named project work packages with priority, status, and notes.",
                },
                {
                    "name": "Deploy",
                    "purpose": "Generates implementation-preparation Markdown from selected journal packages.",
                },
            ],
        }

    def read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "schema": "ttd.upda.planning.v1",
                "packages": [],
            }
        try:
            data = json.loads(read_text(self.state_path))
        except (OSError, json.JSONDecodeError):
            return {
                "schema": "ttd.upda.planning.v1",
                "packages": [],
                "warning": "planning state could not be parsed",
            }
        if not isinstance(data, dict):
            return {"schema": "ttd.upda.planning.v1", "packages": []}
        data.setdefault("schema", "ttd.upda.planning.v1")
        data.setdefault("packages", [])
        return data

    def write_state(self, state: dict[str, Any]) -> None:
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def enrich_package(self, package: dict[str, Any]) -> dict[str, Any]:
        item_ids = [item_id for item_id in package.get("item_ids", []) if isinstance(item_id, str)]
        items = [self.public_item(self.record_by_id[item_id]) for item_id in item_ids if item_id in self.record_by_id]
        enriched = dict(package)
        enriched["items"] = items
        enriched["missing_item_ids"] = [item_id for item_id in item_ids if item_id not in self.record_by_id]
        return enriched

    def planning_payload(self) -> dict[str, Any]:
        state = self.read_state()
        packages = [self.enrich_package(package) for package in state.get("packages", []) if isinstance(package, dict)]
        return {
            "schema": state.get("schema"),
            "state_path": str(self.state_path),
            "packages": packages,
        }

    def create_package(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or "").strip() or "New UPDA Package"
        item_ids = [str(item_id) for item_id in payload.get("item_ids", []) if str(item_id) in self.record_by_id]
        stamp = now_stamp()
        package = {
            "id": stable_id("package", title, stamp),
            "title": title,
            "notes": str(payload.get("notes") or ""),
            "priority": str(payload.get("priority") or "P1"),
            "status": str(payload.get("status") or "draft"),
            "item_ids": sorted(dict.fromkeys(item_ids)),
            "created_at": stamp,
            "updated_at": stamp,
        }
        state = self.read_state()
        state.setdefault("packages", []).append(package)
        self.write_state(state)
        return self.enrich_package(package)

    def update_package(self, payload: dict[str, Any]) -> dict[str, Any]:
        package_id = str(payload.get("id") or "")
        if not package_id:
            raise ValueError("Package id is required.")
        state = self.read_state()
        packages = state.setdefault("packages", [])
        for package in packages:
            if not isinstance(package, dict) or package.get("id") != package_id:
                continue
            for field in ("title", "notes", "priority", "status"):
                if field in payload:
                    package[field] = str(payload.get(field) or "")
            if "item_ids" in payload:
                package["item_ids"] = sorted(
                    dict.fromkeys(str(item_id) for item_id in payload.get("item_ids", []) if str(item_id) in self.record_by_id)
                )
            package["updated_at"] = now_stamp()
            self.write_state(state)
            return self.enrich_package(package)
        raise ValueError("Package not found.")

    def delete_package(self, payload: dict[str, Any]) -> dict[str, Any]:
        package_id = str(payload.get("id") or "")
        state = self.read_state()
        before = len(state.get("packages", []))
        state["packages"] = [package for package in state.get("packages", []) if not isinstance(package, dict) or package.get("id") != package_id]
        self.write_state(state)
        return {"deleted": before - len(state["packages"])}

    def list_deploys(self) -> list[dict[str, Any]]:
        if not self.deploy_root.exists():
            return []
        deploys = []
        for path in sorted(self.deploy_root.glob("*.md"), key=lambda item: item.stat().st_mtime, reverse=True):
            deploys.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "rel_path": rel_label(path),
                    "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)),
                    "bytes": path.stat().st_size,
                }
            )
        return deploys

    def deploy_markdown_for_package(self, package: dict[str, Any]) -> str:
        item_ids = [item_id for item_id in package.get("item_ids", []) if item_id in self.record_by_id]
        records = [self.record_by_id[item_id] for item_id in item_ids]
        lines = [
            f"# UPDA Deploy Plan: {package.get('title') or 'Untitled Package'}",
            "",
            f"- UPDA Artifact: `deploy_plan`",
            f"- Created: `{now_stamp()}`",
            f"- Package ID: `{package.get('id', '')}`",
            f"- Status: `{package.get('status', 'draft')}`",
            f"- Priority: `{package.get('priority', 'P1')}`",
            f"- Source Count: `{len(records)}`",
            "",
            "## Planning Notes",
            "",
            str(package.get("notes") or "No package notes yet.").strip(),
            "",
            "## Source Evidence",
            "",
            "| Source | Kind | Status | Path |",
            "| --- | --- | --- | --- |",
        ]
        for record in records:
            lines.append(
                f"| {record['title']} | {record['kind_label']} | {record.get('status') or ''} | `{record['rel_path']}` |"
            )
        lines.extend(["", "## Implementation Preparation", ""])
        for record in records:
            lines.extend([f"### {record['title']}", ""])
            if record.get("excerpt"):
                lines.extend([record["excerpt"], ""])
            fields = record.get("fields", {})
            if fields:
                lines.extend(["Key facts:", ""])
                for key, value in fields.items():
                    if value:
                        lines.append(f"- {key}: {value}")
                lines.append("")
            function_summary = record.get("sections", {}).get("function_summary", "")
            if function_summary:
                lines.extend(["Blueprint surface functions:", "", function_summary, ""])
            construction = record.get("sections", {}).get("construction_instructions", "")
            if construction:
                lines.extend(["Construction instructions:", "", construction, ""])
            backlog = record.get("sections", {}).get("specification_backlog", "")
            if backlog:
                lines.extend(["Specification backlog:", "", backlog, ""])
            open_requests = record.get("sections", {}).get("open_evidence_requests", "")
            if open_requests:
                lines.extend(["Open evidence requests:", "", open_requests, ""])
        lines.extend(
            [
                "## Deploy Checklist",
                "",
                "- [ ] Confirm source evidence paths still exist.",
                "- [ ] Split package into implementation slices.",
                "- [ ] Assign owner, target module, and validation path per slice.",
                "- [ ] Prepare Unreal-side dry run or preview where mutation is involved.",
                "- [ ] Record post-implementation evidence back into BPJ/UPDA.",
                "",
                "## Acceptance Gates",
                "",
                "- [ ] Blueprint behavior reviewed against selected journals.",
                "- [ ] C++ or Blueprint changes have local verification evidence.",
                "- [ ] Design decisions have a durable documentation target.",
                "- [ ] Packaging/deploy impacts are listed before execution.",
                "",
            ]
        )
        return "\n".join(lines)

    def create_deploy_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        package_id = str(payload.get("package_id") or "")
        package = None
        for candidate in self.read_state().get("packages", []):
            if isinstance(candidate, dict) and candidate.get("id") == package_id:
                package = candidate
                break
        if package is None:
            raise ValueError("Package not found.")
        markdown = self.deploy_markdown_for_package(package)
        self.deploy_root.mkdir(parents=True, exist_ok=True)
        filename = f"{now_stamp()}-{slugify(str(package.get('title') or 'upda-plan'))}.md"
        path = self.deploy_root / filename
        path.write_text(markdown, encoding="utf-8")
        return {
            "name": path.name,
            "path": str(path),
            "rel_path": rel_label(path),
            "bytes": path.stat().st_size,
        }


class UPDAServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], app: UPDAApplication):
        super().__init__(server_address, handler_class)
        self.app = app


class UPDAHandler(BaseHTTPRequestHandler):
    server_version = "UPDA/0.1"

    @property
    def app(self) -> UPDAApplication:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/overview":
                write_json(self, {"ok": True, "overview": self.app.overview(), "filters": self.app.filter_options()})
            elif parsed.path == "/api/items":
                records = self.app.filter_records(query)
                write_json(
                    self,
                    {
                        "ok": True,
                        "items": [self.app.public_item(record) for record in records],
                        "count": len(records),
                        "total": len(self.app.records),
                        "filters": self.app.filter_options(),
                    },
                )
            elif parsed.path == "/api/item":
                item_id = query.get("id", [""])[0]
                record = self.app.record_by_id.get(item_id)
                if not record:
                    write_json(self, {"ok": False, "error": "Item not found."}, HTTPStatus.NOT_FOUND)
                    return
                write_json(self, {"ok": True, "item": self.app.public_item(record, include_detail=True)})
            elif parsed.path == "/api/planning":
                write_json(self, {"ok": True, "planning": self.app.planning_payload()})
            elif parsed.path == "/api/deploy":
                write_json(self, {"ok": True, "deploys": self.app.list_deploys()})
            elif parsed.path == "/api/reindex":
                self.app.rebuild_index()
                write_json(self, {"ok": True, "overview": self.app.overview()})
            else:
                self.serve_static(parsed.path)
        except Exception as exc:  # noqa: BLE001 - local tool should return clear errors
            write_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = read_json_body(self)
            if parsed.path == "/api/planning/create":
                package = self.app.create_package(payload)
                write_json(self, {"ok": True, "package": package, "planning": self.app.planning_payload()})
            elif parsed.path == "/api/planning/update":
                package = self.app.update_package(payload)
                write_json(self, {"ok": True, "package": package, "planning": self.app.planning_payload()})
            elif parsed.path == "/api/planning/delete":
                result = self.app.delete_package(payload)
                write_json(self, {"ok": True, "result": result, "planning": self.app.planning_payload()})
            elif parsed.path == "/api/deploy/create":
                deploy = self.app.create_deploy_plan(payload)
                write_json(self, {"ok": True, "deploy": deploy, "deploys": self.app.list_deploys()})
            else:
                write_json(self, {"ok": False, "error": "Unknown endpoint."}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            write_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            write_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def serve_static(self, request_path: str) -> None:
        fragment = "index.html" if request_path in {"", "/"} else normalize_path_fragment(request_path)
        target = (STATIC_ROOT / fragment).resolve()
        if not path_is_within(target, STATIC_ROOT) or not target.is_file():
            write_json(self, {"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix.lower() in {".html", ".css", ".js"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Unreal Project Design Assistant.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8776, help="Bind port.")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT, help="Planning/deploy state root.")
    parser.add_argument("--source-root", action="append", type=Path, default=[], help="Additional source root to index.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    app = UPDAApplication(source_roots=args.source_root, state_root=args.state_root)
    server = UPDAServer((args.host, args.port), UPDAHandler, app)
    print(f"UPDA: http://{args.host}:{args.port}")
    print(f"Workspace: {WORKSPACE_ROOT}")
    print(f"Indexed: {len(app.records)} records")
    print(f"State: {args.state_root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UPDA.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
