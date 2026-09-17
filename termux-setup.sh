#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo
echo "Desktop Store — this phone"
echo "Installing and starting the shop."
echo

if [ -z "${PREFIX:-}" ] || [ ! -d "${PREFIX}" ]; then
  echo "Open this in Termux on the phone."
  exit 1
fi

python_bin=""
if command -v python3 >/dev/null 2>&1; then
  python_bin="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  python_bin="$(command -v python)"
fi

fetch_bin=""
if command -v curl >/dev/null 2>&1; then
  fetch_bin="curl"
elif command -v wget >/dev/null 2>&1; then
  fetch_bin="wget"
fi

need_pkg=0
[ -z "${python_bin}" ] && need_pkg=1
[ -z "${fetch_bin}" ] && need_pkg=1

if [ "${need_pkg}" -eq 1 ]; then
  echo "Termux needs Python. Trying to install it..."
  if ! pkg install -y python curl; then
    echo
    echo "Termux could not reach its package site (network unreachable)."
    echo "Fix the Termux mirror, then run this again:"
    echo
    echo "  termux-change-repo"
    echo
    echo "Choose a mirror group (try Europe or Default), tap the first list,"
    echo "then paste the install line again."
    exit 1
  fi
  python_bin="$(command -v python3 || command -v python)"
  fetch_bin="curl"
fi

HOME_DIR="${HOME}"
APP_DIR="${HOME_DIR}/DesktopStore-Phone"
ZIP_PATH="${HOME_DIR}/DesktopStore-Phone.zip"
ZIP_URL="https://github.com/Quantikz/desktop-store/releases/latest/download/DesktopStore-Phone.zip"

echo
echo "Downloading the shop..."
if [ "${fetch_bin}" = "curl" ]; then
  curl -fL --retry 3 -o "${ZIP_PATH}" "${ZIP_URL}"
else
  wget -O "${ZIP_PATH}" "${ZIP_URL}"
fi

rm -rf "${APP_DIR}"
"${python_bin}" - << PY
import zipfile
from pathlib import Path
zip_path = Path.home() / "DesktopStore-Phone.zip"
dest = Path.home()
with zipfile.ZipFile(zip_path) as zf:
    zf.extractall(dest)
print("unpacked")
PY
rm -f "${ZIP_PATH}"

if [ ! -f "${APP_DIR}/run_phone.py" ]; then
  echo "Download did not unpack correctly."
  exit 1
fi

mkdir -p "${HOME_DIR}/bin"
cat > "${HOME_DIR}/bin/desktop-store" << LAUNCH
#!/data/data/com.termux/files/usr/bin/bash
cd "\$HOME/DesktopStore-Phone" || exit 1
exec ${python_bin} run_phone.py
LAUNCH
chmod +x "${HOME_DIR}/bin/desktop-store"

if [ -f "${HOME_DIR}/.bashrc" ] && ! grep -q 'HOME/bin' "${HOME_DIR}/.bashrc"; then
  echo 'export PATH="$HOME/bin:$PATH"' >> "${HOME_DIR}/.bashrc"
fi

echo
echo "Done. This phone: http://127.0.0.1:8080"
echo "Leave Termux open. Next time type: desktop-store"
echo

cd "${APP_DIR}"
exec "${python_bin}" run_phone.py
