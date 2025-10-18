#!/usr/bin/env bash
set -euo pipefail

# Check that we're inside a venv
if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "❌ Error: not inside a Python virtual environment."
  echo "Run 'uv venv' (or your setup script) before using pre-commit."
  exit 1
fi

RUNNER="uv run"

# CI path: cold run without daemon
if [ "${CI:-}" = "true" ]; then
  exec ${RUNNER} mypy --config-file pyproject.toml .
fi

# Ensure daemon is running
if ! ${RUNNER} dmypy status >/dev/null 2>&1; then
  ${RUNNER} dmypy start -- --config-file pyproject.toml
fi

# Incremental fine-grained check
exec ${RUNNER} dmypy run -- --config-file pyproject.toml .
