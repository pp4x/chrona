#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HOME_BIN_DIR="${HOME}/.local/bin"
APPLICATIONS_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
WRAPPER_PATH="${HOME_BIN_DIR}/chrona"
DESKTOP_PATH="${APPLICATIONS_DIR}/chrona.desktop"
ICON_PATH="${ICON_DIR}/chrona.png"

mkdir -p "${HOME_BIN_DIR}" "${APPLICATIONS_DIR}" "${ICON_DIR}"

cat > "${WRAPPER_PATH}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT}"

if [[ -x "\${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="\${REPO_ROOT}/.venv/bin/python"
else
    PYTHON_BIN="\${PYTHON:-python3}"
fi

exec "\${PYTHON_BIN}" "\${REPO_ROOT}/src/chrona.py" "\$@"
EOF

chmod +x "${WRAPPER_PATH}"
install -m 0644 "${REPO_ROOT}/icons/chrona.png" "${ICON_PATH}"
sed "s|@HOME@|${HOME}|g" "${REPO_ROOT}/packaging/chrona.desktop" > "${DESKTOP_PATH}"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPLICATIONS_DIR}" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache "${HOME}/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

cat <<EOF
Installed Chrona launcher files:
  Wrapper: ${WRAPPER_PATH}
  Desktop entry: ${DESKTOP_PATH}
  Icon: ${ICON_PATH}

You may need to log out and back in, or refresh your application launcher, before Chrona appears in menus.
EOF
