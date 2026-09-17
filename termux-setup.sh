#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo
echo "Desktop Store — this phone"
echo "Installing and starting the shop."
echo

if ! command -v pkg >/dev/null 2>&1; then
  echo "Open this in Termux on the phone."
  exit 1
fi

pkg update -y
pkg install -y python unzip curl

HOME_DIR="${HOME}"
APP_DIR="${HOME_DIR}/DesktopStore-Phone"
ZIP_PATH="${HOME_DIR}/DesktopStore-Phone.zip"
ZIP_URL="https://github.com/Quantikz/desktop-store/releases/latest/download/DesktopStore-Phone.zip"

echo
echo "Downloading the shop..."
curl -fL --retry 3 -o "${ZIP_PATH}" "${ZIP_URL}"

rm -rf "${APP_DIR}"
unzip -o "${ZIP_PATH}" -d "${HOME_DIR}"
rm -f "${ZIP_PATH}"

if [ ! -f "${APP_DIR}/run_phone.py" ]; then
  echo "Download did not unpack correctly."
  exit 1
fi

mkdir -p "${HOME_DIR}/bin"
cat > "${HOME_DIR}/bin/desktop-store" << 'LAUNCH'
#!/data/data/com.termux/files/usr/bin/bash
cd "$HOME/DesktopStore-Phone" || exit 1
exec python run_phone.py
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
exec python run_phone.py
