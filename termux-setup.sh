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

if [ -z "${python_bin}" ]; then
  echo "Termux needs Python. Trying to install it..."
  if ! pkg install -y python; then
    echo
    echo "Termux could not reach its package site."
    echo "Run:  termux-change-repo"
    echo "Then paste the install line again."
    exit 1
  fi
  python_bin="$(command -v python3 || command -v python)"
fi

HOME_DIR="${HOME}"
APP_DIR="${HOME_DIR}/DesktopStore-Phone"
ZIP_PATH="${HOME_DIR}/DesktopStore-Phone.zip"
ZIP_URL="https://github.com/Quantikz/desktop-store/releases/latest/download/DesktopStore-Phone.zip"

echo
echo "Downloading the shop with Python..."
"${python_bin}" - << PY
import urllib.request
from pathlib import Path
url = "${ZIP_URL}"
dest = Path.home() / "DesktopStore-Phone.zip"
print("from GitHub…")
urllib.request.urlretrieve(url, dest)
print("saved", dest)
PY

rm -rf "${APP_DIR}"
"${python_bin}" - << PY
import zipfile
from pathlib import Path
zip_path = Path.home() / "DesktopStore-Phone.zip"
with zipfile.ZipFile(zip_path) as zf:
    zf.extractall(Path.home())
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
