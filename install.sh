#!/usr/bin/env bash
set -euo pipefail

# backward-compatible shortcut
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/launchd.sh" "${1:-status}"
