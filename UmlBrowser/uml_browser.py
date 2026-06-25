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
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


TOOL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TOOL_ROOT.parents[1]
DEFAULT_SAMPLE_ROOT = TOOL_ROOT / "samples"
DEFAULT_PROJECT_UML_ROOT = REPO_ROOT / "UML"
DEFAULT_UML_ROOT = DEFAULT_PROJECT_UML_ROOT if DEFAULT_PROJECT_UML_ROOT.exists() else DEFAULT_SAMPLE_ROOT
DEFAULT_CACHE_ROOT = REPO_ROOT / "Saved" / "UmlBrowser"
STATIC_ROOT = TOOL_ROOT / "static"
PLANTUML_SUFFIXES = {".puml", ".uml"}
MERMAID_SUFFIXES = {".mmd", ".mermaid"}
DIAGRAM_SUFFIXES = PLANTUML_SUFFIXES | MERMAID_SUFFIXES
MAX_SEARCH_MATCHES_PER_FILE = 8
MAX_BODY_SIZE = 2_000_000


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
        parts = path.relative_to(self.uml_root).parts
        plugin = parts[1] if len(parts) >= 3 and parts[0] == "Plugins" else ""
        kind = parts[-2] if len(parts) >= 2 else ""
        companion = companion_for(path)
        return {
            "path": rel,
            "title": extract_title(source, path),
            "format": diagram_format(path),
            "plugin": plugin,
            "kind": kind,
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
            "companionPath": companion.relative_to(self.uml_root).as_posix() if companion.exists() else None,
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
                cwd=str(self.uml_root),
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
            elif route == "/api/mermaid":
                write_json(self, self.repository.mermaid_preview(single_query(query, "path")))
            elif route == "/api/render":
                force = single_query(query, "force", "0") in ("1", "true", "yes")
                payload = self.repository.render_svg(single_query(query, "path"), force=force)
                status = HTTPStatus.OK if payload.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE
                write_json(self, payload, status=status)
            elif route == "/api/search":
                limit = int(single_query(query, "limit", "200"))
                write_json(self, self.repository.search(single_query(query, "q", ""), max(1, min(limit, 500))))
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
