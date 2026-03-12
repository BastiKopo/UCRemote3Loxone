#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$ROOT_DIR/tools/build_integration.py"

echo
printf 'Fertiges Upload-Paket:\n  %s\n' "$ROOT_DIR/dist/uc-remote3-loxone.tar.gz"
