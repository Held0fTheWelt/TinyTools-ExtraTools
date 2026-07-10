#!/usr/bin/env python3
"""Local UML browser for PlantUML files.

The server intentionally uses only the Python standard library. PlantUML SVG
rendering is enabled when either `plantuml` is on PATH or `PLANTUML_JAR` points
to a local jar and `java` is available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import time
import zlib
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


TOOL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TOOL_ROOT.parents[1]
DEFAULT_SAMPLE_ROOT = TOOL_ROOT / "samples"
DEFAULT_CACHE_ROOT = REPO_ROOT / "Saved" / "UmlBrowser"
STATIC_ROOT = TOOL_ROOT / "static"
PLANTUML_SUFFIXES = {".puml", ".uml"}
MERMAID_SUFFIXES = {".mmd", ".mermaid"}
DIAGRAM_SUFFIXES = PLANTUML_SUFFIXES | MERMAID_SUFFIXES
MAX_SEARCH_MATCHES_PER_FILE = 8
MAX_BODY_SIZE = 2_000_000
COMPOSITION_PACKAGE = Path("Project") / "tiny-tools-compositions"
FAMILY_ORDER = ("components", "sequence", "flow", "use-cases", "classes", "states", "objects", "packages", "traceability", "project", "library", "other")
PLANTUML_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
KNOWN_TOOL_LABELS = {
    "UII": "UnrealIntegrationIntelligence",
    "SCD": "SmartContentDiet",
    "SDA": "SmartDocumentationAssistant",
    "IIS": "InternalIndexService",
    "UCM": "UnrealCapabilityMesh",
    "UMCP": "UnifiedMcpServer",
    "PRS": "ProjectRestructureService",
    "NCU": "NamingConventionUtility",
    "PPW": "PerformancePresetWizard",
    "CCE": "CodeCopyrightEditor",
    "LLE": "LogLevelEditor",
    "LLMStore": "LLMStore",
    "InternalIndexService": "InternalIndexService",
    "UnrealCapabilityMesh": "UnrealCapabilityMesh",
    "UnifiedMcpServer": "UnifiedMcpServer",
    "ProjectRestructureService": "ProjectRestructureService",
    "NamingConventionUtility": "NamingConventionUtility",
    "PerformancePresetWizard": "PerformancePresetWizard",
    "CodeCopyrightEditor": "CodeCopyrightEditor",
    "LogLevelEditor": "LogLevelEditor",
    "SmartContentDiet": "SmartContentDiet",
    "SmartDocumentationAssistant": "SmartDocumentationAssistant",
    "UnrealIntegrationIntelligence": "UnrealIntegrationIntelligence",
}


def first_existing_path(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


DEFAULT_PROJECT_UML_ROOT = first_existing_path(
    (
        REPO_ROOT / "UML",
        REPO_ROOT / "Git" / "UML",
        REPO_ROOT / "AKDB" / "export" / "uml",
        DEFAULT_SAMPLE_ROOT,
    )
)
DEFAULT_UML_ROOT = DEFAULT_PROJECT_UML_ROOT


@dataclass(frozen=True)
class Renderer:
    command: tuple[str, ...] | None
    label: str
    available: bool
    reason: str


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def write_json(handler: SimpleHTTPRequestHandler, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def write_text(handler: SimpleHTTPRequestHandler, text: str, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
    data = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json_body(handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
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


def normalize_rel_path(value: str) -> str:
    value = unquote(value).replace("\\", "/").strip("/")
    normalized = posixpath.normpath(value)
    if normalized in ("", ".") or normalized.startswith("../") or normalized == "..":
        raise ValueError("Invalid UML path.")
    return normalized


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def extract_title(source: str, path: Path) -> str:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("'"):
            continue
        if stripped.startswith("%%"):
            mermaid_title = re.match(r"%%\s*title\s*:\s*(.+)", stripped, re.IGNORECASE)
            if mermaid_title:
                return mermaid_title.group(1).strip() or path.stem
            continue
        if stripped.lower().startswith("title "):
            return stripped[6:].strip() or path.stem
        if stripped.lower().startswith("title:"):
            return stripped[6:].strip() or path.stem
        match = re.match(r"@start(?:uml|mindmap|wbs|gantt|json|yaml)\s+(.+)", stripped, re.IGNORECASE)
        if match:
            return match.group(1).strip() or path.stem
    return path.stem


def companion_for(path: Path) -> Path:
    return path.with_suffix(".md")


def find_first_mermaid_block(markdown: str) -> str | None:
    match = re.search(r"```mermaid\s*\r?\n(.*?)\r?\n```", markdown, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def diagram_format(path: Path) -> str:
    return "mermaid" if path.suffix.lower() in MERMAID_SUFFIXES else "plantuml"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "item"


def uml_family(rel_path: str) -> str:
    normalized_path = rel_path.replace("\\", "/").lower()
    normalized = f"/{normalized_path}"
    if "/_includes/" in normalized:
        return "library"
    if normalized.endswith("/traceability.puml") or normalized.endswith("/traceability.uml"):
        return "traceability"
    if "/project/" in normalized:
        for family in FAMILY_ORDER:
            if family in {"traceability", "project", "library", "other"}:
                continue
            if f"/{family}/" in normalized:
                return family
        return "project"
    for family in FAMILY_ORDER:
        if family in {"traceability", "project", "library", "other"}:
            continue
        if f"/{family}/" in normalized:
            return family
    return "other"


def diagram_scope(rel_path: str) -> str:
    parts = Path(rel_path).parts
    if not parts:
        return "other"
    first = parts[0].lower()
    if first == "plugins":
        return "plugin"
    if first == "project":
        return "project"
    if first == "_includes":
        return "library"
    return "other"


def diagram_plugin(rel_path: str) -> str:
    parts = Path(rel_path).parts
    if len(parts) >= 2 and parts[0].lower() == "plugins":
        return parts[1]
    return ""


def diagram_group(rel_path: str) -> str:
    parts = Path(rel_path).parts
    scope = diagram_scope(rel_path)
    if scope == "plugin" and len(parts) >= 2:
        return parts[1]
    if scope == "project" and len(parts) >= 2:
        return f"Project / {parts[1]}"
    if scope == "library":
        return "Shared libraries"
    return "Other"


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def plantuml_encode(text: str) -> str:
    compressed = zlib.compress(text.encode("utf-8"))[2:-4]
    encoded = []
    for index in range(0, len(compressed), 3):
        chunk = compressed[index : index + 3]
        b1 = chunk[0]
        b2 = chunk[1] if len(chunk) > 1 else 0
        b3 = chunk[2] if len(chunk) > 2 else 0
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        encoded.extend(PLANTUML_ALPHABET[item] for item in (c1, c2, c3, c4))
    return "".join(encoded)


def plantuml_preview_url(source: str) -> str:
    return f"https://www.plantuml.com/plantuml/svg/{plantuml_encode(source)}"


def markdown_heading(text: str) -> str | None:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+)", line.strip())
        if match:
            return match.group(1).strip()
    return None


def markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def first_markdown_paragraph(text: str) -> str:
    cleaned_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if cleaned_lines:
                break
            continue
        if line.startswith("```") or line.startswith("|") or line.startswith("- "):
            continue
        cleaned_lines.append(line)
    return " ".join(cleaned_lines).strip()


def markdown_links(text: str) -> list[dict[str, str]]:
    links = []
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        label = match.group(1).strip()
        href = match.group(2).strip()
        if label and href:
            links.append({"label": label, "href": href})
    return links


def extract_known_tools(text: str) -> list[str]:
    found: list[str] = []
    for token, canonical in KNOWN_TOOL_LABELS.items():
        if re.search(rf"\b{re.escape(token)}\b", text):
            if canonical not in found:
                found.append(canonical)
    return found


def composition_status_label(text: str) -> str:
    candidate = first_markdown_paragraph(text).strip()
    if not candidate:
        return "Reference"
    first_sentence = re.split(r"(?<=[.!?])\s+", candidate, maxsplit=1)[0].strip()
    first_sentence = first_sentence.rstrip(".!?")
    for known in ("Implemented", "Partially implemented", "Target-state", "Experimental", "Rejected", "Reference"):
        if first_sentence.lower().startswith(known.lower()):
            return known
    return first_sentence[:64] or "Reference"


def normalize_model_id(value: str) -> str:
    cleaned = value.strip().strip("\"'[](){}")
    cleaned = re.sub(r"\s+as\s+[A-Za-z_][\w.:-]*$", "", cleaned, flags=re.IGNORECASE)
    normalized = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", cleaned).strip("_")
    return normalized or "item"


def clean_model_label(value: str) -> str:
    value = value.strip().rstrip("{").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value.strip()


def add_model_element(
    elements: dict[str, dict[str, Any]],
    aliases: dict[str, str],
    element_id: str,
    label: str,
    kind: str,
    line_no: int,
    package_stack: list[str] | None = None,
    implicit: bool = False,
) -> None:
    normalized = normalize_model_id(element_id)
    label = clean_model_label(label) or normalized
    aliases.setdefault(label, normalized)
    aliases.setdefault(normalized, normalized)
    existing = elements.get(normalized)
    if existing:
        if existing.get("implicit") and not implicit:
            existing.update({"label": label, "kind": kind.lower(), "line": line_no, "implicit": False})
        return
    elements[normalized] = {
        "id": normalized,
        "label": label,
        "kind": kind.lower(),
        "line": line_no,
        "package": " / ".join(package_stack or []),
        "implicit": implicit,
    }


def endpoint_model_id(value: str, aliases: dict[str, str]) -> str:
    cleaned = clean_model_label(value)
    cleaned = re.sub(r"\s+as\s+[A-Za-z_][\w.:-]*$", "", cleaned, flags=re.IGNORECASE).strip()
    return aliases.get(cleaned, normalize_model_id(cleaned))


def parse_alias_body(body: str) -> tuple[str, str]:
    body = body.strip().rstrip("{").strip()
    match = re.match(r"^(.+?)\s+as\s+([A-Za-z_][\w.:-]*)$", body, re.IGNORECASE)
    if match:
        return match.group(2).strip(), clean_model_label(match.group(1))
    if body.startswith('"'):
        quoted = re.match(r'^"([^"]+)"', body)
        if quoted:
            label = quoted.group(1)
            return normalize_model_id(label), label
    label = clean_model_label(body.split()[0] if " " in body and not body.startswith("[") else body)
    return normalize_model_id(label), clean_model_label(body)


def parse_model_summary(path: Path, text: str) -> dict[str, Any]:
    source_type = "mermaid" if path.suffix.lower() in MERMAID_SUFFIXES else "plantuml"
    title = extract_title(text, path)
    sequence = parse_sequence_model(text, title)
    if sequence:
        return {**sequence, "path": path.as_posix(), "lineCount": len(text.splitlines())}
    activity = parse_activity_model(text, title)
    if activity:
        return {**activity, "path": path.as_posix(), "lineCount": len(text.splitlines())}
    c4 = parse_c4_model(text, title)
    if c4:
        return {**c4, "path": path.as_posix(), "lineCount": len(text.splitlines())}

    elements: dict[str, dict[str, Any]] = {}
    aliases: dict[str, str] = {}
    relationships: list[dict[str, Any]] = []
    warnings: list[str] = []
    package_stack: list[str] = []
    relation_re = re.compile(
        r"^(?P<left>.+?)\s+(?P<arrow><\|--|--\|>|<--|-->|<-|->|<\.\.|\.{2}>|\.\.>|--|\.\.)\s+(?P<right>.+?)(?:\s*:\s*(?P<label>.+))?$"
    )
    declaration_re = re.compile(
        r"^(?P<kind>actor|artifact|class|cloud|component|database|enum|folder|interface|node|package|queue|rectangle|storage|usecase)\s+(?P<body>.+)$",
        re.IGNORECASE,
    )
    bracket_re = re.compile(r"^\[(?P<label>.+?)\](?:\s+as\s+(?P<alias>[A-Za-z_][\w.:-]*))?", re.IGNORECASE)
    mermaid_node_re = re.compile(r"(?P<id>[A-Za-z_][\w.-]*)\s*(?:\[(?P<bracket>[^\]]+)\]|\((?P<round>[^)]+)\)|\{(?P<brace>[^}]+)\})?")

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("'") or line.startswith("//") or line.startswith("!"):
            continue
        if line.lower().startswith("title "):
            title = line[6:].strip() or title
            continue
        if line.startswith("@"):
            continue
        if line == "}":
            if package_stack:
                package_stack.pop()
            continue
        if source_type == "mermaid" and ("-->" in line or "---" in line):
            arrow = "-->" if "-->" in line else "---"
            left_text, right_text = line.split(arrow, 1)
            left = mermaid_node_re.search(left_text.strip())
            right = mermaid_node_re.search(right_text.strip())
            if left and right:
                for match in (left, right):
                    element_id = match.group("id")
                    label = match.group("bracket") or match.group("round") or match.group("brace") or element_id
                    add_model_element(elements, aliases, element_id, label, "node", line_no)
                relationships.append({"source": left.group("id"), "target": right.group("id"), "kind": arrow, "label": "", "line": line_no})
                continue
        relation = relation_re.match(line)
        if relation:
            source = endpoint_model_id(relation.group("left"), aliases)
            target = endpoint_model_id(relation.group("right"), aliases)
            add_model_element(elements, aliases, source, clean_model_label(relation.group("left")), "external", line_no, package_stack, implicit=True)
            add_model_element(elements, aliases, target, clean_model_label(relation.group("right")), "external", line_no, package_stack, implicit=True)
            relationships.append(
                {
                    "source": source,
                    "target": target,
                    "kind": relation.group("arrow"),
                    "label": (relation.group("label") or "").strip(),
                    "line": line_no,
                }
            )
            continue
        bracket = bracket_re.match(line)
        if bracket:
            element_id = bracket.group("alias") or normalize_model_id(bracket.group("label"))
            add_model_element(elements, aliases, element_id, bracket.group("label"), "component", line_no, package_stack)
            continue
        declaration = declaration_re.match(line)
        if declaration:
            kind = declaration.group("kind").lower()
            element_id, label = parse_alias_body(declaration.group("body"))
            add_model_element(elements, aliases, element_id, label, kind, line_no, package_stack)
            if kind == "package" and line.endswith("{"):
                package_stack.append(label)

    if not elements and text.strip():
        warnings.append("No model elements were recognized; source is still available for manual inspection.")
    return {
        "path": path.as_posix(),
        "title": title,
        "sourceType": source_type,
        "lineCount": len(text.splitlines()),
        "elements": sorted(elements.values(), key=lambda item: (item["kind"], item["label"].lower())),
        "relationships": relationships,
        "warnings": warnings,
    }


def parse_sequence_model(text: str, title: str) -> dict[str, Any] | None:
    participant_re = re.compile(
        r"^(actor|participant|entity|boundary|control|database|queue)\s+(?:\"([^\"]+)\"\s+as\s+([A-Za-z_][\w]*)|([A-Za-z_][\w]*)(?:\s+as\s+([A-Za-z_][\w]*))?)",
        re.IGNORECASE,
    )
    message_re = re.compile(r"^([A-Za-z_][\w]*)\s*(->>|-->|<--|->)\s*([A-Za-z_][\w]*)\s*:\s*(.+)$")
    participants: list[dict[str, Any]] = []
    participant_ids: list[str] = []
    messages: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("'") or line.startswith("!") or line.startswith("@"):
            continue
        if line.lower().startswith("title "):
            title = line[6:].strip() or title
            continue
        participant_match = participant_re.match(line)
        if participant_match:
            label = participant_match.group(2) or participant_match.group(4) or ""
            alias = participant_match.group(3) or participant_match.group(5) or participant_match.group(4) or label
            alias = alias.strip()
            label = label.strip() or alias
            if alias not in participant_ids:
                participant_ids.append(alias)
                participants.append({"id": alias, "label": label, "kind": participant_match.group(1).lower(), "line": line_no, "package": "", "implicit": False})
            continue
        message_match = message_re.match(line)
        if message_match:
            source = message_match.group(1).strip()
            target = message_match.group(3).strip()
            for endpoint in (source, target):
                if endpoint not in participant_ids:
                    participant_ids.append(endpoint)
                    participants.append({"id": endpoint, "label": endpoint, "kind": "participant", "line": line_no, "package": "", "implicit": True})
            messages.append(
                {
                    "source": source,
                    "target": target,
                    "kind": message_match.group(2).strip(),
                    "label": message_match.group(4).strip(),
                    "line": line_no,
                }
            )
    if not participants or not messages:
        return None
    return {"title": title, "sourceType": "plantuml-sequence", "elements": participants, "relationships": messages, "warnings": []}


def parse_activity_model(text: str, title: str) -> dict[str, Any] | None:
    steps: list[dict[str, Any]] = []
    step_re = re.compile(r"^:(.+);$")
    if_re = re.compile(r"^if\s+\((.+)\)\s+then\s+\((.+)\)", re.IGNORECASE)
    else_re = re.compile(r"^else\s+\((.+)\)", re.IGNORECASE)
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("'") or line.startswith("!") or line.startswith("@"):
            continue
        if line.lower().startswith("title "):
            title = line[6:].strip() or title
            continue
        if line == "start":
            steps.append({"id": f"step_{len(steps)}", "label": "Start", "kind": "start", "line": line_no, "package": "", "implicit": False})
            continue
        if line == "stop":
            steps.append({"id": f"step_{len(steps)}", "label": "Stop", "kind": "stop", "line": line_no, "package": "", "implicit": False})
            continue
        step_match = step_re.match(line)
        if step_match:
            steps.append({"id": f"step_{len(steps)}", "label": step_match.group(1).strip(), "kind": "action", "line": line_no, "package": "", "implicit": False})
            continue
        if_match = if_re.match(line)
        if if_match:
            steps.append({"id": f"step_{len(steps)}", "label": if_match.group(1).strip(), "kind": "decision", "line": line_no, "package": "", "implicit": False})
            continue
        else_match = else_re.match(line)
        if else_match:
            steps.append({"id": f"step_{len(steps)}", "label": else_match.group(1).strip(), "kind": "else", "line": line_no, "package": "", "implicit": False})
    if len(steps) < 2:
        return None
    relationships = [
        {"source": steps[index]["id"], "target": steps[index + 1]["id"], "kind": "next", "label": "", "line": steps[index + 1]["line"]}
        for index in range(len(steps) - 1)
    ]
    return {"title": title, "sourceType": "plantuml-activity", "elements": steps, "relationships": relationships, "warnings": []}


def parse_c4_model(text: str, title: str) -> dict[str, Any] | None:
    c4_element_re = re.compile(
        r"^(Person|System_Ext|System|Container_Ext|Container|Component_Ext|Component)\s*\(\s*([^,\)]+)\s*,\s*\"([^\"]*)\"",
        re.IGNORECASE,
    )
    c4_rel_re = re.compile(
        r"^Rel(?:_(?:Back|Dir|Undir|Index))?(?:_Left|_Right)?\s*\(\s*([^,\)]+)\s*,\s*([^,\)]+)\s*,\s*\"([^\"]*)\"",
        re.IGNORECASE,
    )
    kind_map = {
        "person": "person",
        "system": "system",
        "system_ext": "external",
        "container": "container",
        "container_ext": "external",
        "component": "component",
        "component_ext": "external",
    }
    elements: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("!") or line.startswith("'") or line.startswith("@") or line == "@enduml":
            continue
        if line.lower().startswith("title "):
            title = line[6:].strip() or title
            continue
        element_match = c4_element_re.match(line)
        if element_match:
            kind_key = element_match.group(1).lower()
            element_id = element_match.group(2).strip()
            label = element_match.group(3).strip()
            add_model_element(elements, {}, element_id, label, kind_map.get(kind_key, "component"), line_no)
            continue
        relation_match = c4_rel_re.match(line)
        if relation_match:
            source = relation_match.group(1).strip()
            target = relation_match.group(2).strip()
            label = relation_match.group(3).strip()
            add_model_element(elements, {}, source, source, "external", line_no, implicit=True)
            add_model_element(elements, {}, target, target, "external", line_no, implicit=True)
            relationships.append({"source": source, "target": target, "kind": "rel", "label": label, "line": line_no})
    if not elements:
        return None
    return {
        "title": title,
        "sourceType": "plantuml-c4",
        "elements": sorted(elements.values(), key=lambda item: (item["kind"], item["label"].lower())),
        "relationships": relationships,
        "warnings": [],
    }


def resolve_renderer(explicit: str | None) -> Renderer:
    candidates: list[tuple[str, ...]] = []

    env_cmd = os.environ.get("PLANTUML_CMD")
    if env_cmd:
        candidates.append(tuple(shlex.split(env_cmd, posix=os.name != "nt")))

    if explicit:
        explicit_path = Path(explicit)
        if explicit_path.suffix.lower() == ".jar":
            java = shutil.which("java")
            if not java:
                return Renderer(None, "PLANTUML_JAR", False, "PLANTUML_JAR was set, but java is not on PATH.")
            candidates.append((java, "-jar", str(explicit_path)))
        else:
            resolved = shutil.which(explicit) or str(explicit_path)
            candidates.append((resolved,))

    env_jar = os.environ.get("PLANTUML_JAR")
    if env_jar:
        java = shutil.which("java")
        if java:
            candidates.append((java, "-jar", env_jar))
        else:
            return Renderer(None, "PLANTUML_JAR", False, "PLANTUML_JAR was set, but java is not on PATH.")

    plantuml = shutil.which("plantuml")
    if plantuml:
        candidates.append((plantuml,))

    for command in candidates:
        if not command:
            continue
        executable = command[0]
        if shutil.which(executable) or Path(executable).exists():
            return Renderer(command, " ".join(command), True, "PlantUML renderer available.")

    return Renderer(
        None,
        "unavailable",
        False,
        "Install PlantUML on PATH, set PLANTUML_CMD, or set PLANTUML_JAR with java on PATH.",
    )


class UmlRepository:
    def __init__(self, uml_root: Path, cache_root: Path, renderer: Renderer, render_timeout: int) -> None:
        self.uml_root = uml_root.resolve()
        self.cache_root = cache_root.resolve()
        self.renderer = renderer
        self.render_timeout = render_timeout

    def safe_diagram_path(self, rel_path: str) -> Path:
        normalized = normalize_rel_path(rel_path)
        path = (self.uml_root / normalized).resolve()
        if path.suffix.lower() not in DIAGRAM_SUFFIXES or not path_is_within(path, self.uml_root) or not path.is_file():
            raise ValueError("Unknown UML diagram.")
        return path

    def safe_write_path(self, rel_path: str) -> Path:
        normalized = normalize_rel_path(rel_path)
        path = (self.uml_root / normalized).resolve()
        if path.suffix.lower() not in DIAGRAM_SUFFIXES or not path_is_within(path, self.uml_root):
            raise ValueError("Target path must stay inside the UML root and end in .puml, .uml, .mmd, or .mermaid.")
        return path

    def iter_diagrams(self) -> list[Path]:
        if not self.uml_root.exists():
            return []
        return sorted(
            (path for path in self.uml_root.rglob("*") if path.is_file() and path.suffix.lower() in DIAGRAM_SUFFIXES),
            key=lambda item: item.relative_to(self.uml_root).as_posix().lower(),
        )

    def diagram_info(self, path: Path) -> dict[str, Any]:
        rel = path.relative_to(self.uml_root).as_posix()
        source = read_text(path)
        companion = companion_for(path)
        family = uml_family(rel)
        scope = diagram_scope(rel)
        plugin = diagram_plugin(rel)
        return {
            "path": rel,
            "title": extract_title(source, path),
            "format": diagram_format(path),
            "plugin": plugin,
            "kind": family,
            "family": family,
            "scope": scope,
            "group": diagram_group(rel),
            "isLibrary": scope == "library",
            "fileName": path.name,
            "size": path.stat().st_size,
            "modified": int(path.stat().st_mtime),
            "hasCompanion": companion.exists(),
            "companionPath": companion.relative_to(self.uml_root).as_posix() if companion.exists() else None,
        }

    def list_diagrams(self) -> dict[str, Any]:
        diagrams = [self.diagram_info(path) for path in self.iter_diagrams()]
        return {
            "umlRoot": str(self.uml_root),
            "cacheRoot": str(self.cache_root),
            "count": len(diagrams),
            "renderer": {
                "available": self.renderer.available,
                "label": self.renderer.label,
                "reason": self.renderer.reason,
            },
            "diagrams": diagrams,
        }

    def source(self, rel_path: str) -> dict[str, Any]:
        path = self.safe_diagram_path(rel_path)
        text = read_text(path)
        companion = companion_for(path)
        return {
            "path": path.relative_to(self.uml_root).as_posix(),
            "title": extract_title(text, path),
            "format": diagram_format(path),
            "text": text,
            "lineCount": len(text.splitlines()),
            "webPreviewUrl": plantuml_preview_url(text) if path.suffix.lower() in PLANTUML_SUFFIXES else None,
            "companionPath": companion.relative_to(self.uml_root).as_posix() if companion.exists() else None,
        }

    def related_diagrams(self, rel_path: str) -> list[dict[str, Any]]:
        path = self.safe_diagram_path(rel_path)
        rel = path.relative_to(self.uml_root).as_posix()
        plugin = diagram_plugin(rel)
        family = uml_family(rel)
        scope = diagram_scope(rel)
        related: list[Path] = []
        for candidate in self.iter_diagrams():
            candidate_rel = candidate.relative_to(self.uml_root).as_posix()
            if candidate_rel == rel:
                continue
            if uml_family(candidate_rel) != family:
                continue
            if plugin and diagram_plugin(candidate_rel) == plugin:
                related.append(candidate)
            elif not plugin and scope == diagram_scope(candidate_rel) and diagram_group(candidate_rel) == diagram_group(rel):
                related.append(candidate)
        return [self.diagram_info(item) for item in related[:24]]

    def model(self, rel_path: str) -> dict[str, Any]:
        path = self.safe_diagram_path(rel_path)
        text = read_text(path)
        companion = companion_for(path)
        summary = parse_model_summary(path, text)
        return {
            "ok": True,
            "path": path.relative_to(self.uml_root).as_posix(),
            "title": summary["title"],
            "sourceType": summary["sourceType"],
            "lineCount": summary["lineCount"],
            "elements": summary["elements"],
            "relationships": summary["relationships"],
            "warnings": summary["warnings"],
            "companionPath": companion.relative_to(self.uml_root).as_posix() if companion.exists() else None,
            "related": self.related_diagrams(rel_path),
        }

    def mermaid_preview(self, rel_path: str) -> dict[str, Any]:
        path = self.safe_diagram_path(rel_path)
        if path.suffix.lower() in MERMAID_SUFFIXES:
            return {
                "ok": True,
                "path": path.relative_to(self.uml_root).as_posix(),
                "companionPath": None,
                "code": read_text(path),
            }
        companion = companion_for(path)
        if not companion.exists():
            return {"ok": False, "error": "No Markdown companion found for this diagram."}
        markdown = read_text(companion)
        code = find_first_mermaid_block(markdown)
        if not code:
            return {"ok": False, "error": "Markdown companion has no fenced mermaid preview."}
        return {
            "ok": True,
            "path": path.relative_to(self.uml_root).as_posix(),
            "companionPath": companion.relative_to(self.uml_root).as_posix(),
            "code": code,
        }

    def cache_path_for(self, source_path: Path) -> Path:
        rel = source_path.relative_to(self.uml_root).as_posix()
        digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]
        return self.cache_root / "svg" / f"{source_path.stem}-{digest}.svg"

    def render_svg(self, rel_path: str, force: bool = False) -> dict[str, Any]:
        path = self.safe_diagram_path(rel_path)
        if path.suffix.lower() in MERMAID_SUFFIXES:
            return {"ok": False, "error": "Mermaid diagrams render in the browser preview tab."}
        cache_path = self.cache_path_for(path)
        if (
            not force
            and cache_path.exists()
            and cache_path.stat().st_mtime >= path.stat().st_mtime
            and cache_path.stat().st_size > 0
        ):
            return {
                "ok": True,
                "path": path.relative_to(self.uml_root).as_posix(),
                "cached": True,
                "renderer": self.renderer.label,
                "svg": read_text(cache_path),
            }

        if not self.renderer.available or not self.renderer.command:
            return {
                "ok": False,
                "error": self.renderer.reason,
                "renderer": {
                    "available": self.renderer.available,
                    "label": self.renderer.label,
                    "reason": self.renderer.reason,
                },
            }

        source = read_text(path)
        command = [*self.renderer.command, "-tsvg", "-pipe"]
        started = time.time()
        try:
            completed = subprocess.run(
                command,
                input=source,
                capture_output=True,
                text=True,
                timeout=self.render_timeout,
                cwd=str(path.parent),
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"PlantUML render timed out after {self.render_timeout}s."}
        except OSError as exc:
            return {"ok": False, "error": f"Could not start PlantUML: {exc}"}

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0 or "<svg" not in stdout:
            detail = stderr or stdout or f"PlantUML exited with code {completed.returncode}."
            return {"ok": False, "error": detail}

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(stdout, encoding="utf-8")
        return {
            "ok": True,
            "path": path.relative_to(self.uml_root).as_posix(),
            "cached": False,
            "elapsedMs": int((time.time() - started) * 1000),
            "renderer": self.renderer.label,
            "svg": stdout,
        }

    def rendered_svg_text(self, rel_path: str, force: bool = False) -> tuple[str, HTTPStatus, str]:
        payload = self.render_svg(rel_path, force=force)
        if payload.get("ok"):
            return str(payload.get("svg") or ""), HTTPStatus.OK, "image/svg+xml; charset=utf-8"
        return str(payload.get("error") or "Render failed."), HTTPStatus.SERVICE_UNAVAILABLE, "text/plain; charset=utf-8"

    def save_source(self, rel_path: str, text: str) -> dict[str, Any]:
        path = self.safe_diagram_path(rel_path)
        path.write_text(text, encoding="utf-8")
        cache_path = self.cache_path_for(path)
        if cache_path.exists():
            cache_path.unlink()
        return self.source(path.relative_to(self.uml_root).as_posix())

    def import_diagram(self, rel_path: str, text: str, overwrite: bool = False) -> dict[str, Any]:
        path = self.safe_write_path(rel_path)
        existed = path.exists()
        if existed and not overwrite:
            raise ValueError(f"Diagram already exists: {path.relative_to(self.uml_root).as_posix()}")
        if not text.strip():
            raise ValueError("Diagram source is required.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {
            "ok": True,
            "diagram": self.diagram_info(path),
            "created": not existed,
            "umlRoot": str(self.uml_root),
        }

    def search(self, query: str, limit: int) -> dict[str, Any]:
        query = query.strip()
        if not query:
            return {"query": query, "count": 0, "results": []}

        needles = [token.lower() for token in query.split() if token.strip()]
        results: list[dict[str, Any]] = []

        for diagram_path in self.iter_diagrams():
            info = self.diagram_info(diagram_path)
            searchable_files = [("source", diagram_path)]
            companion = companion_for(diagram_path)
            if companion.exists():
                searchable_files.append(("companion", companion))

            matches: list[dict[str, Any]] = []
            total_matches = 0
            for file_kind, file_path in searchable_files:
                lines = read_text(file_path).splitlines()
                for line_no, line in enumerate(lines, start=1):
                    haystack = line.lower()
                    if all(needle in haystack for needle in needles):
                        total_matches += 1
                        if len(matches) < MAX_SEARCH_MATCHES_PER_FILE:
                            matches.append(
                                {
                                    "fileKind": file_kind,
                                    "path": file_path.relative_to(self.uml_root).as_posix(),
                                    "line": line_no,
                                    "text": line.strip(),
                                }
                            )

            if total_matches:
                results.append({**info, "matchCount": total_matches, "matches": matches})
                if len(results) >= limit:
                    break

        return {"query": query, "count": len(results), "results": results}

    def composition_root(self) -> Path:
        return self.uml_root / COMPOSITION_PACKAGE

    def composition_manifest_path(self) -> Path:
        return self.composition_root() / "composition.manifest.json"

    def list_compositions(self, query: str = "") -> dict[str, Any]:
        compositions, warnings, source = self.load_compositions()
        query_text = query.strip().lower()
        if query_text:
            compositions = [
                item
                for item in compositions
                if query_text
                in " ".join(
                    [
                        item.get("id", ""),
                        item.get("title", ""),
                        item.get("status", ""),
                        item.get("mode", ""),
                        item.get("level", ""),
                        item.get("valueSummary", ""),
                        " ".join(item.get("tools", [])),
                        " ".join(item.get("limits", [])),
                    ]
                ).lower()
            ]
        return {
            "ok": True,
            "query": query,
            "count": len(compositions),
            "source": source,
            "manifestPath": str(self.composition_manifest_path()),
            "warnings": warnings,
            "compositions": compositions,
        }

    def composition(self, composition_id: str) -> dict[str, Any]:
        compositions, warnings, source = self.load_compositions()
        for item in compositions:
            if item.get("id") == composition_id:
                diagram_infos = []
                for diagram in item.get("diagrams", []):
                    path_text = str(diagram.get("path") if isinstance(diagram, dict) else diagram)
                    try:
                        diagram_infos.append(self.diagram_info(self.safe_diagram_path(path_text)))
                    except ValueError:
                        continue
                return {
                    "ok": True,
                    "source": source,
                    "warnings": warnings,
                    "composition": {**item, "diagramInfos": diagram_infos},
                }
        raise ValueError("Unknown composition.")

    def load_compositions(self) -> tuple[list[dict[str, Any]], list[str], str]:
        manifest = self.composition_manifest_path()
        if manifest.exists():
            try:
                payload = json.loads(read_text(manifest))
            except json.JSONDecodeError as exc:
                return self.synthesized_compositions([f"Manifest JSON is invalid: {exc}"])
            entries = payload.get("compositions") if isinstance(payload, dict) else payload
            if not isinstance(entries, list):
                return self.synthesized_compositions(["Manifest must be a list or contain a compositions list."])
            return self.normalize_manifest_compositions(entries, manifest)
        return self.synthesized_compositions(["No composition.manifest.json found; synthesized from Markdown companions."])

    def normalize_manifest_compositions(self, entries: list[Any], manifest: Path) -> tuple[list[dict[str, Any]], list[str], str]:
        warnings: list[str] = []
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                warnings.append(f"Composition entry {index + 1} is not an object.")
                continue
            title = str(entry.get("title") or "").strip()
            composition_id = str(entry.get("id") or slugify(title)).strip()
            if not composition_id or not title:
                warnings.append(f"Composition entry {index + 1} is missing id or title.")
                continue
            if composition_id in seen:
                warnings.append(f"Duplicate composition id ignored: {composition_id}")
                continue
            seen.add(composition_id)
            normalized.append(
                {
                    "id": composition_id,
                    "title": title,
                    "status": str(entry.get("status") or "Unknown"),
                    "mode": str(entry.get("mode") or "composition"),
                    "level": str(entry.get("level") or "unknown"),
                    "tools": normalize_string_list(entry.get("tools")),
                    "requiredTools": normalize_string_list(entry.get("requiredTools") or entry.get("required_tools")),
                    "optionalTools": normalize_string_list(entry.get("optionalTools") or entry.get("optional_tools")),
                    "valueSummary": str(entry.get("valueSummary") or entry.get("value_summary") or ""),
                    "docs": self.normalize_link_list(entry.get("docs")),
                    "diagrams": self.normalize_link_list(entry.get("diagrams")),
                    "owningSadDecisions": self.normalize_link_list(entry.get("owningSadDecisions") or entry.get("owning_sad_decisions")),
                    "contracts": self.normalize_link_list(entry.get("contracts")),
                    "gates": self.normalize_link_list(entry.get("gates")),
                    "evidence": self.normalize_link_list(entry.get("evidence")),
                    "limits": normalize_string_list(entry.get("limits")),
                    "sourcePath": manifest.relative_to(self.uml_root).as_posix(),
                }
            )
        normalized.sort(key=lambda item: (item["level"], item["title"].lower()))
        return normalized, warnings, "manifest"

    def normalize_link_list(self, value: Any) -> list[dict[str, str]]:
        if value is None:
            return []
        if isinstance(value, str):
            return [{"label": value, "path": value}] if value.strip() else []
        if isinstance(value, list):
            links = []
            for item in value:
                if isinstance(item, dict):
                    label = str(item.get("label") or item.get("title") or item.get("path") or item.get("href") or "").strip()
                    path = str(item.get("path") or item.get("href") or label).strip()
                    if label and path:
                        links.append({"label": label, "path": path})
                else:
                    text = str(item).strip()
                    if text:
                        links.append({"label": text, "path": text})
            return links
        return [{"label": str(value), "path": str(value)}]

    def synthesized_compositions(self, initial_warnings: list[str] | None = None) -> tuple[list[dict[str, Any]], list[str], str]:
        warnings = list(initial_warnings or [])
        root = self.composition_root()
        if not root.exists():
            return [], [*warnings, f"Composition package not found: {root}"], "none"
        compositions = []
        markdown_files = [path for path in root.rglob("*.md") if path.name.upper() != "TRACEABILITY.MD"]
        for path in sorted(markdown_files, key=lambda item: item.relative_to(root).as_posix().lower()):
            compositions.append(self.composition_from_markdown(path))
        return compositions, warnings, "markdown"

    def composition_from_markdown(self, path: Path) -> dict[str, Any]:
        text = read_text(path)
        rel = path.relative_to(self.uml_root).as_posix()
        title = markdown_heading(text) or path.stem.replace("-", " ").title()
        purpose_match = re.search(r"^Purpose:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        purpose = purpose_match.group(1).strip() if purpose_match else ""
        value = first_markdown_paragraph(markdown_section(text, "Value")) or purpose or first_markdown_paragraph(text)
        status = composition_status_label(markdown_section(text, "Status"))
        links = markdown_links(text)
        diagrams: list[dict[str, str]] = []
        docs: list[dict[str, str]] = []
        for link in links:
            href = link["href"]
            if href.lower().endswith(tuple(DIAGRAM_SUFFIXES)):
                candidate = (path.parent / href).resolve()
                if path_is_within(candidate, self.uml_root):
                    diagrams.append({"label": link["label"], "path": candidate.relative_to(self.uml_root).as_posix()})
                else:
                    diagrams.append({"label": link["label"], "path": href})
            else:
                docs.append({"label": link["label"], "path": href})
        sibling_puml = path.with_suffix(".puml")
        if sibling_puml.exists() and path_is_within(sibling_puml, self.uml_root):
            sibling_rel = sibling_puml.relative_to(self.uml_root).as_posix()
            if not any(item["path"] == sibling_rel for item in diagrams):
                diagrams.append({"label": sibling_puml.stem, "path": sibling_rel})
        level = "variants"
        lower_title = title.lower()
        if "overview" in lower_title or path.name.lower() == "readme.md":
            level = "full-picture"
        elif "single" in lower_title:
            level = "single"
        elif "pair" in lower_title:
            level = "pair"
        mode = "solution-slice" if "slice" in lower_title else "overview"
        tools = extract_known_tools(text)
        return {
            "id": slugify(path.relative_to(self.composition_root()).with_suffix("").as_posix()),
            "title": title,
            "status": status,
            "mode": mode,
            "level": level,
            "tools": tools,
            "requiredTools": tools,
            "optionalTools": [],
            "valueSummary": value,
            "docs": docs,
            "diagrams": diagrams,
            "owningSadDecisions": [item for item in docs if "architecture.md#" in item["path"]],
            "contracts": [item for item in docs if "/contracts/" in item["path"].replace("\\", "/")],
            "gates": [item for item in docs if "/gates/" in item["path"].replace("\\", "/")],
            "evidence": [item for item in docs if any(token in item["path"].replace("\\", "/") for token in ("/evidence/", "/integrations/", "TRACEABILITY"))],
            "limits": [],
            "sourcePath": rel,
        }


class UmlBrowserHandler(SimpleHTTPRequestHandler):
    repository: UmlRepository

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        try:
            if route == "/api/health":
                write_json(self, {"ok": True})
            elif route == "/api/diagrams":
                write_json(self, self.repository.list_diagrams())
            elif route == "/api/source":
                write_json(self, self.repository.source(single_query(query, "path")))
            elif route == "/api/model":
                write_json(self, self.repository.model(single_query(query, "path")))
            elif route == "/api/mermaid":
                write_json(self, self.repository.mermaid_preview(single_query(query, "path")))
            elif route == "/api/render":
                force = single_query(query, "force", "0") in ("1", "true", "yes")
                payload = self.repository.render_svg(single_query(query, "path"), force=force)
                status = HTTPStatus.OK if payload.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE
                write_json(self, payload, status=status)
            elif route == "/api/svg":
                force = single_query(query, "force", "0") in ("1", "true", "yes")
                text, status, content_type = self.repository.rendered_svg_text(single_query(query, "path"), force=force)
                write_text(self, text, content_type, status=status)
            elif route == "/api/search":
                limit = int(single_query(query, "limit", "200"))
                write_json(self, self.repository.search(single_query(query, "q", ""), max(1, min(limit, 500))))
            elif route == "/api/compositions":
                write_json(self, self.repository.list_compositions(single_query(query, "q", "")))
            elif route == "/api/composition":
                write_json(self, self.repository.composition(single_query(query, "id")))
            else:
                self.serve_static(route)
        except ValueError as exc:
            write_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError:
            write_json(self, {"ok": False, "error": "File not found."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        try:
            payload = read_json_body(self)
            if route == "/api/source":
                path = str(payload.get("path") or "")
                text = str(payload.get("text") or "")
                write_json(self, self.repository.save_source(path, text))
            elif route == "/api/import":
                path = str(payload.get("path") or "")
                text = str(payload.get("text") or "")
                overwrite = bool(payload.get("overwrite") or False)
                write_json(self, self.repository.import_diagram(path, text, overwrite=overwrite), HTTPStatus.CREATED)
            else:
                write_json(self, {"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            write_json(self, {"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError:
            write_json(self, {"ok": False, "error": "File not found."}, HTTPStatus.NOT_FOUND)

    def serve_static(self, route: str) -> None:
        if route in ("", "/"):
            route = "/index.html"
        rel = normalize_rel_path(route)
        path = (STATIC_ROOT / rel).resolve()
        if not path_is_within(path, STATIC_ROOT) or not path.is_file():
            write_json(self, {"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        elif path.suffix in (".html", ".css"):
            content_type = f"text/{path.suffix[1:]}; charset=utf-8"
        write_text(self, read_text(path), content_type)


def single_query(query: dict[str, list[str]], key: str, default: str | None = None) -> str:
    values = query.get(key)
    if values:
        return values[0]
    if default is not None:
        return default
    raise ValueError(f"Missing query parameter: {key}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Tiny Tool UML browser.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", default=8765, type=int, help="Port to bind.")
    parser.add_argument("--uml-root", default=str(DEFAULT_UML_ROOT), help="Directory containing .puml, .uml, .mmd, or .mermaid files.")
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE_ROOT), help="Directory for rendered SVG cache.")
    parser.add_argument("--plantuml", default=None, help="Optional plantuml executable or plantuml.jar path.")
    parser.add_argument("--render-timeout", default=90, type=int, help="PlantUML render timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    uml_root = Path(args.uml_root).resolve()
    cache_root = Path(args.cache_root).resolve()
    renderer = resolve_renderer(args.plantuml)

    if not uml_root.exists():
        print(f"UML root does not exist: {uml_root}", file=sys.stderr)
        return 2

    UmlBrowserHandler.repository = UmlRepository(uml_root, cache_root, renderer, args.render_timeout)
    server = ThreadingHTTPServer((args.host, args.port), UmlBrowserHandler)
    print(f"UML browser: http://{args.host}:{args.port}")
    print(f"UML root: {uml_root}")
    print(f"Render cache: {cache_root}")
    print(f"Renderer: {renderer.reason}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UML browser.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
