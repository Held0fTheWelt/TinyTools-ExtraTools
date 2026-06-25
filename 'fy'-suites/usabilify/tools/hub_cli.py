from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from usabilify.adapter.service import UsabilifyAdapter, inspect_usability_surfaces


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit user-facing repository surfaces.")
    parser.add_argument("command", choices=["audit"], nargs="?", default="audit")
    parser.add_argument("--target-repo", default=".")
    parser.add_argument("--workspace-root", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.workspace_root:
        payload = UsabilifyAdapter(Path(args.workspace_root)).audit(args.target_repo)
    else:
        payload = inspect_usability_surfaces(Path(args.target_repo).resolve())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
