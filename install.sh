#!/usr/bin/env bash
# Install canon-systems globally from this checkout.
# After this, the `canon` CLI is on PATH and user-level Cursor rules +
# subagents are installed under ~/.cursor/. Every repo you open in Cursor
# will get an autosetup prompt on the first substantive prompt.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v pipx >/dev/null 2>&1; then
  echo "Installing canon-systems via pipx..."
  pipx install --force "${ROOT_DIR}[aws]" || pipx install --force "${ROOT_DIR}" || true
else
  echo "pipx not found; falling back to pip --user..."
  python3 -m pip install --user "${ROOT_DIR}[aws]" || python3 -m pip install --user "${ROOT_DIR}" || true
fi

# Ensure a shim on PATH even if pipx didn't place one there.
mkdir -p "${HOME}/.local/bin"
if ! command -v canon >/dev/null 2>&1; then
  cat > "${HOME}/.local/bin/canon" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${ROOT_DIR}/src:\${PYTHONPATH:-}"
exec python3 -m canon_systems.cli "\$@"
EOF
  chmod +x "${HOME}/.local/bin/canon"
  echo "Installed shim at ~/.local/bin/canon"
fi

# Install user-level rules + subagents so unwired repos still get the
# auto-setup offer and have subagents available.
PYTHONPATH="${ROOT_DIR}/src" python3 - <<'PY'
try:
    from canon_systems.repo_enable import install_user_scope
    install_user_scope()
    print("Installed ~/.cursor/rules/canon-autosetup.mdc, memory-layer-defaults.mdc, and scoper/cursor-pilot/qa-gate subagents.")
except Exception as exc:
    print(f"Note: user-scope install skipped: {exc}")
PY

echo ""
echo "canon-systems is installed."
echo "  CLI:            canon --help"
echo "  Per-repo setup: cd <repo> && canon setup"
echo ""
echo "When you open a new repo in Cursor, the agent will offer to run setup"
echo "on the first substantive prompt (via the canon-autosetup rule)."
