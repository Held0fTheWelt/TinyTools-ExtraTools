#!/usr/bin/env bash
# Track Shape Docker helper (bash wrapper → docker-up.py)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$ROOT/docker-up.py" "$@"
