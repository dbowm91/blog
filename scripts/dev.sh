#!/usr/bin/env bash
# Compatibility wrapper — dev.sh duplicated scripts/setup-dev.sh.
# This wrapper will be removed in a future release.
echo "NOTE: dev.sh is now scripts/setup-dev.sh" >&2
echo "      Running scripts/setup-dev.sh --dev instead." >&2
echo "" >&2
exec "$(dirname "${BASH_SOURCE[0]}")/setup-dev.sh" --dev "$@"
