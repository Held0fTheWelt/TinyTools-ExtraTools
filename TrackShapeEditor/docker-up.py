#!/usr/bin/env python3
"""Track Shape Editor - Docker lifecycle and local dev entry point.

Usage:
    python docker-up.py deploy          # build images + start editor
    python docker-up.py up              # start editor (Docker)
    python docker-up.py down            # stop stack
    python docker-up.py dev             # local Vite dev server (no Docker)
    python docker-up.py test            # CI tests in Docker
    python docker-up.py compile -- --shape /workspace/foo.json --out /output/out.json
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = ROOT / "docker-compose.yml"
EDITOR_DIR = ROOT / "editor"
DEFAULT_PORT = 8080

ALIASES = {
    "hochladen": "up",
    "start": "up",
    "load": "up",
    "entladen": "down",
    "stop": "down",
    "unload": "down",
    "bauen": "build",
    "bauen-und-hochladen": "deploy",
    "ci": "test",
    "log": "logs",
    "ps": "status",
}


class DockerUpError(RuntimeError):
    pass


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def resolve_command(cmd: list[str]) -> list[str]:
    if not cmd:
        return cmd
    resolved = shutil.which(cmd[0])
    if resolved is None:
        return cmd
    return [resolved, *cmd[1:]]


def require_docker() -> None:
    docker = shutil.which("docker")
    if docker is None:
        raise DockerUpError("Docker CLI not found. Install Docker Desktop and add docker to PATH.")
    proc = subprocess.run([docker, "info"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise DockerUpError("Docker daemon is not running. Start Docker Desktop and retry.")


def ensure_dirs() -> None:
    for name in ("workspace", "output"):
        path = ROOT / name
        path.mkdir(parents=True, exist_ok=True)


def npm_bin(name: str) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    return EDITOR_DIR / "node_modules" / ".bin" / f"{name}{suffix}"


def editor_deps_ready() -> bool:
    return (EDITOR_DIR / "node_modules").is_dir() and npm_bin("vite").is_file()


def ensure_editor_deps() -> None:
    if editor_deps_ready():
        return
    print("Installing editor dependencies (npm install)...")
    run(["npm", "install"], cwd=EDITOR_DIR)


def compose_cmd(*args: str, env: dict[str, str] | None = None) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def run(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print("$", " ".join(cmd))
    resolved_cmd = resolve_command(cmd)
    try:
        proc = subprocess.run(resolved_cmd, cwd=cwd or ROOT, env=merged, text=True)
    except FileNotFoundError as exc:
        raise DockerUpError(f"Command not found: {cmd[0]}") from exc
    if check and proc.returncode != 0:
        raise DockerUpError(f"Command failed (exit {proc.returncode}): {' '.join(cmd)}")
    return proc


def editor_port(args: argparse.Namespace) -> int:
    return int(args.port or os.environ.get("EDITOR_PORT", DEFAULT_PORT))


def cmd_build(_: argparse.Namespace) -> None:
    require_docker()
    run(compose_cmd("build", "editor"))
    run(compose_cmd("--profile", "tools", "build", "toolchain"))
    print("Build complete.")


def cmd_up(args: argparse.Namespace) -> None:
    require_docker()
    ensure_dirs()
    if args.build:
        cmd_build(args)
    port = editor_port(args)
    run(compose_cmd("up", "-d", "editor"), env={"EDITOR_PORT": str(port)})
    print(f"Editor: http://localhost:{port}")


def cmd_down(_: argparse.Namespace) -> None:
    require_docker()
    run(compose_cmd("down", "--remove-orphans"))
    print("Stack unloaded.")


def cmd_restart(args: argparse.Namespace) -> None:
    cmd_down(args)
    cmd_up(args)


def cmd_deploy(args: argparse.Namespace) -> None:
    args.build = True
    cmd_up(args)


def cmd_rebuild(args: argparse.Namespace) -> None:
    args.build = True
    cmd_build(args)
    cmd_down(args)
    cmd_up(args)


def cmd_status(_: argparse.Namespace) -> None:
    require_docker()
    run(compose_cmd("ps", "-a"))


def cmd_logs(_: argparse.Namespace) -> None:
    require_docker()
    run(compose_cmd("logs", "-f", "--tail=100", "editor"), check=False)


def cmd_health(args: argparse.Namespace) -> None:
    port = editor_port(args)
    url = f"http://127.0.0.1:{port}/"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            ok = 200 <= resp.status < 400
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DockerUpError(f"Health check failed for {url}: {exc}") from exc
    if not ok:
        raise DockerUpError(f"Health check failed for {url}: HTTP {resp.status}")
    print(f"OK: {url}")


def cmd_test(_: argparse.Namespace) -> None:
    require_docker()
    cmd_build(argparse.Namespace(build=False, port=DEFAULT_PORT))
    run(compose_cmd("--profile", "ci", "run", "--rm", "toolchain-test"))
    run(compose_cmd("--profile", "ci", "run", "--rm", "editor-test"))
    print("CI tests finished.")


def cmd_toolchain(args: argparse.Namespace, sub: str) -> None:
    require_docker()
    ensure_dirs()
    if not args.no_build:
        cmd_build(argparse.Namespace(build=False, port=DEFAULT_PORT))
    run(compose_cmd("--profile", "tools", "run", "--rm", "toolchain", sub, *args.toolchain_args))


def cmd_dev(args: argparse.Namespace) -> None:
    """Start Vite dev server locally (no Docker)."""
    ensure_dirs()
    if shutil.which("npm") is None:
        raise DockerUpError("npm not found. Install Node.js or use: python docker-up.py deploy")
    ensure_editor_deps()
    port = int(args.port or os.environ.get("VITE_PORT", "5173"))
    print(f"Starting Vite dev server on http://localhost:{port}")
    run(["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(port)], cwd=EDITOR_DIR, check=False)


def cmd_init_env(_: argparse.Namespace) -> None:
    ensure_dirs()
    print("workspace/ and output/ are ready.")


def cmd_ensure_env(_: argparse.Namespace) -> None:
    cmd_init_env(_)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track Shape Editor - docker-up.py (build, start, stop, dev, test)",
    )
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("toolchain_args", nargs=argparse.REMAINDER, help="Args after -- for compile/trace/apply")
    parser.add_argument("--build", "-b", action="store_true", help="Build images before up")
    parser.add_argument("--no-build", action="store_true", help="Skip build for compile/trace/apply")
    parser.add_argument("--port", "-p", type=int, help=f"Editor port (default {DEFAULT_PORT})")
    return parser


def print_help() -> None:
    print(
        """Track Shape Editor - docker-up.py

Commands:
  deploy              Build images and start editor in Docker
  up                  Start editor container
  down                Stop containers and unload stack
  restart             down + up
  rebuild             Force rebuild + restart
  build               Build Docker images only
  dev                 Local Vite dev server (no Docker)
  test                Run Python + editor tests in Docker
  compile             Toolchain compile (use -- before args)
  trace               Raster trace CLI
  apply               MCP apply CLI
  shell               Shell in toolchain container
  status              docker compose ps
  logs                Follow editor logs
  health              HTTP check on editor URL
  init-env            Create workspace/ and output/
  ensure-env          Same as init-env

Aliases: hochladen/start=up, entladen/stop=down, bauen=build

Examples:
  python docker-up.py deploy
  python docker-up.py dev
  python docker-up.py down
  python docker-up.py compile -- --shape /workspace/daytona_shape.example.json --out /output/out.json
"""
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = ALIASES.get(args.command.lower(), args.command.lower()) if args.command else "help"

    if args.toolchain_args and args.toolchain_args[0] == "--":
        args.toolchain_args = args.toolchain_args[1:]

    handlers = {
        "help": lambda a: print_help(),
        "build": cmd_build,
        "up": cmd_up,
        "down": cmd_down,
        "restart": cmd_restart,
        "deploy": cmd_deploy,
        "rebuild": cmd_rebuild,
        "status": cmd_status,
        "logs": cmd_logs,
        "health": cmd_health,
        "test": cmd_test,
        "compile": lambda a: cmd_toolchain(a, "compile"),
        "trace": lambda a: cmd_toolchain(a, "trace"),
        "apply": lambda a: cmd_toolchain(a, "apply"),
        "shell": lambda a: cmd_toolchain(a, "bash"),
        "bash": lambda a: cmd_toolchain(a, "bash"),
        "dev": cmd_dev,
        "init-env": cmd_init_env,
        "ensure-env": cmd_ensure_env,
    }

    try:
        handler = handlers.get(command)
        if handler is None:
            _eprint(f"Unknown command: {args.command}")
            print_help()
            return 1
        handler(args)
        return 0
    except DockerUpError as exc:
        _eprint(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
