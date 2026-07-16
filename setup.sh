#!/usr/bin/env bash
# Compatibility wrapper — setup.sh has moved to scripts/setup-dev.sh.
# This wrapper will be removed in a future release.
echo "NOTE: setup.sh has been renamed to scripts/setup-dev.sh" >&2
echo "      Running scripts/setup-dev.sh instead." >&2
echo "" >&2
exec "$(dirname "$0")/scripts/setup-dev.sh" "$@"
