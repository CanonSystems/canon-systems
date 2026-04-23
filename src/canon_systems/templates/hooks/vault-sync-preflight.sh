#!/usr/bin/env bash
set -eu
canon vault sync --once --dry-run 2>/dev/null || true
