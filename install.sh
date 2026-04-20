#!/usr/bin/env bash
# Install canon-memory-layer globally from this checkout.
# After this, the CLI is on PATH and user-level Cursor rules + subagents are
# installed under ~/.cursor/. Every repo you open in Cursor will get an
# autosetup prompt on first substantive prompt.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v pipx >/dev/null 2>&1; then
  echo "Installing canon-memory-layer via pipx..."
  pipx install --force "${ROOT_DIR}[aws]" || pipx install --force "${ROOT_DIR}" || true
else
  echo "pipx not found; falling back to pip --user..."
  python3 -m pip install --user "${ROOT_DIR}[aws]" || python3 -m pip install --user "${ROOT_DIR}" || true
fi

# Ensure a shim on PATH even if pipx didn't place one there.
mkdir -p "${HOME}/.local/bin"
if ! command -v canon-memory-layer >/dev/null 2>&1; then
  cat > "${HOME}/.local/bin/canon-memory-layer" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${ROOT_DIR}/src:\${PYTHONPATH:-}"
exec python3 -m memory_layer.cli "\$@"
EOF
  chmod +x "${HOME}/.local/bin/canon-memory-layer"
  echo "Installed shim at ~/.local/bin/canon-memory-layer"
fi

# Install user-level rules + subagents so unwired repos still get the
# auto-setup offer and have subagents available.
python3 - <<'PY'
import sys
sys.path.insert(0, "${ROOT_DIR}/src".replace("${ROOT_DIR}", __import__("os").path.dirname(__import__("os").path.abspath("$0"))))
try:
    from memory_layer.repo_enable import install_user_scope
    install_user_scope()
    print("Installed ~/.cursor/rules/canon-autosetup.mdc, memory-layer-defaults.mdc, and scoper/cursor-pilot/qa-gate subagents.")
except Exception as exc:
    print(f"Note: user-scope install skipped: {exc}")
PY

echo ""
echo "canon-memory-layer is installed."
echo "  CLI:           canon-memory-layer --help"
echo "  Per-repo setup: cd <repo> && canon-memory-layer setup"
echo ""
echo "When you open a new repo in Cursor, the agent will offer to run setup"
echo "on the first substantive prompt (via the canon-autosetup rule)."
